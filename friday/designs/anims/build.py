#!/usr/bin/env python3
"""Build the FRIDAY desktop animation pack -> assets/packs/FRIDAY/Anims.

Run: python build.py             regenerates every animation, manifest and previews
     python build.py Idle Talk   only the named animations (no manifest update)

Each animation = passive loop + active reaction (button press on the desktop).
Frames are rendered procedurally (character.py + hud.py), de-duplicated and
written as frame_N.png + meta.txt. Previews land in ./previews.
"""
import math
import shutil
import sys

import numpy as np

import character as ch
import hud
from anim import PACK, Anim, write_manifest
from raster import H, PATTERNS, W

HUD_X = 83  # dotted rail separating figure and HUD column
CORE = (105, 29)  # HUD core ring centre


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def sway(i, n=16, amp=1.0, phase=0):
    """Ponytail sway -1..1 quantised to half steps over an n-frame cycle."""
    return round(math.sin(2 * math.pi * (i + phase) / n) * amp * 2) / 2


def breath(i, n=16):
    return 1.0 if (i % n) >= n // 2 else 0.0


def figure(pose):
    s, m = ch.render(pose)
    return s.ink, m


def dim(ink, m):
    """Low-power hologram: knock 25 % of the pixels out of the dark masses."""
    dark = m["back"] | m["tail"] | m["torso"] | m["bangs"] | m["side"]
    ink[dark & PATTERNS["dots25"]] = False


def core_ring(ink, i, r=15, burst=0.0, sweep=True):
    """Rotating HUD core: dashed outer ring, solid inner ring, ticks, radar sweep."""
    cx, cy = CORE
    phase = (i * 22.5) % 360
    hud.ring(ink, cx, cy, r, dash=(55, 35), phase=phase)
    hud.ring(ink, cx, cy, r - 4)
    hud.radial_ticks(ink, cx, cy, r - 3, r - 1.5, 4, phase=-phase * 2)
    if sweep:
        a = math.radians(phase * 3)
        hud.line(ink, cx, cy, cx + (r - 5) * math.cos(a), cy + (r - 5) * math.sin(a))
        for k in (1, 2):  # fading trail
            a2 = a - k * 0.35
            hud.put(ink, int(round(cx + (r - 6) * math.cos(a2))), int(round(cy + (r - 6) * math.sin(a2))))
            hud.put(ink, int(round(cx + (r - 9) * math.cos(a2))), int(round(cy + (r - 9) * math.sin(a2))))
    hud.put(ink, cx, cy)
    # orbiting particle outside the ring
    a = math.radians(phase * 1.5 + 90)
    hud.put(ink, int(round(cx + (r + 2) * math.cos(a))), int(round(cy + (r + 2) * math.sin(a))))
    if burst > 0:
        rr = r + 1 + burst * 9
        hud.ring(ink, cx, cy, rr, dash=(20, 25), phase=phase)
        if burst > 0.5:
            hud.ring(ink, cx, cy, rr - 4, dash=(10, 30), phase=-phase)


def readout(ink, label, i, bar=True):
    hud.text(ink, label, 126, 46, "small", align="right")
    if bar:
        hud.dotted_hline(ink, 86, 126, 52, step=2, phase=i)
        x = 86 + (i * 3) % 41
        hud.put(ink, x, 52)
        hud.put(ink, x, 53)


def rail(ink, i):
    hud.dotted_vline(ink, HUD_X, 14, 50, step=3, phase=i)


def tag(ink):
    hud.tag(ink, 127, 63)


# ---------------------------------------------------------------------------
# 1. IDLE  - she looks at you, blinks, glances, hair sways, HUD ticks
# ---------------------------------------------------------------------------

