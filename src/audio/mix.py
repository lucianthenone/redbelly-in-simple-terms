"""Mix narration, score and sound effects, then master for social video.

Targets: narration stem -16 LUFS, music bed sits about 11 LU under the voice
and ducks a further 5 dB while someone is speaking. Final master -14 LUFS
integrated, true peak limited to -1.5 dBTP so it stays below -1 dBTP after AAC
encoding (two pass EBU R128 in ffmpeg).

Writes build/audio/narration.wav, build/audio/mix.wav, build/audio/final.wav
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[2]
SR = 48000


def db(x):
    return 10 ** (x / 20)


def peaking(x, f0, gain_db, q):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * a, -2 * np.cos(w), 1 - al * a]
    aa = [1 + al / a, -2 * np.cos(w), 1 - al / a]
    sos = np.array([[b[0] / aa[0], b[1] / aa[0], b[2] / aa[0], 1, aa[1] / aa[0], aa[2] / aa[0]]])
    return sosfilt(sos, x, axis=0)


def envelope(x, attack, release):
    e = np.zeros_like(x)
    ga, gr = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    v = 0.0
    for i, s in enumerate(np.abs(x)):
        g = ga if s > v else gr
        v = g * v + (1 - g) * s
        e[i] = v
    return e


def compress(x, thresh_db=-22, ratio=2.5, attack=0.008, release=0.12):
    env = envelope(x, attack, release)
    lvl = 20 * np.log10(np.maximum(env, 1e-6))
    over = np.maximum(0, lvl - thresh_db)
    return x * db(-over * (1 - 1 / ratio))


def main():
    tl = json.loads((ROOT / "build" / "timeline.json").read_text())
    n = int((tl["duration"] + 0.05) * SR)
    meter = pyln.Meter(SR)

    voice = np.zeros(n, np.float32)
    for l in tl["lines"]:
        y, sr = sf.read(ROOT / "build" / "voice48" / f"{l['id']}.wav", dtype="float32")
        assert sr == SR
        i = int(round(l["start"] * SR))
        voice[i:i + len(y)] += y[: max(0, n - i)]
    voice = sosfilt(butter(2, 75, btype="high", fs=SR, output="sos"), voice)
    voice = peaking(voice, 220, -1.5, 0.9)      # a little less boxiness
    voice = peaking(voice, 3200, 2.0, 1.0)      # presence for small phone speakers
    voice = compress(voice)
    voice *= db(-16 - meter.integrated_loudness(voice))

    music, _ = sf.read(ROOT / "build" / "audio" / "music.wav", dtype="float32")
    sfx, _ = sf.read(ROOT / "build" / "audio" / "sfx.wav", dtype="float32")
    music, sfx = music[:n], sfx[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    sfx = np.pad(sfx, ((0, n - len(sfx)), (0, 0)))
    music *= db(-27 - meter.integrated_loudness(music))

    # duck the music while the narrator speaks
    talk = envelope(voice, 0.03, 0.45)
    talk = np.clip(talk / (np.percentile(talk[talk > 1e-4], 60) + 1e-9), 0, 1)
    music *= db(-5.0 * talk)[:, None]

    sfx *= db(-3.0)
    mix = np.stack([voice, voice], axis=1) + music + sfx
    fade = int(0.8 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2

    out = ROOT / "build" / "audio"
    sf.write(out / "narration.wav", voice, SR, subtype="FLOAT")
    sf.write(out / "mix.wav", mix.astype(np.float32), SR, subtype="FLOAT")

    # two pass loudness normalisation
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out / "mix.wav"), "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = p.stderr[p.stderr.rindex("{"):p.stderr.rindex("}") + 1]
    m = json.loads(js)
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={input_i}:measured_TP={input_tp}:"
          "measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}:linear=true").format(**m)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / "mix.wav"), "-af", af,
                    "-ar", "48000", "-c:a", "pcm_s24le", str(out / "final.wav")], check=True)
    print("mastered:", m["input_i"], "LUFS in ->", "-14 LUFS target")


if __name__ == "__main__":
    main()
