"""HUD primitives and hologram effects on native 128x64 bool ink arrays."""
import math
import pathlib
import sys

import numpy as np

from raster import H, W, PATTERNS, dilate, erode

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
import fgfx  # noqa: E402

_YY, _XX = np.mgrid[0:H, 0:W]


def put(ink, x, y, v=True):
    if 0 <= x < W and 0 <= y < H:
        ink[y, x] = v


# ---- text ---------------------------------------------------------------------

def text(ink, s, x, y, font="small", color=True, align="left"):
    glyphs = fgfx.SMALL if font == "small" else fgfx.MED
    s = s.upper()
    w = fgfx.text_width(glyphs, s, 1)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w // 2
    for ch in s:
        g = glyphs[ch]
        for dy, row in enumerate(g):
            for dx, c in enumerate(row):
                if c == "#":
                    put(ink, x + dx, y + dy, color)
        x += len(g[0]) + 1
    return x


def text_width(s, font="small"):
    glyphs = fgfx.SMALL if font == "small" else fgfx.MED
    return fgfx.text_width(glyphs, s.upper(), 1)


def logo(ink, s, x, y, spacing=2, color=True):
    for ch in s:
        g = fgfx.LOGO[ch]
        yy = y + fgfx.LOGO_H - len(g)
        for dy, row in enumerate(g):
            for dx, c in enumerate(row):
                if c == "#":
                    put(ink, x + dx, yy + dy, color)
        x += len(g[0]) + spacing
    return x


def tag(ink, x1=127, y1=63, label="F.R.I.D.A.Y.", invert=True, pad=2):
    """Name tag anchored at its bottom-right corner. Inverted box by default."""
    w = text_width(label, "med") + 2 * pad + 2
    h = fgfx.MED_H + 2 * pad
    x0, y0 = x1 - w + 1, y1 - h + 1
    if invert:
        ink[y0:y1 + 1, x0:x1 + 1] = True
        # chamfered corners
        for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            put(ink, cx, cy, False)
        text(ink, label, x0 + pad + 1, y0 + pad, "med", color=False)
        # 1 px light halo so it separates from whatever is behind
        halo = dilate(np.pad(np.zeros((H, W), bool), 0))
        ink[max(y0 - 1, 0):y0, x0 - 1:x1 + 2] = False
        ink[y0 - 1:y1 + 2, max(x0 - 1, 0):x0] = False
    else:
        text(ink, label, x0 + pad + 1, y0 + pad, "med", color=True)
    return x0, y0


# ---- geometric ---------------------------------------------------------------

def circle_pts(cx, cy, r, n=None):
    n = n or max(16, int(2 * math.pi * r * 1.5))
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def ring(ink, cx, cy, r, dash=None, phase=0.0, color=True):
    """Circle outline. dash=(on_deg, off_deg); phase rotates in degrees."""
    n = max(24, int(2 * math.pi * r * 2))
    for i in range(n):
        a = 360.0 * i / n
        if dash:
            on, off = dash
            if ((a - phase) % (on + off)) >= on:
                continue
        rad = math.radians(a)
        put(ink, int(round(cx + r * math.cos(rad))), int(round(cy + r * math.sin(rad))), color)


def arc(ink, cx, cy, r, a0, a1, color=True):
    n = max(8, int(abs(a1 - a0) / 360 * 2 * math.pi * r * 2))
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        put(ink, int(round(cx + r * math.cos(a))), int(round(cy + r * math.sin(a))), color)


def radial_ticks(ink, cx, cy, r0, r1, n, phase=0.0, color=True):
    for i in range(n):
        a = math.radians(phase + 360.0 * i / n)
        line(ink, cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a), cy + r1 * math.sin(a), color)


