"""Original score and sound design, synthesised from scratch in NumPy.

No samples, loops or third-party recordings are used. Every sound below is
generated from oscillators and noise, so the music is original to this entry.

Reads build/timeline.json (scene start times and sound cues).
Writes build/audio/music.wav and build/audio/sfx.wav (48 kHz stereo).
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parents[2]
SR = 48000
BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
RNG = np.random.default_rng(20261030)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def note(name):
    names = {"C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
    p, o = (name[:2], name[2:]) if name[:2] in names else (name[:1], name[1:])
    return 12 * (int(o) + 1) + names[p]


# ---------------------------------------------------------------- oscillators
def saw_table(f, cutoff, n=4096):
    """One cycle of a band-limited, softly low-passed saw for fundamental f."""
    k = np.arange(1, max(2, int(min(cutoff * 1.6, SR / 2 - 200) / f)) + 1)
    amp = (1.0 / k) / np.sqrt(1 + (k * f / cutoff) ** 4)
    ph = np.arange(n) / n
    return (np.sin(2 * np.pi * np.outer(ph, k)) @ amp).astype(np.float32)


def table_osc(table, f, n, phase0=0.0):
    N = len(table)
    ph = (phase0 + f * np.arange(n) / SR) % 1.0 * N
    i = ph.astype(int)
    fr = ph - i
    return table[i] * (1 - fr) + table[(i + 1) % N] * fr


def adsr(n, a, d, s, r, hold):
    """Envelope with a hold section of `hold` seconds then release r."""
    t = np.arange(n) / SR
    env = np.where(t < a, t / max(a, 1e-6), 1.0)
    env = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-6), env)
    env = np.where((t >= a + d), s, env)
    rel = t >= hold
    env[rel] = env[rel] * np.exp(-(t[rel] - hold) / max(r / 4.0, 1e-3))
    return env


def lowpass(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="low", fs=SR, output="sos"), x, axis=0)


def highpass(x, fc, order=2):
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x, axis=0)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x, axis=0)


def place(buf, x, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def pan(x, p):
    """Equal-power pan, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


# ---------------------------------------------------------------- instruments
def pad_note(m, dur, cutoff, level=1.0):
    f = hz(m)
    n = int((dur + 2.6) * SR)
    out = np.zeros((n, 2), np.float32)
    for i, c in enumerate([-11, -5, 0, 6, 12]):
        ff = f * 2 ** (c / 1200)
        tab = saw_table(ff, cutoff)
        x = table_osc(tab, ff, n, RNG.random())
        out += pan(x, [-0.8, -0.35, 0.0, 0.35, 0.8][i])
    env = adsr(n, 1.1, 0.8, 0.85, 2.4, dur)
    return out * env[:, None] * (0.055 * level)


def pluck(m, level=1.0, bright=1.0):
    f = hz(m)
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 11):
        if k * f > SR / 2.2:
            break
        x += (1 / k ** 1.35) * np.sin(2 * np.pi * k * f * t + 0.3 * k) * np.exp(-t * (2.6 + 2.2 * k / bright))
    x *= np.minimum(1, t / 0.003)
    return (x * 0.16 * level).astype(np.float32)


def bass_note(m, dur, level=1.0):
    f = hz(m)
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = adsr(n, 0.012, 0.25, 0.7, 0.3, dur)
    return (np.tanh(1.4 * x) * env * 0.22 * level).astype(np.float32)


def kick(level=1.0):
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 44 + 88 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 6.5)
    click = highpass(RNG.standard_normal(n) * np.exp(-t * 900), 2500) * 0.18
    return ((np.tanh(1.6 * x) + click) * 0.42 * level).astype(np.float32)


def hat(level=1.0, open_=False):
    n = int((0.35 if open_ else 0.09) * SR)
    t = np.arange(n) / SR
    x = highpass(RNG.standard_normal(n), 7200, 4) * np.exp(-t * (14 if open_ else 70))
    return (x * 0.05 * level).astype(np.float32)


def snap(level=1.0):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 32) + 0.6 * np.exp(-np.maximum(0, t - 0.011) * 40) * (t > 0.011)
    x = bandpass(RNG.standard_normal(n), 1100, 5200) * env
    return (x * 0.12 * level).astype(np.float32)


