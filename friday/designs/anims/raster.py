"""Hi-res grayscale -> 128x64 1-bit rasterisation helpers.

Everything is drawn at SCALE x on a float32 canvas where 1.0 = backlight
(background) and 0.0 = ink (lit LCD pixel), then box-filtered down and
dithered. Native-resolution touch-ups happen afterwards on the 1-bit grid.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 128, 64
SCALE = 8
HW, HH = W * SCALE, H * SCALE

BAYER4 = (
    np.array(
        [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32
    )
    + 0.5
) / 16.0
BAYER2 = (np.array([[0, 2], [3, 1]], dtype=np.float32) + 0.5) / 4.0


def catmull_rom(points, samples=12, closed=True):
    """Smooth a polygon's control points into a dense point list."""
    pts = list(points)
    n = len(pts)
    out = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if closed else pts[max(i - 1, 0)]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if closed else pts[min(i + 2, n - 1)]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * (
                2 * p1[0]
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                2 * p1[1]
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            out.append((x, y))
    if not closed:
        out.append(pts[-1])
    return out


class Canvas:
    """Float grayscale canvas at SCALE x native resolution."""

    def __init__(self, fill=1.0):
        self.a = np.full((HH, HW), fill, dtype=np.float32)

    # -- masks -----------------------------------------------------------
    @staticmethod
    def mask_polygon(points, smooth=True, samples=12):
        """Boolean mask from native-coordinate polygon points."""
        pts = catmull_rom(points, samples) if smooth else list(points)
        img = Image.new("L", (HW, HH), 0)
        ImageDraw.Draw(img).polygon([(x * SCALE, y * SCALE) for x, y in pts], fill=255)
        return np.asarray(img) > 127

    @staticmethod
    def mask_ellipse(cx, cy, rx, ry):
        img = Image.new("L", (HW, HH), 0)
        ImageDraw.Draw(img).ellipse(
            ((cx - rx) * SCALE, (cy - ry) * SCALE, (cx + rx) * SCALE, (cy + ry) * SCALE),
            fill=255,
        )
        return np.asarray(img) > 127

    @staticmethod
    def mask_stroke(points, width, smooth=True, samples=12, closed=False):
        """Boolean mask of a thick polyline (native coords, native width)."""
        pts = catmull_rom(points, samples, closed=closed) if smooth else list(points)
        img = Image.new("L", (HW, HH), 0)
        d = ImageDraw.Draw(img)
        d.line(
            [(x * SCALE, y * SCALE) for x, y in pts],
            fill=255,
            width=max(1, int(width * SCALE)),
            joint="curve",
        )
        r = width * SCALE / 2
        for x, y in (pts[0], pts[-1]):
            d.ellipse((x * SCALE - r, y * SCALE - r, x * SCALE + r, y * SCALE + r), fill=255)
        return np.asarray(img) > 127

    @staticmethod
    def feather(mask, radius_px):
        """Soft (0..1) version of a boolean mask, radius in native px."""
        img = Image.fromarray((mask * 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(radius_px * SCALE))
        return np.asarray(img).astype(np.float32) / 255.0

    # -- painting --------------------------------------------------------
    def fill(self, mask, value):
        self.a[mask] = value

    def paint(self, mask, values):
        """values: scalar or full-canvas array; applied where mask."""
        if np.isscalar(values):
            self.a[mask] = values
        else:
            self.a[mask] = values[mask]

    def blend(self, soft, value):
        """Blend toward value by a soft 0..1 weight array."""
        self.a = self.a * (1 - soft) + value * soft

    def outline(self, mask, width, value=0.0, inside=True):
        """Draw a stroke along a mask's edge (eroded/dilated difference)."""
        img = Image.fromarray((mask * 255).astype(np.uint8))
        k = int(width * SCALE) * 2 + 1
        if inside:
            inner = np.asarray(img.filter(ImageFilter.MinFilter(k))) > 127
            edge = mask & ~inner
        else:
            outer = np.asarray(img.filter(ImageFilter.MaxFilter(k))) > 127
            edge = outer & ~mask
        self.a[edge] = value
        return edge

    # -- gradients -------------------------------------------------------
    @staticmethod
    def grad(x0, y0, x1, y1, v0, v1):
        """Linear gradient array along the vector (x0,y0)->(x1,y1), native coords."""
        ys, xs = np.mgrid[0:HH, 0:HW].astype(np.float32)
        xs /= SCALE
        ys /= SCALE
        dx, dy = x1 - x0, y1 - y0
        t = ((xs - x0) * dx + (ys - y0) * dy) / (dx * dx + dy * dy)
        t = np.clip(t, 0, 1)
        return v0 + (v1 - v0) * t

    @staticmethod
    def radial(cx, cy, r0, r1, v0, v1):
        ys, xs = np.mgrid[0:HH, 0:HW].astype(np.float32)
        xs /= SCALE
        ys /= SCALE
        d = np.hypot(xs - cx, ys - cy)
        t = np.clip((d - r0) / (r1 - r0), 0, 1)
        return v0 + (v1 - v0) * t

    # -- output ----------------------------------------------------------
    def downsample(self):
        """Box filter to native resolution; returns float array HxW."""
        return self.a.reshape(H, SCALE, W, SCALE).mean(axis=(1, 3))


def dither(gray, mode="bayer4", threshold=0.5):
    """float HxW (1=bg) -> bool HxW ink mask."""
    if mode == "bayer4":
        t = np.tile(BAYER4, (H // 4, W // 4))
        return gray < t
    if mode == "bayer2":
        t = np.tile(BAYER2, (H // 2, W // 2))
        return gray < t
    if mode == "threshold":
        return gray < threshold
    if mode == "fs":
        g = gray.copy()
        ink = np.zeros_like(g, dtype=bool)
        for y in range(H):
            for x in range(W):
                old = g[y, x]
                new = 1.0 if old >= 0.5 else 0.0
                ink[y, x] = new == 0.0
                err = old - new
                if x + 1 < W:
                    g[y, x + 1] += err * 7 / 16
                if y + 1 < H:
                    if x > 0:
                        g[y + 1, x - 1] += err * 3 / 16
                    g[y + 1, x] += err * 5 / 16
                    if x + 1 < W:
                        g[y + 1, x + 1] += err * 1 / 16
        return ink
    raise ValueError(mode)


def to_image(ink):
    """bool ink mask -> PIL mode '1' image (0 = ink)."""
    return Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).convert("1")


def from_image(img):
    return np.asarray(img.convert("L")) < 128


# ---------------------------------------------------------------------------
# Native-resolution cel-shading compositor
# ---------------------------------------------------------------------------

_YY, _XX = np.mgrid[0:H, 0:W]
PATTERNS = {
    "black": np.ones((H, W), bool),
    "white": np.zeros((H, W), bool),
    "checker": (_XX + _YY) % 2 == 0,
    "dots25": ((_XX % 2) == 0) & ((_YY % 2) == 0),  # 25 % ink
    "dots75": ~(((_XX % 2) == 1) & ((_YY % 2) == 1)),  # 75 % ink
    "dots12": ((_XX % 4) == 0) & ((_YY % 2) == 0) | ((_XX % 4) == 2) & ((_YY % 2) == 1),
    "hlines": _YY % 2 == 0,
    "hlines3": _YY % 3 == 0,
    "vlines": _XX % 2 == 0,
    "diag": (_XX + _YY) % 3 == 0,
    "diag_r": (_XX - _YY) % 3 == 0,
}


def native_mask(mask_hr, coverage=0.5):
    """Hi-res bool mask -> native bool mask by pixel coverage."""
    cov = mask_hr.reshape(H, SCALE, W, SCALE).mean(axis=(1, 3))
    return cov >= coverage


def erode(m):
    out = m.copy()
    out[1:, :] &= m[:-1, :]
    out[:-1, :] &= m[1:, :]
    out[:, 1:] &= m[:, :-1]
    out[:, :-1] &= m[:, 1:]
    return out


def dilate(m):
    out = m.copy()
    out[1:, :] |= m[:-1, :]
    out[:-1, :] |= m[1:, :]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def dilate8(m):
    out = dilate(m)
    out[1:, 1:] |= m[:-1, :-1]
    out[1:, :-1] |= m[:-1, 1:]
    out[:-1, 1:] |= m[1:, :-1]
    out[:-1, :-1] |= m[1:, 1:]
    return out


class Scene:
    """1-bit compositor working on native bool masks with pattern fills."""

    def __init__(self):
        self.ink = np.zeros((H, W), bool)

    def fill(self, mask, pattern="black"):
        pat = PATTERNS[pattern] if isinstance(pattern, str) else pattern
        self.ink[mask] = pat[mask]

    def outline(self, mask, against_light=True, inner=True):
        """1 px outline of a native mask. If against_light, only where the
        pixel just outside the edge is currently light (keeps hair/face
        boundaries from doubling up)."""
        edge = mask & ~erode(mask) if inner else dilate(mask) & ~mask
        if against_light:
            outside = dilate8(~mask) if inner else mask
            # a pixel is on the lit boundary if any neighbour outside mask is light
            light_nb = dilate8(~mask & ~self.ink)
            edge &= light_nb
        self.ink[edge] = True
        return edge

    def line(self, pts, value=True):
        """Crisp native polyline via PIL."""
        img = Image.new("1", (W, H), 0)
        ImageDraw.Draw(img).line([(int(round(x)), int(round(y))) for x, y in pts], fill=1)
        m = np.asarray(img).astype(bool)
        self.ink[m] = value
        return m