def line(ink, x0, y0, x1, y1, color=True):
    x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        put(ink, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def dotted_hline(ink, x0, x1, y, step=2, phase=0, color=True):
    for x in range(x0, x1 + 1):
        if (x + phase) % step == 0:
            put(ink, x, y, color)


def dotted_vline(ink, x, y0, y1, step=2, phase=0, color=True):
    for y in range(y0, y1 + 1):
        if (y + phase) % step == 0:
            put(ink, x, y, color)


def corners(ink, x0, y0, x1, y1, length=4, color=True):
    for cx, cy, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        line(ink, cx, cy, cx + sx * (length - 1), cy, color)
        line(ink, cx, cy, cx, cy + sy * (length - 1), color)


def rect(ink, x0, y0, x1, y1, fill=None, outline=True):
    if fill is not None:
        ink[y0:y1 + 1, x0:x1 + 1] = PATTERNS[fill][y0:y1 + 1, x0:x1 + 1] if isinstance(fill, str) else fill
    if outline:
        ink[y0, x0:x1 + 1] = True
        ink[y1, x0:x1 + 1] = True
        ink[y0:y1 + 1, x0] = True
        ink[y0:y1 + 1, x1] = True


def bars(ink, x, y_base, heights, w=2, gap=1, up=True, color=True):
    """Equalizer bars growing up from y_base (or centred if up is None)."""
    for i, h in enumerate(heights):
        h = int(round(h))
        bx = x + i * (w + gap)
        if h <= 0:
            put(ink, bx, y_base, color)
            if w > 1:
                put(ink, bx + 1, y_base, color)
            continue
        if up is None:
            y0, y1 = y_base - h, y_base + h
        elif up:
            y0, y1 = y_base - h, y_base
        else:
            y0, y1 = y_base, y_base + h
        ink[max(0, y0):min(H, y1 + 1), bx:bx + w] = color


def waveform(ink, x0, x1, yc, amp, phase, freq=0.25, color=True):
    """Sine-ish voice waveform between x0..x1."""
    prev = None
    for x in range(x0, x1 + 1):
        t = (x - x0) / max(1, x1 - x0)
        env = math.sin(math.pi * t)  # fade at the ends
        y = yc + amp * env * math.sin(freq * x * 2 * math.pi / 4 + phase) * math.sin(0.11 * x + phase * 0.5)
        yi = int(round(y))
        if prev is not None:
            line(ink, x - 1, prev, x, yi, color)
        prev = yi


# ---- hologram effects ---------------------------------------------------------

def scan_row(ink, mask, y, dotted=True, dark_only=True):
    """Hologram refresh line: invert the figure's pixels along row y
    (by default only the dark pixels, so it reads as a light sheen passing)."""
    if 0 <= y < H:
        sel = mask[y].copy()
        if dotted:
            sel &= (_XX[y] % 2 == 0)
        if dark_only:
            sel &= ink[y]
        ink[y, sel] = ~ink[y, sel]


def bitstream(ink, x, y0, y1, i, seed=7, cols=2, density=0.45):
    """Scrolling column(s) of data bits at the screen edge."""
    rng = np.random.default_rng(seed)
    pattern = rng.random((256, cols)) < density
    for k, y in enumerate(range(y0, y1 + 1)):
        row = pattern[(k + i) % 256]
        for c in range(cols):
            put(ink, x + c * 2, y, bool(row[c]))


def scan_band(ink, mask, y, h=2):
    """Erase (to light) a band through dark regions and ink through light."""
    for yy in range(y, y + h):
        if 0 <= yy < H:
            ink[yy, mask[yy]] = ~ink[yy, mask[yy]]


def glitch(ink, slices, mask=None):
    """slices: list of (y0, y1, dx). Shift rows horizontally (within mask if given)."""
    out = ink.copy()
    for y0, y1, dx in slices:
        y0, y1 = max(0, y0), min(H, y1)
        src = ink[y0:y1]
        shifted = np.roll(src, dx, axis=1)
        if dx > 0:
            shifted[:, :dx] = False
        elif dx < 0:
            shifted[:, dx:] = False
        if mask is not None:
            region = mask[y0:y1] | np.roll(mask[y0:y1], dx, axis=1)
            out[y0:y1][region] = shifted[region]
        else:
            out[y0:y1] = shifted
    ink[:] = out


def scanlines(ink, mask, every=2, phase=0):
    """Hologram raster: erase every n-th row of the figure."""
    rows = (_YY % every) == phase
    ink[rows & mask] = False


def noise(ink, mask, density, seed, color=None):
    rng = np.random.default_rng(seed)
    n = rng.random((H, W)) < density
    if color is None:
        ink[n & mask] = ~ink[n & mask]
    else:
        ink[n & mask] = color


def reveal_rows(ink, mask, frac, seed=0, fuzz=6):
    """Materialise: keep figure rows from the centre outward up to frac (0..1),
    with a noisy edge so it looks like a holo-projector filling in."""
    rng = np.random.default_rng(seed)
    ys = np.where(mask.any(axis=1))[0]
    if len(ys) == 0:
        return
    y_min, y_max = ys.min(), ys.max()
    span = y_max - y_min
    cut = y_min + span * frac
    for y in range(y_min, y_max + 1):
        if y > cut + fuzz:
            ink[y, mask[y]] = False
        elif y > cut:
            keep = rng.random(W) < (1 - (y - cut) / fuzz) * 0.6
            ink[y, mask[y] & ~keep] = False


def particles(ink, pts, color=True):
    for x, y in pts:
        put(ink, int(round(x)), int(round(y)), color)
