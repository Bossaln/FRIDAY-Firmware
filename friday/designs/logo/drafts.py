#!/usr/bin/env python3
"""Render FRIDAY wordmark drafts to designs/logo/drafts/."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
import fgfx as g  # noqa: E402

OUT = pathlib.Path(__file__).parent / "drafts"
TAG1 = "FIRMWARE FOR RADIO, INFRARED,"
TAG2 = "DIGITAL ACCESS & YOU"


def solid():
    img, d = g.new()
    g.corners(d, 0, 0, 127, 63)
    g.logo(img, "F.R.I.D.A.Y.", 64, 10, align="center")
    g.ticks(d, 21, 106, 28)
    g.small(img, TAG1, 64, 38, align="center")
    g.small(img, TAG2, 64, 45, align="center")
    g.dotted_hline(d, 21, 106, 56)
    return img


def outlined():
    img, d = g.new()
    g.logo(img, "F.R.I.D.A.Y.", 64, 9, spacing=4, align="center")
    img = g.outline(img)
    d = g.ImageDraw.Draw(img)
    d.line((8, 29, 119, 29), fill=g.FG)
    d.line((8, 29, 4, 33), fill=g.FG)
    d.line((119, 29, 123, 33), fill=g.FG)
    g.small(img, TAG1, 64, 38, align="center")
    g.small(img, TAG2, 64, 45, align="center")
    g.corners(d, 0, 0, 127, 63, length=3)
    return img


def hud():
    img, d = g.new()
    cx, cy = 23, 32
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), outline=g.FG)
    for start in range(0, 360, 45):
        d.arc((cx - 14, cy - 14, cx + 14, cy + 14), start + 8, start + 37, fill=g.FG)
    d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=g.FG)
    for x0, y0, x1, y1 in (
        (cx, cy - 23, cx, cy - 17),
        (cx, cy + 17, cx, cy + 23),
        (cx - 23, cy, cx - 17, cy),
        (cx + 17, cy, cx + 23, cy),
    ):
        d.line((x0, y0, x1, y1), fill=g.FG)
    g.logo(img, "FRIDAY", 51, 12)
    g.ticks(d, 51, 123, 29)
    g.small(img, "FIRMWARE FOR RADIO,", 51, 36)
    g.small(img, "INFRARED, DIGITAL", 51, 43)
    g.small(img, "ACCESS & YOU", 51, 50)
    return img


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, fn in (("a_solid", solid), ("b_outline", outlined), ("c_hud", hud)):
        fn().save(OUT / f"{name}.png")
        print(OUT / f"{name}.png")