def reverb_ir(seconds=2.4, predelay=0.018, damp=4500):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    decay = np.exp(-6.9 * t / seconds)
    ir = np.stack([RNG.standard_normal(n), RNG.standard_normal(n)], axis=1) * decay[:, None]
    ir = lowpass(ir, damp, 1)
    ir = np.concatenate([np.zeros((int(predelay * SR), 2)), ir])
    return (ir / np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))).astype(np.float32)


def reverb(x, ir, mix):
    wet = np.stack([fftconvolve(x[:, 0], ir[:, 0])[: len(x)], fftconvolve(x[:, 1], ir[:, 1])[: len(x)]], axis=1)
    return x + wet * mix


def pingpong(x, delay, fb, mix):
    out = x.copy()
    d = int(delay * SR)
    left, right = x[:, 0].copy(), x[:, 1].copy()
    g = mix
    for i in range(1, 7):
        src = right if i % 2 else left
        sh = np.zeros_like(src)
        sh[d * i:] = (x[:, 0] + x[:, 1])[: len(src) - d * i] * 0.5
        out[:, i % 2] += lowpass(sh, 3800, 1) * g
        g *= fb
    return out


# ---------------------------------------------------------------- arrangement
CHORDS = {
    "Dm9":     (["D3", "F3", "A3", "C4", "E4"], "D2"),
    "Bbmaj7":  (["Bb2", "D3", "F3", "A3", "C4"], "Bb1"),
    "Fadd9":   (["F3", "C4", "G4", "A4"], "F2"),
    "Csus":    (["C3", "G3", "D4", "E4"], "C2"),
    "Dm7":     (["D3", "A3", "C4", "F4"], "D2"),
    "Bbmaj9":  (["Bb2", "F3", "A3", "C4", "D4"], "Bb1"),
    "Gm7":     (["G2", "D3", "F3", "Bb3"], "G1"),
    "C":       (["C3", "G3", "C4", "E4"], "C2"),
    "F":       (["F2", "C3", "F3", "A3", "C4", "G4"], "F1"),
}


