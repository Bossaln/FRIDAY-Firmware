"""Preview helpers: animated GIF (passive then active at real fps) and contact sheets.

Colours match tools/preview.py: lit pixels dark on Flipper orange.
"""
from PIL import Image

ON = (0x1B, 0x1B, 0x1B)
OFF = (0xFF, 0x82, 0x00)
GAP = 8


def colorize(img, scale=4):
    src = img.convert("1")
    out = Image.composite(
        Image.new("RGB", src.size, OFF), Image.new("RGB", src.size, ON), src.convert("L")
    )
    return out.resize((src.width * scale, src.height * scale), Image.NEAREST)


def gif(path, frames, order, fps, scale=4):
    """frames: list of PIL '1' images; order: list of indices played in sequence."""
    tiles = [colorize(f, scale) for f in frames]
    seq = [tiles[i] for i in order]
    # Collapse consecutive duplicates into longer durations to keep the GIF small
    out, durs = [], []
    for t in seq:
        if out and out[-1] is t:
            durs[-1] += 1000 // fps
        else:
            out.append(t)
            durs.append(1000 // fps)
    out[0].save(
        path, save_all=True, append_images=out[1:], duration=durs, loop=0, optimize=False
    )


def sheet(path, frames, scale=3, cols=6, labels=True):
    from PIL import ImageDraw

    tiles = [colorize(f, scale) for f in frames]
    w, h = tiles[0].size
    cols = min(cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * (w + GAP) + GAP, rows * (h + GAP) + GAP), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for i, t in enumerate(tiles):
        x, y = GAP + (i % cols) * (w + GAP), GAP + (i // cols) * (h + GAP)
        img.paste(t, (x, y))
        if labels:
            d.text((x + 2, y + 2), str(i), fill=(255, 255, 255))
    img.save(path)
