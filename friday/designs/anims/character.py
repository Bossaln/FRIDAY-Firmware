"""FRIDAY character: an original holographic AI assistant.

Geometry is defined in native 128x64 coordinates (floats). Shapes are
rasterised at SCALE x, converted to crisp native masks and filled with
flat 1-bit patterns (cel shading). Facial features (eyes, brows, nose,
mouth) are hand-tuned pixel overlays from `overlays/`.
"""
import pathlib

import numpy as np

from raster import H, W, Canvas, Scene, dilate, erode, native_mask

HERE = pathlib.Path(__file__).resolve().parent
OVERLAYS = HERE / "overlays"

CX = 42.0  # head centre x


class Xf:
    """Design-space -> screen-space transform (zoom about the forehead anchor)."""

    def __init__(self, z=1.0, ox=0.0, oy=0.0, ax=None, ay=9.0):
        self.z, self.ox, self.oy = z, ox, oy
        self.ax = CX if ax is None else ax
        self.ay = ay

    def pt(self, p):
        x, y = p
        return (self.ax + self.ox + (x - self.ax) * self.z, self.ay + self.oy + (y - self.ay) * self.z)

    def mask_polygon(self, pts, **kw):
        return Canvas.mask_polygon([self.pt(p) for p in pts], **kw)

    def mask_stroke(self, pts, width, **kw):
        return Canvas.mask_stroke([self.pt(p) for p in pts], width * self.z, **kw)

    def mask_ellipse(self, cx, cy, rx, ry):
        x, y = self.pt((cx, cy))
        return Canvas.mask_ellipse(x, y, rx * self.z, ry * self.z)

    @property
    def xl(self):
        return self.z >= 1.4


class Pose:
    """Per-frame animation parameters."""

    def __init__(
        self,
        eyes="open",
        brows="neutral",
        mouth="neutral",
        gaze=0,  # -1 left, 0 centre, 1 right (px)
        hair=0.0,  # ponytail sway -1..1
        breath=0.0,  # 0..1 shoulder rise
        head_dx=0.0,
        head_dy=0.0,
        blush=False,
        strand=0.0,  # loose strand sway -1..1
        xf=None,  # Xf transform (zoom); default 1:1
    ):
        self.eyes = eyes
        self.brows = brows
        self.mouth = mouth
        self.gaze = gaze
        self.hair = hair
        self.breath = breath
        self.head_dx = head_dx
        self.head_dy = head_dy
        self.blush = blush
        self.strand = strand
        self.xf = xf or Xf()

    def replace(self, **kw):
        p = Pose(**{**self.__dict__})
        for k, v in kw.items():
            setattr(p, k, v)
        return p