def build_music(tl):
    total = tl["duration"]
    n = int((total + 3.0) * SR)
    pads = np.zeros((n, 2), np.float32)
    plk = np.zeros((n, 2), np.float32)
    bass = np.zeros((n, 2), np.float32)
    drums = np.zeros((n, 2), np.float32)
    kick_env = np.zeros(n, np.float32)

    s = {sc["id"]: sc for sc in tl["scenes"]}
    # The groove lands exactly on the Redbelly reveal; the bar grid is anchored there.
    reveal = s["onestep"]["start"]
    first_bar = reveal - BAR * np.ceil(reveal / BAR)
    bars = np.arange(first_bar, total + BAR, BAR)

    def section(t):
        for sc in reversed(tl["scenes"]):
            if t >= sc["start"] - 0.05:
                return sc["id"]
        return "hook"

    close_t = s["close"]["start"]
    end_hit = tl["cues"]["endcard"]
    intro_prog = ["Dm9", "Dm9", "Bbmaj7", "Bbmaj7"]
    main_prog = ["Fadd9", "Csus", "Dm7", "Bbmaj9"]
    proof_prog = ["Bbmaj9", "Fadd9", "Gm7", "Csus"]

    for bi, b0 in enumerate(bars):
        if b0 >= end_hit - 0.01:
            break
        sec = section(max(0.0, b0 + 0.01))
        if b0 + BAR <= 0:
            continue
        if sec in ("hook", "problem"):
            ch = intro_prog[bi % 4]
            cutoff, lvl = (850, 0.85) if sec == "hook" else (1100, 0.95)
        elif sec == "proof":
            ch = proof_prog[bi % 4]
            cutoff, lvl = 2400, 1.0
        elif sec == "close":
            ch = ["Bbmaj9", "Csus", "Bbmaj9", "Csus"][bi % 4]
            cutoff, lvl = 2600, 1.05
        else:
            ch = main_prog[bi % 4]
            cutoff, lvl = 2000 if sec == "onestep" else 2300, 1.0
        notes, root = CHORDS[ch]
        bar_end = min(b0 + BAR, end_hit)
        dur = bar_end - b0
        for m in notes:
            x = pad_note(note(m), dur, cutoff, lvl)
            if b0 < 0:
                x = x[int(-b0 * SR):]
            place(pads, x, max(0.0, b0))

        groove = sec in ("onestep", "people", "rules", "assets", "proof")
        if sec == "problem" or groove:
            # bass: steady eighths in the groove, a soft pulse in the problem scene
            steps = [0, 1.5, 2, 3, 3.5] if groove else [0, 2]
            for st in steps:
                tt = b0 + st * BEAT
                if 0 <= tt < bar_end:
                    place(bass, pan(bass_note(note(root) + 12 * (st == 3.5), BEAT * 0.9, 0.9 if groove else 0.6), 0), tt)
        if groove or sec in ("hook", "problem", "close"):
            # plucked arpeggio, sparse in the intro and the close, eighths in the groove
            tones = sorted(note(m) for m in notes)
            arp = [tones[0] + 12, tones[2] + 12, tones[-1] + 12, tones[1] + 12, tones[2] + 12, tones[-1] + 12, tones[1] + 24, tones[2] + 12]
            grid = range(8) if groove else ([0, 3, 6] if sec != "close" else [0, 2, 4, 6])
            for i in grid:
                tt = b0 + i * BEAT / 2
                if 0 <= tt < bar_end:
                    lv = (0.75 if i % 2 else 1.0) * (0.55 if not groove else 0.85)
                    place(plk, pan(pluck(arp[i], lv, 1.0 if groove else 0.7), [-0.45, 0.45][i % 2]), tt)
        if groove:
            for beat in range(4):
                tt = b0 + beat * BEAT
                if 0 <= tt < bar_end:
                    if beat in (0, 2) or (sec in ("assets", "proof") and beat == 3 and bi % 2):
                        k = kick(0.95 if beat == 0 else 0.8)
                        place(drums, pan(k, 0), tt)
                        e = np.exp(-np.arange(int(0.35 * SR)) / SR * 9.0).astype(np.float32)
                        place(kick_env, e, tt)
                    if beat in (1, 3) and sec != "onestep":
                        place(drums, pan(snap(0.8), 0.1), tt)
                for h in range(2):
                    th = tt + h * BEAT / 2
                    if 0 <= th < bar_end:
                        place(drums, pan(hat(0.9 if h else 0.55), 0.3), th)
        elif sec == "problem":
            # a quiet ticking clock under the reconciliation scene
            for beat in range(4):
                tt = b0 + beat * BEAT
                if 0 <= tt < bar_end:
                    place(drums, pan(hat(0.7), -0.25 if beat % 2 else 0.25), tt)

    # final resolve on F on the end card
    for m in CHORDS["F"][0]:
        place(pads, pad_note(note(m), 3.2, 2400, 1.15), end_hit)
    place(bass, pan(bass_note(note("F1"), 2.4, 1.0), 0), end_hit)
    for i, m in enumerate(["F5", "A5", "C6", "F6"]):
        place(plk, pan(pluck(note(m), 0.6, 0.9), [-0.3, 0.3, -0.15, 0.15][i]), end_hit + i * 0.09)

    duck = 1.0 - 0.32 * np.clip(kick_env, 0, 1)
    pads *= duck[:, None]
    bass *= (1.0 - 0.45 * np.clip(kick_env, 0, 1))[:, None]

    plk = pingpong(plk, 0.75 * BEAT, 0.42, 0.33)
    ir = reverb_ir()
    mix = reverb(pads, ir, 0.45) + reverb(plk, ir, 0.35) + bass + reverb(drums, ir, 0.12)
    mix = highpass(mix, 32, 2)
    # gentle fade in and a natural tail after the end card
    t = np.arange(len(mix)) / SR
    mix *= np.clip(t / 1.2, 0, 1)[:, None]
    tail = end_hit + 2.9
    mix *= np.where(t > tail, np.exp(-(t - tail) / 0.6), 1.0)[:, None]
    return np.tanh(mix * 1.1) / 1.1


