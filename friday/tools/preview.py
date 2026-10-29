#!/usr/bin/env python3
"""Render 128x64 Flipper frames as an upscaled contact sheet.

Black pixels are drawn in Flipper orange on dark, like the real screen.
Usage: preview.py out.png frame1.png [frame2.png ...] [--scale 4] [--cols 3]
"""
import argparse

from PIL import Image

ON = (0x1B, 0x1B, 0x1B)  # lit pixel (dark on the orange LCD)
OFF = (0xFF, 0x82, 0x00)  # LCD background: Flipper brand orange #FF8200
GAP = 8


def render(path, scale):
    src = Image.open(path).convert("1")
    # White pixels show the backlight, black pixels are lit
    out = Image.composite(
        Image.new("RGB", src.size, OFF), Image.new("RGB", src.size, ON), src.convert("L")
    )
    return out.resize((src.width * scale, src.height * scale), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()

    tiles = [render(f, args.scale) for f in args.frames]
    w, h = tiles[0].size
    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + GAP) + GAP, rows * (h + GAP) + GAP), (40, 40, 40))
    for i, t in enumerate(tiles):
        sheet.paste(t, (GAP + (i % cols) * (w + GAP), GAP + (i // cols) * (h + GAP)))
    sheet.save(args.out)


if __name__ == "__main__":
    main()