def body_masks(pose):
    """Return dict of native bool masks for every body part."""
    M = pose.xf
    dx, dy = pose.head_dx, pose.head_dy
    cx = CX + dx
    br = -pose.breath * 1.0
    sway = pose.hair

    m = {}

    # ---- torso: fitted top with stand collar --------------------------
    torso_pts = [
        (cx - 40, 68), (cx - 35, 60.5 + br), (cx - 27, 56.5 + br), (cx - 17, 54.5 + br),
        (cx - 9, 53.5 + br), (cx - 6.5, 57), (cx, 59.5), (cx + 6.5, 57), (cx + 9, 53.5 + br),
        (cx + 17, 54.5 + br), (cx + 27, 56.5 + br), (cx + 35, 60.5 + br), (cx + 40, 68),
        (cx + 40, 72), (cx - 40, 72),
    ]
    m["torso"] = native_mask(M.mask_polygon(torso_pts, samples=8))
    # collar V seam (light line on the dark top)
    seam = M.mask_stroke([(cx - 8.5, 54 + br), (cx - 2.5, 61.5), (cx, 64)], 0.8, smooth=False)
    seam |= M.mask_stroke([(cx + 8.5, 54 + br), (cx + 2.5, 61.5), (cx, 64)], 0.8, smooth=False)
    m["seam"] = native_mask(seam, 0.35)
    # lit shoulder panel (upper left) and a shoulder seam on the right
    m["torso_lit"] = native_mask(
        M.mask_polygon(
            [(cx - 36, 61 + br), (cx - 28, 57 + br), (cx - 18, 55 + br), (cx - 12, 56 + br),
             (cx - 16, 60 + br), (cx - 24, 63 + br), (cx - 33, 66 + br)],
            samples=6,
        )
    )

    # ---- neck -----------------------------------------------------------
    neck_pts = [(cx - 5, 42 + dy), (cx + 5, 42 + dy), (cx + 6.5, 58), (cx - 6.5, 58)]
    m["neck"] = native_mask(M.mask_polygon(neck_pts, smooth=False))
    m["neck_shadow"] = native_mask(
        M.mask_polygon(
            [(cx - 6, 44 + dy), (cx + 6, 44 + dy), (cx + 6, 48 + dy), (cx, 50.5 + dy), (cx - 6, 48 + dy)],
            samples=6,
        )
    )
    m["neck_side"] = native_mask(
        M.mask_polygon([(cx + 2, 42 + dy), (cx + 6, 42 + dy), (cx + 8, 58), (cx + 4, 58)], smooth=False)
    )

    # ---- back hair ------------------------------------------------------
    back_pts = [
        (cx - 18, 32 + dy), (cx - 19.5, 20 + dy), (cx - 17, 9 + dy), (cx - 9, 3 + dy),
        (cx + 2, 1.5 + dy), (cx + 12, 4 + dy), (cx + 18, 10 + dy), (cx + 19.5, 20 + dy),
        (cx + 18, 32 + dy), (cx + 13, 41 + dy), (cx, 45 + dy), (cx - 13, 41 + dy),
    ]
    m["back"] = native_mask(M.mask_polygon(back_pts, samples=10))

    # ---- ponytail: high, sweeping to the right -----------------------------
    px0, py0 = cx + 11, 5 + dy
    s = sway
    tail_pts = [
        (px0, py0), (px0 + 8 + s * 1.0, py0 + 1.5), (px0 + 15 + s * 2.5, py0 + 7),
        (px0 + 17.5 + s * 4.0, py0 + 16), (px0 + 16 + s * 5.5, py0 + 26),
        (px0 + 11 + s * 7.0, py0 + 34), (px0 + 6 + s * 8.0, py0 + 39),
    ]
    widths = [4.5, 7.0, 9.5, 10.0, 8.5, 5.5, 2.5]
    tail = np.zeros((H * 8, W * 8), bool)
    smooth_pts = tail_pts
    for i in range(len(smooth_pts) - 1):
        tail |= M.mask_stroke(
            [smooth_pts[i], smooth_pts[i + 1]], (widths[i] + widths[i + 1]) / 2, smooth=False
        )
    m["tail"] = native_mask(tail)
    # sheen on the tail: a band following the flow
    hl = M.mask_stroke(
        [(px0 + 12 + s * 2.0, py0 + 4), (px0 + 16.5 + s * 3.5, py0 + 11), (px0 + 17 + s * 4.8, py0 + 20),
         (px0 + 14 + s * 6.2, py0 + 29), (px0 + 10 + s * 7.5, py0 + 35)],
        1.4,
    )
    m["tail_sheen"] = native_mask(hl, 0.45) & erode(m["tail"])
    # a flyaway strand at the tip
    m["tail_tip"] = native_mask(
        M.mask_stroke(
            [(px0 + 7 + s * 8.0, py0 + 38), (px0 + 3 + s * 9.0, py0 + 43), (px0 + 1 + s * 9.5, py0 + 46)],
            1.0, smooth=False,
        )
    )
    # hair tie (small light band where the tail leaves the head)
    m["tie"] = native_mask(M.mask_stroke([(px0 + 4, py0 - 1), (px0 + 6, py0 + 5)], 1.2, smooth=False))

    # ---- face ---------------------------------------------------------------
    face_pts = [
        (cx, 9 + dy), (cx + 9.5, 11 + dy), (cx + 14.5, 18 + dy), (cx + 15.5, 27 + dy),
        (cx + 13.5, 36 + dy), (cx + 9.5, 43 + dy), (cx + 4, 47.5 + dy), (cx, 48.5 + dy),
        (cx - 4, 47.5 + dy), (cx - 9.5, 43 + dy), (cx - 13.5, 36 + dy), (cx - 15.5, 27 + dy),
        (cx - 14.5, 18 + dy), (cx - 9.5, 11 + dy),
    ]
    m["face"] = native_mask(M.mask_polygon(face_pts, samples=10))
    # cel shadow on the right side of the face (cheek/jaw), under bangs, and under lower lip
    m["face_shadow"] = native_mask(
        M.mask_polygon(
            [(cx + 15.5, 24 + dy), (cx + 15.2, 32 + dy), (cx + 12, 40 + dy), (cx + 7, 45.5 + dy),
             (cx + 2, 48 + dy), (cx + 6.5, 44.5 + dy), (cx + 10.5, 38 + dy), (cx + 12.3, 30 + dy),
             (cx + 12.5, 24 + dy)],
            samples=6,
        )
    )
    # highlight on the forehead / cheekbone left (kept light - handled by default)

    # ---- front hair -----------------------------------------------------------
    # Side-swept bangs: part on the right, sweeping down-left across the forehead
    bangs = M.mask_polygon(
        [
            (cx + 9, 5 + dy), (cx + 3, 7.5 + dy), (cx - 4, 11 + dy), (cx - 10, 15.5 + dy),
            (cx - 14, 21 + dy), (cx - 16.5, 28 + dy), (cx - 17.5, 20 + dy), (cx - 15, 11 + dy),
            (cx - 9, 5.5 + dy), (cx - 1, 2.8 + dy), (cx + 8, 3 + dy), (cx + 15, 6 + dy),
            (cx + 18.5, 12 + dy), (cx + 17, 10.5 + dy), (cx + 13, 7 + dy),
        ],
        samples=10,
    )
    # pointed strands at the lower fringe edge
    for sx, sy, ex, ey, w in (
        (cx + 1, 8 + dy, cx - 4, 14 + dy, 2.4),
        (cx - 5, 11 + dy, cx - 9, 18.5 + dy, 2.4),
        (cx - 10, 15 + dy, cx - 13, 22 + dy, 2.0),
        (cx + 5, 6 + dy, cx + 4.5, 10.5 + dy, 1.8),
    ):
        bangs |= M.mask_stroke([(sx, sy), (ex, ey)], w, smooth=False)
    m["bangs"] = native_mask(bangs)
    # Right side lock in front of the ear
    m["side"] = native_mask(
        M.mask_polygon(
            [(cx + 12, 8 + dy), (cx + 17.5, 13 + dy), (cx + 18.5, 22 + dy), (cx + 17, 32 + dy),
             (cx + 15.2, 31 + dy), (cx + 15.6, 22 + dy), (cx + 14, 14 + dy)],
            samples=6,
        )
    )
    # Left loose strand framing the face (sways slightly)
    st = pose.strand
    m["strand"] = native_mask(
        M.mask_stroke(
            [(cx - 15.5, 20 + dy), (cx - 17.5 + st * 0.6, 30 + dy), (cx - 16 + st * 1.2, 40 + dy),
             (cx - 14 + st * 1.5, 45 + dy)],
            1.3,
        ),
        0.4,
    )
    # bangs sheen: a thin light streak following the sweep
    m["bangs_sheen"] = native_mask(
        M.mask_stroke([(cx + 6, 6 + dy), (cx, 7.5 + dy), (cx - 6, 11 + dy), (cx - 11, 16 + dy)], 0.9),
        0.45,
    ) & m["bangs"]
    # back hair rim light (left)
    m["back_rim"] = native_mask(
        M.mask_stroke([(cx - 15.5, 9 + dy), (cx - 18.5, 15 + dy), (cx - 19, 24 + dy)], 0.8), 0.45
    ) & m["back"]
    # light flow lines inside the dark hair
    flow = np.zeros((H * 8, W * 8), bool)
    for pts in (
        [(cx - 14, 12 + dy), (cx - 17, 19 + dy), (cx - 17.5, 28 + dy)],
    ):
        flow |= M.mask_stroke(pts, 0.6)
    m["flow"] = native_mask(flow, 0.4)
    # ear
    m["ear"] = native_mask(M.mask_ellipse(cx + 15.5, 28.5 + dy, 1.8, 3.0)) & ~m["face"]
    return m