# ---------------------------------------------------------------- sound effects
def sfx_whoosh(d=0.7, up=True, level=1.0):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = RNG.standard_normal(n)
    out = np.zeros(n)
    seg = 512
    for i in range(0, n, seg):
        p = i / n
        fc = 300 + (3800 if up else 3800 * (1 - p)) * (p if up else 1)
        out[i:i + seg] = bandpass(x[max(0, i - 2048):i + seg], max(80, fc * 0.6), min(SR / 2.2, fc * 1.5))[-len(x[i:i + seg]):]
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return pan((out * env * 0.09 * level).astype(np.float32), 0)


def sfx_tick(level=1.0, f=2100):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 90)
    return pan((x * 0.07 * level).astype(np.float32), 0)


def sfx_chime(level=1.0, base="C6"):
    out = None
    for i, m in enumerate([note(base), note(base) + 7]):
        n = int(1.4 * SR)
        t = np.arange(n) / SR
        f = hz(m)
        x = (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 8)) * np.exp(-t * 3.2)
        x *= np.minimum(1, t / 0.002)
        x = np.concatenate([np.zeros(int(i * 0.075 * SR)), x])[:n]
        out = x if out is None else out + x
    return pan((out * 0.06 * level).astype(np.float32), 0)


def sfx_deny(level=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * (150 - 50 * t) * t) * np.exp(-t * 9)
    x += 0.35 * np.sign(np.sin(2 * np.pi * 92 * t)) * np.exp(-t * 18)
    return pan((lowpass(x, 1400) * 0.12 * level).astype(np.float32), 0)


def sfx_lock(level=1.0):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    click = highpass(RNG.standard_normal(n), 3000) * np.exp(-t * 400)
    thump = np.sin(2 * np.pi * (180 * np.exp(-t * 20) + 60) * t) * np.exp(-t * 22)
    return pan(((0.35 * click + thump) * 0.13 * level).astype(np.float32), 0)


def sfx_pop(level=1.0, f=900):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * (1 + 0.6 * np.exp(-t * 40)) * t) * np.exp(-t * 38)
    return pan((x * 0.06 * level).astype(np.float32), 0)


def sfx_impact(level=1.0):
    n = int(2.5 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 12)) * t) * np.exp(-t * 2.2)
    air = lowpass(RNG.standard_normal(n), 2500) * np.exp(-t * 5) * 0.25
    return pan(((sub + air) * 0.16 * level).astype(np.float32), 0)


SFX = {
    "whoosh": lambda: sfx_whoosh(0.6, True),
    "whoosh_long": lambda: sfx_whoosh(1.0, True, 1.1),
    "whoosh_down": lambda: sfx_whoosh(0.7, False, 0.8),
    "tick": lambda: sfx_tick(1.0),
    "tick_soft": lambda: sfx_tick(0.6, 1700),
    "chime": lambda: sfx_chime(1.0),
    "chime_low": lambda: sfx_chime(0.8, "G5"),
    "deny": lambda: sfx_deny(1.0),
    "lock": lambda: sfx_lock(1.0),
    "pop": lambda: sfx_pop(1.0),
    "pop_high": lambda: sfx_pop(0.8, 1300),
    "impact": lambda: sfx_impact(1.0),
}


def build_sfx(tl):
    n = int((tl["duration"] + 3.0) * SR)
    out = np.zeros((n, 2), np.float32)
    for c in tl["sfx"]:
        place(out, SFX[c["sound"]]() * c.get("gain", 1.0), c["t"])
    ir = reverb_ir(1.4, 0.01, 6000)
    return reverb(out, ir, 0.18)


def main():
    tl = json.loads((ROOT / "build" / "timeline.json").read_text())
    out = ROOT / "build" / "audio"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "music.wav", build_music(tl).astype(np.float32), SR, subtype="FLOAT")
    sf.write(out / "sfx.wav", build_sfx(tl).astype(np.float32), SR, subtype="FLOAT")
    print("music and sfx written")


if __name__ == "__main__":
    main()