def anim_idle():
    a = Anim("FRIDAY_Idle", fps=8, cooldown=4)
    N, cycles = 16, 10

    def hud_frame(ink, m, i, burst=0.0, label=None):
        hud.scan_row(ink, m["all"], (i * 8) % 64)
        core_ring(ink, i, burst=burst)
        hud.bitstream(ink, 124, 14, 40, i, seed=3)
        readout(ink, label or ("SYS OK" if i < 8 else "CPU 12%"), i)
        rail(ink, i)
        tag(ink)

    def pose_for(c, i):
        p = ch.Pose(hair=sway(i, N), breath=breath(i, N), strand=sway(i, N, phase=4))
        if c in (1, 3, 7, 9):  # single blink
            p.eyes = {5: "half", 6: "closed", 7: "half"}.get(i, "open")
        if c == 5:  # double blink
            p.eyes = {5: "half", 6: "closed", 7: "half", 8: "closed", 9: "half"}.get(i, "open")
        if c == 4 and 8 <= i <= 13:  # glance left
            p.gaze = -1
            if i in (8, 13):
                p.eyes = "half"
        if c == 6 and 0 <= i <= 3:  # glance right
            p.gaze = 1
            if i in (0, 3):
                p.eyes = "half"
        if c == 8 and 2 <= i <= 5:  # a small smile
            p.mouth = "smirk" if i in (2, 5) else "smile"
        return p

    for c in range(cycles):
        for i in range(N):
            ink, m = figure(pose_for(c, i))
            hud_frame(ink, m, i)
            a.push(ink)

    # ACTIVE: she notices you - surprise, grin, wink, settles back smiling
    seq = [
        (ch.Pose(eyes="wide", brows="raised", mouth="open_o", hair=0.5), 0.2, "HEY!", 2),
        (ch.Pose(eyes="wide", brows="raised", mouth="open_o", hair=1.0), 0.6, "HEY!", 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", hair=0.5, blush=True), 1.0, "HEY!", 3),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", hair=0.0, blush=True), 0.0, "HEY!", 3),
        (ch.Pose(eyes="wink", mouth="smirk", hair=-0.5, blush=True), 0.0, "HELLO", 5),
        (ch.Pose(eyes="wink", mouth="smirk", hair=-1.0, blush=True), 0.0, "HELLO", 3),
        (ch.Pose(eyes="open", mouth="smile", hair=-0.5, blush=True), 0.0, "HELLO", 3),
        (ch.Pose(eyes="open", mouth="smile", hair=0.0, blush=True), 0.0, "SYS OK", 3),
        (ch.Pose(eyes="half", mouth="smile", hair=0.5), 0.0, "SYS OK", 1),
        (ch.Pose(eyes="open", mouth="neutral", hair=0.5), 0.0, "SYS OK", 2),
    ]
    for k, (p, burst, label, hold) in enumerate(seq):
        ink, m = figure(p)
        hud_frame(ink, m, 32 + k * 2, burst=burst, label=label)
        a.push(ink, hold, active=True)
    return a


# ---------------------------------------------------------------------------
# 2. SCAN  - targeting brackets lock on her, a scan line sweeps, she focuses
# ---------------------------------------------------------------------------

