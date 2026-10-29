#!/usr/bin/env python3
"""Render the FRIDAY firstboot slideshow and update splash into assets/slideshow.

Frame order and buttons must match the 7-frame input logic in
firmware/applications/services/desktop/views/desktop_view_slideshow.c:
  0: Right  1: Up  2-4: auto (2 s)  5: Left = replay from 2, Right  6: OK
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
import fgfx as g  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[3] / "assets" / "slideshow"

ACROSTIC = [
    ("F", "IRMWARE FOR"),
    ("R", "ADIO"),
    ("I", "NFRARED"),
    ("D", "IGITAL"),
    ("A", "CCESS &"),
    ("Y", "OU"),
]


def header_line(d, y):
    d.line((8, y, 119, y), fill=g.FG)
    d.line((8, y, 4, y + 4), fill=g.FG)
    d.line((119, y, 123, y + 4), fill=g.FG)


def welcome():
    img, d = g.new()
    g.small(img, "WELCOME TO", 6, 3)
    g.logo_outlined(img, "F.R.I.D.A.Y.", 64, 12)
    header_line(d, 29)
    g.small(img, "FIRMWARE FOR RADIO, INFRARED,", 64, 35, align="center")
    g.small(img, "DIGITAL ACCESS & YOU", 64, 42, align="center")
    g.button(d, img, "NEXT }", 124, 62)
    return img


def systems_check():
    img, d = g.new()
    g.med(img, "SYSTEMS CHECK", 4, 3)
    d.line((4, 12, 123, 12), fill=g.FG)
    rows = ["SUB-GHZ RADIO", "INFRARED", "NFC / RFID", "DIGITAL ACCESS"]
    for i, name in enumerate(rows):
        y = 16 + i * 7
        end = g.small(img, "> " + name, 4, y)
        g.dotted_hline(d, end + 2, 112, y + 4)
        g.small(img, "OK", 123, y, align="right")
    g.button(d, img, "^ PRESS UP", 64 + 24, 62)
    return img


def acrostic(revealed):
    img, d = g.new()
    for i, (letter, rest) in enumerate(ACROSTIC):
        y = 2 + i * 10
        if i < revealed:
            d.rectangle((3, y, 11, y + 8), fill=g.FG)
            g.med(img, letter, 5, y + 1, color=g.BG)
            g.med(img, rest, 15, y + 1)
        else:
            d.rectangle((3, y, 11, y + 8), outline=g.FG)
            g.med(img, letter, 5, y + 1)
    # Progress bar on the right edge
    d.rectangle((120, 2, 124, 61), outline=g.FG)
    fill = round(58 * revealed / len(ACROSTIC))
    if fill:
        d.rectangle((122, 60 - fill + 1, 122, 60), fill=g.FG)
    return img


def hello():
    img, d = g.new()
    g.corners(d, 0, 0, 127, 63, length=3)
    g.med(img, "HELLO, BOSS.", 64, 12, align="center")
    g.small(img, "ALL SYSTEMS ONLINE", 64, 24, align="center")
    g.ticks(d, 20, 107, 33)
    g.button(d, img, "{ REPLAY", 3 + g.text_width(g.SMALL, "{ REPLAY", 1) + 6, 61)
    g.button(d, img, "NEXT }", 124, 61)
    return img


def online():
    img, d = g.new()
    g.logo_outlined(img, "F.R.I.D.A.Y.", 64, 8)
    header_line(d, 25)
    g.med(img, "IS ONLINE", 64, 33, align="center")
    # "PRESS [OK] TO START", centred, text on the button label's baseline
    x = 64 - (g.text_width(g.SMALL, "PRESS", 1) + 4 + 13 + 4 + g.text_width(g.SMALL, "TO START", 1)) // 2
    x = g.small(img, "PRESS", x, 55) + 3
    x = g.button(d, img, "OK", x + 13, 62) + 13
    g.small(img, "TO START", x + 4, 55)
    return img


def updated():
    img, d = g.new()
    g.logo_outlined(img, "F.R.I.D.A.Y.", 64, 8)
    header_line(d, 25)
    g.med(img, "FIRMWARE UPDATED", 64, 34, align="center")
    g.button(d, img, "OK }", 124, 62)
    return img


FIRSTBOOT = [welcome, systems_check, lambda: acrostic(2), lambda: acrostic(4),
             lambda: acrostic(6), hello, online]

if __name__ == "__main__":
    for folder, frames in (("firstboot", FIRSTBOOT), ("update_default", [updated])):
        (OUT / folder).mkdir(exist_ok=True)
        for i, fn in enumerate(frames):
            fn().save(OUT / folder / f"frame_{i:02d}.png")
    print("ok")
