"""Generate the narration, one line at a time, and keep the best take.

Voice: Chatterbox Turbo (Resemble AI), MIT licensed code and weights, built-in voice.
Every take is transcribed with Whisper. A take is only eligible if the transcript
matches the script word for word. Among eligible takes the clearest one wins
(highest mean word probability, natural speaking rate).

Usage: python src/audio/voice.py [--takes 4] [--only L05,L06]
Output: build/voice/<line>.wav and build/voice/manifest.json
"""
import argparse
import json
import re
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "voice"
TAKES = OUT / "takes"


def norm_words(s):
    s = s.lower().replace("i.d.", "id").replace("c.s.i.r.o.", "csiro")
    s = re.sub(r"[^a-z0-9' ]+", " ", s.replace("-", " "))
    s = re.sub(r"\bred belly\b", "redbelly", s)
    s = re.sub(r"(\w)iz(ation|e|ed)\b", r"\1is\2", s).replace("trialed", "trialled")
    return [w.strip("'") for w in s.split() if w.strip("'")]


def wer(ref, hyp):
    r, h = norm_words(ref), norm_words(hyp)
    d = np.zeros((len(r) + 1, len(h) + 1), dtype=int)
    d[:, 0] = range(len(r) + 1)
    d[0, :] = range(len(h) + 1)
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(r), len(h)] / max(1, len(r))


def trim(y, sr):
    _, (a, b) = librosa.effects.trim(y, top_db=42, frame_length=1024, hop_length=128)
    pad = int(0.04 * sr)
    a, b = max(0, a - pad), min(len(y), b + pad)
    y = y[a:b].copy()
    fade = int(0.012 * sr)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--takes", type=int, default=4)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    torch.set_num_threads(4)
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    from faster_whisper import WhisperModel

    script = json.loads((ROOT / "src" / "script.json").read_text())
    lines = script["lines"]
    if args.only:
        keep = set(args.only.split(","))
        lines = [l for l in lines if l["id"] in keep]

    OUT.mkdir(parents=True, exist_ok=True)
    TAKES.mkdir(parents=True, exist_ok=True)
    man_path = OUT / "manifest.json"
    manifest = json.loads(man_path.read_text()) if man_path.exists() else {}

    tts = ChatterboxTurboTTS.from_pretrained(device="cpu")
    asr = WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)

    for li, line in enumerate(lines):
        spoken = line.get("tts", line["text"])
        results = []
        for k in range(args.takes):
            seed = 7000 + int(line["id"][1:]) * 31 + k
            torch.manual_seed(seed)
            np.random.seed(seed)
            wav = tts.generate(spoken, temperature=0.75, top_p=0.95, repetition_penalty=1.2)
            y = trim(wav.squeeze(0).cpu().numpy().astype(np.float32), tts.sr)
            f = TAKES / f"{line['id']}_t{k}.wav"
            sf.write(f, y, tts.sr)
            a16 = librosa.resample(y, orig_sr=tts.sr, target_sr=16000)
            segs, _ = asr.transcribe(a16, word_timestamps=True, beam_size=5, language="en")
            words = [w for s in segs for w in s.words]
            hyp = " ".join(w.word.strip() for w in words)
            prob = float(np.mean([w.probability for w in words])) if words else 0.0
            dur = len(y) / tts.sr
            wps = len(norm_words(line["text"])) / dur
            e = wer(line["text"], hyp)
            # Prefer exact transcripts, then clarity, then a relaxed speaking rate.
            score = (1.0 if e == 0 else 0.0) * 10 + prob - 0.15 * max(0.0, wps - 3.3)
            results.append({"take": k, "seed": seed, "file": f.name, "dur": round(dur, 3),
                            "wps": round(wps, 2), "wer": round(e, 3), "prob": round(prob, 4),
                            "score": round(score, 4), "asr": hyp})
            print(f"{line['id']} take {k}: wer={e:.3f} prob={prob:.3f} dur={dur:.2f}s wps={wps:.2f} | {hyp}", flush=True)
        best = max(results, key=lambda r: r["score"])
        y, sr = sf.read(TAKES / best["file"])
        sf.write(OUT / f"{line['id']}.wav", y, sr)
        manifest[line["id"]] = {"text": line["text"], "spoken": spoken, "chosen": best, "takes": results}
        man_path.write_text(json.dumps(manifest, indent=2))
        print(f"==> {line['id']} chose take {best['take']} ({best['dur']}s)", flush=True)


if __name__ == "__main__":
    main()