def anim_scan():
    a = Anim("FRIDAY_Scan", fps=8, cooldown=4)
    N = 16
    cx = int(ch.CX)
    bx0, by0, bx1, by1 = cx - 20, 6, cx + 20, 51

    def hud_frame(ink, m, i, pct, label, lock=False, burst=0.0):
        # targeting brackets around the face, breathing in/out by 1 px
        g = 1 if (i % 8) < 4 else 0
        if lock:
            hud.rect(ink, bx0 - 1, by0 - 1, bx1 + 1, by1 + 1)
            hud.corners(ink, bx0 - 3, by0 - 3, bx1 + 3, by1 + 3, 6)
        else:
            hud.corners(ink, bx0 - g, by0 - g, bx1 + g, by1 + g, 5)
        # vertical scan line sweeping across the figure (inverts her pixels)
        if not lock:
            x = bx0 + int(((i % N) / (N - 1)) * (bx1 - bx0))
            col = m["all"][:, x]
            ink[col, x] = ~ink[col, x]
            hud.dotted_vline(ink, x, by0, by1, step=2, phase=i)
            # horizontal dashed sweep, slower
            y = by0 + ((i * 3) % (by1 - by0))
            hud.dotted_hline(ink, bx0, bx1, y, step=3, phase=i)
        core_ring(ink, i, r=13, burst=burst)
        readout(ink, label, i, bar=False)
        # progress bar
        hud.rect(ink, 86, 52, 126, 54)
        w = int(pct / 100 * 39)
        if w:
            ink[53, 87:87 + w] = True
        hud.bitstream(ink, 124, 14, 40, i, seed=11, density=0.55)
        rail(ink, i)
        tag(ink)

    cycles = 4
    for c in range(cycles):
        for i in range(N):
            p = ch.Pose(brows="focused", hair=sway(i, N, 0.5), breath=breath(i, N), strand=sway(i, N, phase=4))
            # eyes follow the scan line
            p.gaze = -1 if i < 5 else (1 if i > 10 else 0)
            p.mouth = "hmm" if c % 2 else "neutral"
            if c == 1 and i in (7, 8):
                p.eyes = "closed" if i == 7 else "half"
            if c == 3 and i in (2, 3):
                p.eyes = "half"
            pct = int(100 * i / (N - 1))
            label = f"SCAN {pct:02d}%" if c % 2 == 0 else f"ID {pct * 37 % 100:02d}{i:X}"
            ink, m = figure(p)
            hud_frame(ink, m, i, pct, label)
            a.push(ink)

    # ACTIVE: lock-on + match - she lights up
    seq = [
        (ch.Pose(brows="raised", eyes="wide", mouth="hmm", hair=0.5), True, 100, "LOCK", 0.3, 2),
        (ch.Pose(brows="raised", eyes="wide", mouth="open_o", hair=1.0), True, 100, "LOCK", 0.7, 2),
        (ch.Pose(brows="raised", eyes="open", mouth="smile", hair=0.5), True, 100, "MATCH", 1.0, 3),
        (ch.Pose(brows="raised", eyes="smile", mouth="grin", hair=0.0, head_dy=1), True, 100, "MATCH", 0.0, 4),
        (ch.Pose(brows="neutral", eyes="smile", mouth="grin", hair=-0.5, head_dy=0), False, 100, "MATCH", 0.0, 3),
        (ch.Pose(brows="neutral", eyes="open", mouth="smile", hair=-1.0), False, 100, "100%", 0.0, 3),
        (ch.Pose(brows="neutral", eyes="open", mouth="smile", hair=-0.5), False, 100, "100%", 0.0, 3),
        (ch.Pose(brows="focused", eyes="open", mouth="neutral", hair=0.0), False, 0, "SCAN 00%", 0.0, 2),
    ]
    for k, (p, lock, pct, label, burst, hold) in enumerate(seq):
        ink, m = figure(p)
        hud_frame(ink, m, 40 + k * 2, pct, label, lock=lock, burst=burst)
        a.push(ink, hold, active=True)
    return a


# ---------------------------------------------------------------------------
# 3. BOOT  - hologram materialises from noise, glitches, stabilises, fades out
# ---------------------------------------------------------------------------