def compose(scene, m, pose):
    """Paint the body masks into a Scene in back-to-front order."""
    s = scene
    # back hair & ponytail
    s.fill(m["back"], "black")
    s.fill(m["tail"], "black")
    s.fill(m["tail_sheen"], "white")
    s.fill(m["tail_tip"], "black")
    s.fill(m["tie"], "white")
    # torso
    s.fill(m["torso"], "black")
    s.fill(m["torso_lit"], "dots75")
    s.fill(m["seam"] & m["torso"], "white")
    # neck
    s.fill(m["neck"], "white")
    s.fill(m["neck_shadow"] & m["neck"], "checker")
    s.fill(m["neck_side"] & m["neck"] & ~m["neck_shadow"], "dots25")
    s.outline(m["neck"], against_light=False)
    # ear & face
    s.fill(m["ear"], "white")
    s.outline(m["ear"], against_light=False)
    s.fill(m["face"], "white")
    s.fill(m["face_shadow"] & m["face"], "checker")
    face_edge = s.outline(m["face"], against_light=True)
    # front hair
    s.fill(m["bangs"], "black")
    s.fill(m["bangs_sheen"] & erode(m["bangs"]), "white")
    s.fill(m["side"], "black")
    s.fill(m["strand"], "black")
    hair_all = m["back"] | m["bangs"] | m["side"]
    s.fill(m["flow"] & erode(hair_all) & ~m["bangs_sheen"], "white")
    return s


