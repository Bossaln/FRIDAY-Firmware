"""Animation assembly: frame dedupe, meta.txt, manifest, previews."""
import pathlib

import numpy as np

from raster import to_image
import previewgif

HERE = pathlib.Path(__file__).resolve().parent
PACK = HERE.parents[2] / "assets" / "packs" / "FRIDAY" / "Anims"
PREVIEWS = HERE / "previews"
MAX_UNIQUE = 45


class Anim:
    def __init__(self, name, fps, active_cycles=1, cooldown=5, duration=300):
        self.name = name
        self.fps = fps
        self.active_cycles = active_cycles
        self.cooldown = cooldown
        self.duration = duration
        self.frames = []  # unique bool ink arrays
        self._index = {}
        self.passive = []
        self.active = []

    def _add(self, ink):
        key = np.packbits(ink).tobytes()
        if key not in self._index:
            self._index[key] = len(self.frames)
            self.frames.append(ink.copy())
        return self._index[key]

    def push(self, ink, hold=1, active=False):
        idx = self._add(ink)
        (self.active if active else self.passive).extend([idx] * hold)
        return idx

    # ------------------------------------------------------------------
    def check(self):
        total = len(self.passive) + len(self.active)
        assert total <= 255, f"{self.name}: frame order {total} > 255"
        assert len(self.frames) <= MAX_UNIQUE, f"{self.name}: {len(self.frames)} unique frames > {MAX_UNIQUE}"
        assert len(self.passive) > 0

    def meta(self):
        order = " ".join(map(str, self.passive + self.active))
        return (
            "Filetype: Flipper Animation\nVersion: 1\n\n"
            f"Width: 128\nHeight: 64\n"
            f"Passive frames: {len(self.passive)}\n"
            f"Active frames: {len(self.active)}\n"
            f"Frames order: {order}\n"
            f"Active cycles: {self.active_cycles}\n"
            f"Frame rate: {self.fps}\n"
            f"Duration: {self.duration}\n"
            f"Active cooldown: {self.cooldown}\n\n"
            "Bubble slots: 0\n"
        )

    def write(self):
        self.check()
        folder = PACK / f"{self.name}_128x64"
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("frame_*.png"):
            old.unlink()
        images = [to_image(f) for f in self.frames]
        for i, img in enumerate(images):
            img.save(folder / f"frame_{i}.png")
        (folder / "meta.txt").write_text(self.meta())
        PREVIEWS.mkdir(exist_ok=True)
        previewgif.gif(PREVIEWS / f"{self.name}.gif", images, self.passive + self.active, self.fps, scale=4)
        previewgif.sheet(PREVIEWS / f"{self.name}_sheet.png", images, scale=2, cols=6)
        return folder

    def summary(self):
        return (
            f"{self.name}: {len(self.frames)} unique frames, order {len(self.passive)}+{len(self.active)}"
            f"={len(self.passive) + len(self.active)}, {self.fps} fps"
        )


def write_manifest(anims):
    PACK.mkdir(parents=True, exist_ok=True)
    entries = []
    for a in anims:
        entries.append(
            f"Name: {a.name}_128x64\nMin butthurt: 0\nMax butthurt: 18\nMin level: 1\nMax level: 30\nWeight: 3\n"
        )
    (PACK / "manifest.txt").write_text("Filetype: Flipper Animation Manifest\nVersion: 1\n\n" + "\n".join(entries))