def anim_boot():
    a = Anim("FRIDAY_Boot", fps=8, cooldown=4)
    N = 16

    def hud_frame(ink, i, label, pct, heavy=False):
        core_ring(ink, i, r=13, sweep=not heavy)
        readout(ink, label, i, bar=False)
        hud.rect(ink, 86, 52, 126, 54)
        w = int(pct / 100 * 39)
        if w:
            ink[53, 87:87 + w] = True
        hud.bitstream(ink, 124, 14, 40, i * (3 if heavy else 1), seed=5, density=0.6 if heavy else 0.4)
        rail(ink, i)
        tag(ink)

    base = ch.Pose()
    stages = ["INIT", "INIT", "CORE", "CORE", "CORE", "SYNC", "SYNC", "SYNC", "LINK", "LINK"]
    # empty projector field with sparse noise
    for k in range(2):
        ink = np.zeros((H, W), bool)
        _, m = figure(base)
        hud.noise(ink, m["all"], 0.04 * (k + 1), seed=100 + k, color=True)
        hud.scanlines(ink, m["all"], every=2, phase=k)
        hud.dotted_hline(ink, 4, 80, 62, step=4, phase=k)  # projector base line
        hud_frame(ink, k, stages[k], 5 * k, heavy=True)
        a.push(ink, 2)
    # materialise bottom-up with noise and raster lines
    steps = 8
    for k in range(steps):
        frac = (k + 1) / steps
        ink, m = figure(base.replace(hair=sway(k, 8, 0.5)))
        hud.reveal_rows(ink, m["all"], frac, seed=k, fuzz=8)
        hud.noise(ink, m["all"], 0.25 * (1 - frac) + 0.03, seed=200 + k)
        hud.scanlines(ink, m["all"], every=2 if k < 5 else 3, phase=k % 2)
        if k in (2, 5):
            hud.glitch(ink, [(14 + k * 3, 20 + k * 3, 3), (30 + k, 34 + k, -2)], m["all"])
        hud.dotted_hline(ink, 4, 80, 62, step=4, phase=k)
        hud_frame(ink, 2 + k, stages[2 + k], 10 + int(80 * frac), heavy=True)
        a.push(ink, 1)
    # two glitch frames as the projection snaps into focus
    for k, slices in enumerate(([(10, 16, 4), (26, 31, -3), (44, 48, 2)], [(20, 24, -4), (36, 40, 3)])):
        ink, m = figure(base.replace(eyes="half" if k == 0 else "open", hair=0.5))
        hud.glitch(ink, slices, m["all"])
        hud.scanlines(ink, m["all"], every=3, phase=k)
        hud_frame(ink, 10 + k, "LINK", 95, heavy=True)
        a.push(ink, 1)
    # stable: ONLINE, she blinks and smiles briefly
    for i in range(N):
        p = ch.Pose(hair=sway(i, N), breath=breath(i, N), strand=sway(i, N, phase=4))
        if i in (3, 4, 5):
            p.eyes = {3: "half", 4: "closed", 5: "half"}[i]
        if 9 <= i <= 13:
            p.mouth = "smile" if i in (10, 11, 12) else "smirk"
        ink, m = figure(p)
        hud.scan_row(ink, m["all"], (i * 8) % 64)
        hud_frame(ink, 12 + i, "ONLINE", 100)
        a.push(ink, 2)
    # flicker + dematerialise (loop point)
    for k, slices in enumerate(([(18, 22, 3), (40, 44, -3)], [(8, 12, -2), (28, 33, 4), (50, 54, -3)])):
        ink, m = figure(ch.Pose(hair=0.5, eyes="half" if k else "open"))
        hud.glitch(ink, slices, m["all"])
        hud.scanlines(ink, m["all"], every=3, phase=k)
        hud_frame(ink, 28 + k, "RESYNC", 100, heavy=True)
        a.push(ink, 1)
    for k in range(5):
        frac = 1 - (k + 1) / 5
        ink, m = figure(ch.Pose(hair=0.0, eyes="closed"))
        hud.reveal_rows(ink, m["all"], frac, seed=300 + k, fuzz=8)
        hud.noise(ink, m["all"], 0.2 * (1 - frac), seed=400 + k)
        hud.scanlines(ink, m["all"], every=2, phase=k % 2)
        hud.dotted_hline(ink, 4, 80, 62, step=4, phase=k)
        hud_frame(ink, 30 + k, "RESYNC", int(100 * frac), heavy=True)
        a.push(ink, 1)

    # ACTIVE: a hard glitch burst, then she grins at you - fully stable
    seq = [
        (ch.Pose(eyes="wide", brows="raised", mouth="hmm", hair=1.0), [(6, 12, -5), (22, 27, 4), (38, 44, -3), (52, 58, 5)], "ERR", 1),
        (ch.Pose(eyes="wide", brows="raised", mouth="open_o", hair=0.5), [(14, 20, 5), (30, 36, -4), (46, 50, 3)], "ERR", 1),
        (ch.Pose(eyes="half", brows="raised", mouth="open_o", hair=0.0), [(26, 30, 2)], "RESYNC", 1),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", hair=-0.5, blush=True), [], "ONLINE", 4),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", hair=-1.0, blush=True), [], "ONLINE", 4),
        (ch.Pose(eyes="wink", brows="neutral", mouth="smile", hair=-0.5, blush=True), [], "HELLO", 4),
        (ch.Pose(eyes="open", brows="neutral", mouth="smile", hair=0.0), [], "HELLO", 3),
        (ch.Pose(eyes="open", brows="neutral", mouth="neutral", hair=0.5), [], "ONLINE", 2),
    ]
    for k, (p, slices, label, hold) in enumerate(seq):
        ink, m = figure(p)
        if slices:
            hud.glitch(ink, slices, m["all"])
            hud.scanlines(ink, m["all"], every=3, phase=k)
        hud_frame(ink, 40 + k * 2, label, 100, heavy=bool(slices))
        a.push(ink, hold, active=True)
    return a