# ---------------------------------------------------------------------------
# Native-resolution feature overlays
# ---------------------------------------------------------------------------

_overlay_cache = {}


def load_overlay(name):
    """ASCII overlay: '#' ink, '.' erase to light, ' ' transparent, ';' comment."""
    if name in _overlay_cache:
        return _overlay_cache[name]
    lines = (OVERLAYS / f"{name}.txt").read_text().splitlines()
    lines = [l for l in lines if not l.startswith(";")]
    w = max(len(l) for l in lines)
    ink = np.zeros((len(lines), w), bool)
    erase = np.zeros((len(lines), w), bool)
    for y, l in enumerate(lines):
        for x, ch in enumerate(l):
            if ch == "#":
                ink[y, x] = True
            elif ch == ".":
                erase[y, x] = True
    _overlay_cache[name] = (ink, erase)
    return ink, erase


def stamp(ink_img, name, x, y, mirror=False):
    ink, erase = load_overlay(name)
    if mirror:
        ink, erase = ink[:, ::-1], erase[:, ::-1]
    h, w = ink.shape
    x0, y0 = int(round(x)), int(round(y))
    for yy in range(h):
        for xx in range(w):
            px, py = x0 + xx, y0 + yy
            if 0 <= px < W and 0 <= py < H:
                if erase[yy, xx]:
                    ink_img[py, px] = False
                if ink[yy, xx]:
                    ink_img[py, px] = True


# Feature anchors relative to head centre (native px)
EYE_L = (-12, 24)
EYE_R = (3, 24)
BROW_L = (-13, 20)
BROW_R = (3, 20)
NOSE = (-2, 29)
MOUTH = (-5, 39)


# XL (close-up) anchors: top-left of each overlay in design space
EYE_L_XL = (-13, 23)
EYE_R_XL = (2, 23)
BROW_L_XL = (-14, 19.5)
BROW_R_XL = (2, 19.5)
NOSE_XL = (-3, 29)
MOUTH_XL = (-6, 39.5)


def apply_features(ink, pose):
    xf = pose.xf
    dx, dy = pose.head_dx, pose.head_dy
    cx = CX + dx
    xl = xf.xl
    sfx = "_xl" if xl else ""
    eye_l, eye_r = (EYE_L_XL, EYE_R_XL) if xl else (EYE_L, EYE_R)
    brow_l, brow_r = (BROW_L_XL, BROW_R_XL) if xl else (BROW_L, BROW_R)
    nose, mouth = (NOSE_XL, MOUTH_XL) if xl else (NOSE, MOUTH)

    def at(anchor, gx=0):
        x, y = xf.pt((cx + anchor[0], anchor[1] + dy))
        return int(round(x)) + gx, int(round(y))

    left, right = pose.eyes, pose.eyes
    if pose.eyes == "wink":
        left, right = "open", "closed"
    gaze = pose.gaze if pose.eyes in ("open", "half", "wide", "wink") else 0
    stamp(ink, f"eye_{left}{sfx}", *at(eye_l, gaze))
    stamp(ink, f"eye_{right}{sfx}", *at(eye_r, gaze), mirror=True)
    stamp(ink, f"brow_{pose.brows}{sfx}", *at(brow_l))
    stamp(ink, f"brow_{pose.brows}{sfx}", *at(brow_r), mirror=True)
    stamp(ink, f"nose{sfx}", *at(nose))
    stamp(ink, f"mouth_{pose.mouth}{sfx}", *at(mouth))
    if pose.blush:
        stamp(ink, f"blush{sfx}", *at((-13, 33)))
        stamp(ink, f"blush{sfx}", *at((10, 33)))
    return ink


def render(pose, scene=None):
    """Render the character into a Scene (or a fresh one). Returns (scene, masks)."""
    s = scene or Scene()
    m = body_masks(pose)
    compose(s, m, pose)
    apply_features(s.ink, pose)
    m["all"] = m["back"] | m["tail"] | m["tail_tip"] | m["torso"] | m["neck"] | m["face"] | m["bangs"] | m["side"] | m["strand"] | m["ear"]
    return s, m
