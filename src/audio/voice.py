"""Generate the narration, one line at a time, and keep the best take.

Voice: Kokoro 82M v1.0 (hexgrad), Apache 2.0 weights, voice "af_bella" (American
English, female), run through kokoro-onnx. Kokoro gives the same audio every time
for the same input, so the takes of a line differ in speaking speed instead.
Every take is transcribed with Whisper. A take is only eligible if the transcript
matches the script word for word. Among eligible takes the clearest one wins
(highest mean word probability), with a light preference for the natural speed.

Usage: python src/audio/voice.py [--only L05,L06]
Output: build/voice/<line>.wav and build/voice/manifest.json
The model files (about 350 MB) are downloaded to build/models/ on first run.
"""
import argparse
import json
import re
import shutil
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "voice"
TAKES = OUT / "takes"
MODELS = ROOT / "build" / "models"
VOICE = "af_bella"
SPEEDS = [1.0, 0.97, 1.03]
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def norm_words(s):
    s = s.lower().replace("i.d.", "id").replace("c.s.i.r.o.", "csiro")
    s = re.sub(r"[^a-z0-9' ]+", " ", s.replace("-", " "))
    s = re.sub(r"\bred belly\b", "redbelly", s)
    s = re.sub(r"(\w)iz(ation|e|ed)\b", r"\1is\2", s).replace("trialed", "trialled")
    s = re.sub(r"\btoo\b", "two", s)  # same sound; Whisper cannot tell them apart
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


def load_kokoro():
    from kokoro_onnx import EspeakConfig, Kokoro
    import espeakng_loader

    MODELS.mkdir(parents=True, exist_ok=True)
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        if not (MODELS / name).exists():
            print(f"downloading {name}", flush=True)
            urllib.request.urlretrieve(MODEL_URL + name, MODELS / name)
    # espeak-ng cuts data paths longer than about 160 characters, so keep a copy at a short path.
    data = Path(espeakng_loader.get_data_path())
    if len(str(data)) > 100:
        short = Path.home() / ".cache" / "espk" / "espeak-ng-data"
        if not short.exists():
            shutil.copytree(data, short)
        data = short
    return Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"),
                  espeak_config=EspeakConfig(data_path=str(data)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    script = json.loads((ROOT / "src" / "script.json").read_text())
    lines = script["lines"]
    if args.only:
        keep = set(args.only.split(","))
        lines = [l for l in lines if l["id"] in keep]

    OUT.mkdir(parents=True, exist_ok=True)
    TAKES.mkdir(parents=True, exist_ok=True)
    man_path = OUT / "manifest.json"
    manifest = json.loads(man_path.read_text()) if man_path.exists() and args.only else {}

    tts = load_kokoro()
    asr = WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)

    for line in lines:
        spoken = line.get("tts", line["text"])
        results = []
        for k, speed in enumerate(SPEEDS):
            wav, sr = tts.create(spoken, voice=VOICE, speed=speed, lang="en-us")
            y = trim(np.asarray(wav, dtype=np.float32), sr)
            f = TAKES / f"{line['id']}_t{k}.wav"
            sf.write(f, y, sr)
            # Whisper tends to miss a word that starts at the very first sample, so lead in with silence.
            a16 = np.concatenate([np.zeros(6400, np.float32), librosa.resample(y, orig_sr=sr, target_sr=16000)])
            segs, _ = asr.transcribe(a16, word_timestamps=True, beam_size=5, language="en")
            words = [w for s in segs for w in s.words]
            hyp = " ".join(w.word.strip() for w in words)
            prob = float(np.mean([w.probability for w in words])) if words else 0.0
            dur = len(y) / sr
            e = wer(line["text"], hyp)
            # Prefer exact transcripts, then clarity, then the natural speed.
            score = (1.0 if e == 0 else 0.0) * 10 + prob - 0.5 * abs(speed - 1.0)
            results.append({"take": k, "speed": speed, "file": f.name, "dur": round(dur, 3),
                            "wer": round(e, 3), "prob": round(prob, 4), "score": round(score, 4), "asr": hyp})
            print(f"{line['id']} speed {speed}: wer={e:.3f} prob={prob:.3f} dur={dur:.2f}s | {hyp}", flush=True)
        best = max(results, key=lambda r: r["score"])
        y, sr = sf.read(TAKES / best["file"])
        sf.write(OUT / f"{line['id']}.wav", y, sr)
        manifest[line["id"]] = {"text": line["text"], "spoken": spoken, "voice": VOICE, "chosen": best, "takes": results}
        man_path.write_text(json.dumps(manifest, indent=2))
        print(f"==> {line['id']} chose speed {best['speed']} ({best['dur']}s)", flush=True)


if __name__ == "__main__":
    main()