# ---------------------------------------------------------------------------
# 4. TALK  - she speaks, mouth shapes + voice equalizer, eyes alive
# ---------------------------------------------------------------------------

VISEMES_A = ["open_a", "open_o", "open_e", "hmm", "open_a", "neutral", "open_o", "open_e",
             "open_a", "hmm", "neutral", "open_o", "open_a", "open_e", "neutral", "neutral"]
VISEMES_B = ["open_o", "open_e", "open_a", "neutral", "open_e", "open_o", "hmm", "open_a",
             "open_e", "open_a", "open_o", "neutral", "hmm", "open_e", "open_a", "neutral"]
LINES = ["ANALYZING", "ALL NOMINAL", "READY", "LISTENING"]


def eq_heights(i, n_bars, seed, energy=1.0):
    rng = np.random.default_rng(seed + i)
    h = []
    for b in range(n_bars):
        env = math.sin(math.pi * (b + 0.5) / n_bars) ** 0.6
        v = (0.35 + 0.65 * rng.random()) * env * energy
        h.append(max(0, round(v * 11)))
    return h


def anim_talk():
    a = Anim("FRIDAY_Talk", fps=8, cooldown=4)
    N = 16
    n_bars = 14

    def hud_frame(ink, i, mouth, label, energy=1.0, laugh=False):
        quiet = mouth in ("neutral", "hmm", "smile", "grin", "smirk") and not laugh
        heights = eq_heights(i, n_bars, 77, energy * (0.25 if quiet else 1.0))
        hud.bars(ink, 85, 28, heights, w=2, gap=1, up=None)
        hud.dotted_hline(ink, 85, 126, 28, step=2, phase=i)
        hud.corners(ink, 84, 14, 127, 42, 3)
        readout(ink, label, i)
        rail(ink, i)
        tag(ink)

    for c in range(2):
        vis = VISEMES_A if c == 0 else VISEMES_B
        for i in range(N):
            p = ch.Pose(mouth=vis[i], hair=sway(i, N, 0.5, phase=c * 4), breath=breath(i, N), strand=sway(i, N, phase=4))
            if c == 0:
                p.gaze = -1 if 6 <= i <= 9 else 0
                p.brows = "raised" if i in (4, 5, 12, 13) else "neutral"
                if i == 14:
                    p.eyes = "closed"
            else:
                p.gaze = 1 if 2 <= i <= 5 else 0
                p.brows = "raised" if 8 <= i <= 10 else "neutral"
                p.head_dx = 1 if 9 <= i <= 12 else 0
                if i in (6, 15):
                    p.eyes = "half"
            ink, m = figure(p)
            hud.scan_row(ink, m["all"], (i * 8) % 64)
            hud_frame(ink, c * N + i, vis[i], LINES[(c * 2 + i // 8) % len(LINES)])
            a.push(ink, 1)

    # ACTIVE: she laughs - head bobs, eyes crease, equalizer spikes
    seq = [
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", head_dy=-1, hair=0.5, blush=True), 1.3, "HAHA", 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="open_a", head_dy=1, hair=1.0, blush=True), 1.5, "HAHA", 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", head_dy=-1, hair=0.5, blush=True), 1.3, "HAHA", 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="open_a", head_dy=1, hair=0.0, blush=True), 1.5, "HAHA", 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", head_dy=0, hair=-0.5, blush=True), 1.0, "HAHA", 3),
        (ch.Pose(eyes="wink", brows="neutral", mouth="smirk", head_dy=0, hair=-1.0, blush=True), 0.4, "CUTE", 4),
        (ch.Pose(eyes="open", brows="neutral", mouth="smile", head_dy=0, hair=-0.5), 0.2, "READY", 3),
        (ch.Pose(eyes="open", brows="neutral", mouth="neutral", head_dy=0, hair=0.0), 0.2, "READY", 2),
    ]
    for k, (p, energy, label, hold) in enumerate(seq):
        ink, m = figure(p)
        hud_frame(ink, 40 + k * 3, p.mouth, label, energy=energy, laugh=k < 5)
        a.push(ink, hold, active=True)
    return a


# ---------------------------------------------------------------------------
# 5. STANDBY - low-power mode: eyes closed, slow breathing, dim hologram
# ---------------------------------------------------------------------------

def anim_standby():
    a = Anim("FRIDAY_Standby", fps=4, cooldown=4)
    N = 16

    def hud_frame(ink, m, i, label, pulse, dimmed=True, burst=0.0):
        if dimmed:
            dim(ink, m)
        cx, cy = CORE
        hud.ring(ink, cx, cy, 11, dash=(30, 60), phase=i * 6)
        hud.ring(ink, cx, cy, 4 + pulse, dash=(40, 40) if pulse > 2 else None, phase=i * 10)
        hud.put(ink, cx, cy)
        if burst > 0:
            hud.ring(ink, cx, cy, 13 + burst * 8, dash=(25, 20), phase=i * 10)
        readout(ink, label, i, bar=False)
        hud.dotted_hline(ink, 86, 126, 52, step=4, phase=i)
        hud.bitstream(ink, 124, 14, 40, i // 2, seed=9, density=0.2)
        rail(ink, i)
        tag(ink)

    for c in range(3):
        for i in range(N):
            p = ch.Pose(eyes="closed", mouth="neutral", hair=sway(i, N, 0.5), breath=breath(i, N),
                        head_dy=1 if 4 <= i <= 11 else 0, strand=sway(i, N, phase=4))
            if c == 1 and i in (12, 13):
                p.eyes = "down"  # a drowsy peek
            label = "STANDBY" if (i // 8) % 2 == 0 else "LOW PWR"
            pulse = [0, 1, 2, 3, 4, 3, 2, 1][(i // 2) % 8]
            ink, m = figure(p)
            hud_frame(ink, m, i, label, pulse)
            a.push(ink)

    # ACTIVE: wake up - eyes open, brows up, bright hologram, ONLINE
    seq = [
        (ch.Pose(eyes="down", brows="neutral", mouth="neutral", hair=0.5, head_dy=1), True, "WAKE", 0.0, 1),
        (ch.Pose(eyes="half", brows="raised", mouth="neutral", hair=1.0, head_dy=0), True, "WAKE", 0.3, 1),
        (ch.Pose(eyes="wide", brows="raised", mouth="open_o", hair=0.5, head_dy=0), False, "WAKE", 0.8, 2),
        (ch.Pose(eyes="open", brows="raised", mouth="smile", hair=0.0, head_dy=0), False, "ONLINE", 1.0, 2),
        (ch.Pose(eyes="smile", brows="raised", mouth="grin", hair=-0.5, head_dy=0, blush=True), False, "ONLINE", 0.0, 3),
        (ch.Pose(eyes="open", brows="neutral", mouth="smile", hair=-1.0, head_dy=0), False, "ONLINE", 0.0, 2),
        (ch.Pose(eyes="open", brows="neutral", mouth="smile", hair=-0.5, head_dy=0), False, "READY", 0.0, 2),
        (ch.Pose(eyes="half", brows="neutral", mouth="neutral", hair=0.0, head_dy=0), True, "STANDBY", 0.0, 1),
    ]
    for k, (p, dimmed, label, burst, hold) in enumerate(seq):
        ink, m = figure(p)
        hud_frame(ink, m, 50 + k * 3, label, 2, dimmed=dimmed, burst=burst)
        a.push(ink, hold, active=True)
    return a




# ---------------------------------------------------------------------------
# 6. CLOSEUP - zoomed portrait, retina scan line, she looks right at you
# ---------------------------------------------------------------------------

def anim_closeup():
    a = Anim("FRIDAY_Closeup", fps=8, cooldown=4)
    N, cycles = 16, 6
    xf = ch.Xf(z=1.6, oy=-7)

    def hud_frame(ink, m, i, label, burst=0.0):
        # retina scan: dotted line sweeping over the eye band, inverting her pixels
        y = 14 + (i * 2) % 26
        hud.scan_row(ink, m["all"], y, dotted=False)  # light line through the hair
        hud.dotted_hline(ink, 2, 125, y, step=3, phase=i)
        hud.corners(ink, 1, 13, 126, 62, 5)
        hud.text(ink, label, 126, 46, "small", align="right")
        hud.text(ink, f"{(i * 7) % 100:02d}.{(i * 3) % 10}", 126, 53, "small", align="right")
        hud.bitstream(ink, 122, 30, 42, i, seed=21, cols=3, density=0.4)
        if burst > 0:
            hud.ring(ink, 64, 32, 20 + burst * 40, dash=(12, 18), phase=i * 9)
        tag(ink)

    def pose_for(c, i):
        p = ch.Pose(xf=xf, hair=sway(i, N, 0.5), breath=breath(i, N), strand=sway(i, N, phase=4))
        if c in (1, 4):
            p.eyes = {6: "half", 7: "closed", 8: "half"}.get(i, "open")
        if c == 2 and 3 <= i <= 8:  # slow glance left (2 px in close-up)
            p.gaze = -2 if 4 <= i <= 7 else -1
        if c == 3 and 9 <= i <= 13:
            p.gaze = 2 if 10 <= i <= 12 else 1
        if c == 5 and 4 <= i <= 9:
            p.mouth = "smirk" if i in (4, 9) else "smile"
            p.eyes = "half" if i in (6, 7) else "open"
        return p

    for c in range(cycles):
        for i in range(N):
            ink, m = figure(pose_for(c, i))
            hud_frame(ink, m, i, "IRIS OK" if i < 8 else "FOCUS 98%")
            a.push(ink)

    seq = [
        (ch.Pose(xf=xf, eyes="wide", brows="raised", mouth="hmm", hair=0.5), 0.2, "ALERT", 2),
        (ch.Pose(xf=xf, eyes="wide", brows="raised", mouth="open_o", hair=1.0), 0.6, "ALERT", 2),
        (ch.Pose(xf=xf, eyes="open", brows="raised", mouth="smile", hair=0.5), 1.0, "USER", 3),
        (ch.Pose(xf=xf, eyes="smile", brows="raised", mouth="grin", hair=0.0, blush=True), 0.0, "HELLO", 4),
        (ch.Pose(xf=xf, eyes="wink", brows="neutral", mouth="smirk", hair=-0.5, blush=True), 0.0, "HELLO", 5),
        (ch.Pose(xf=xf, eyes="open", brows="neutral", mouth="smile", hair=-1.0), 0.0, "HELLO", 3),
        (ch.Pose(xf=xf, eyes="half", brows="neutral", mouth="smile", hair=-0.5), 0.0, "IRIS OK", 1),
        (ch.Pose(xf=xf, eyes="open", brows="neutral", mouth="neutral", hair=0.0), 0.0, "IRIS OK", 2),
    ]
    for k, (p, burst, label, hold) in enumerate(seq):
        ink, m = figure(p)
        hud_frame(ink, m, 40 + k * 2, label, burst=burst)
        a.push(ink, hold, active=True)
    return a


# ---------------------------------------------------------------------------

ANIMS = {"Idle": anim_idle, "Scan": anim_scan, "Boot": anim_boot, "Talk": anim_talk, "Standby": anim_standby,
         "Closeup": anim_closeup}


def main(argv):
    names = argv[1:] or list(ANIMS)
    built = []
    for n in names:
        a = ANIMS[n]()
        a.write()
        print(a.summary())
        built.append(a)
    if not argv[1:]:
        keep = {f"{a.name}_128x64" for a in built}
        for d in PACK.iterdir():
            if d.is_dir() and d.name not in keep:
                shutil.rmtree(d)
        write_manifest(built)
        print(f"manifest: {len(built)} animations -> {PACK}")


if __name__ == "__main__":
    main(sys.argv)
