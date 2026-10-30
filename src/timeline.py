"""Build the master timeline that the audio mix, the renderer and the captions share.

1. Takes the chosen narration takes from build/voice/, slows them gently with
   Rubber Band (formant preserved) for a relaxed, easy to follow pace, and
   resamples to 48 kHz.
2. Lays the lines out on the clock using the pauses in src/script.json.
3. Gets word timings with Whisper and aligns them to the script words.
4. Resolves every animation and sound cue to a time, anchored on spoken words,
   so the picture moves when the voice says the word.

Writes build/timeline.json and build/voice48/<line>.wav
"""
import difflib
import json
import re
import subprocess
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SR = 48000
TEMPO = 0.95          # 5 percent slower than the raw take
INTRO = 0.6           # seconds of picture before the first word
SCENE_LEAD = 0.45     # a scene starts this long before its first line
ENDCARD_HOLD = 3.4    # end card length after the last line
FPS = 60
MAX_CAPTION_CHARS = 46

# (cue name, line, word to anchor on, "start" or "end", offset in seconds)
CUES = [
    ("hook.send", "L01", "send", "start", 0.0),
    ("hook.arrive", "L01", "second", "start", 0.05),
    ("hook.fund", "L02", "buying", "start", -0.15),
    ("hook.days", "L02", "two", "start", 0.0),
    ("hook.settle", "L02", "settle", "start", 0.0),
    ("problem.money", "L03", "money", "start", 0.0),
    ("problem.record", "L03", "record", "start", 0.0),
    ("problem.copies", "L04", "different", "start", 0.0),
    ("problem.check", "L04", "check", "start", 0.0),
    ("onestep.logo", "L05", "redbelly", "start", -0.05),
    ("onestep.public", "L05", "public", "start", 0.0),
    ("onestep.australia", "L05", "australia", "start", 0.0),
    ("onestep.together", "L05", "together", "start", 0.0),
    ("onestep.swap", "L06", "move", "start", 0.0),
    ("onestep.step", "L06", "step", "start", 0.0),
    ("onestep.fail", "L07", "fails", "start", 0.0),
    ("onestep.nothing", "L07", "nothing", "start", 0.0),
    ("onestep.final", "L08", "final", "start", 0.0),
    ("people.crowd", "L09", "and", "start", 0.0),
    ("people.verify", "L10", "verified", "start", 0.0),
    ("people.id", "L10", "id", "start", 0.0),
    ("people.private", "L10", "private", "start", 0.0),
    ("rules.list", "L11", "rules", "start", 0.0),
    ("rules.trade", "L12", "trade", "start", 0.0),
    ("rules.check", "L12", "checks", "start", 0.0),
    ("rules.fail", "L13", "not", "start", 0.0),
    ("rules.blocked", "L13", "doesn't", "start", 0.0),
    ("assets.property", "L14", "property", "start", 0.0),
    ("assets.loans", "L14", "loans", "start", 0.0),
    ("assets.bonds", "L14", "bonds", "start", 0.0),
    ("assets.funds", "L14", "funds", "start", 0.0),
    ("assets.digital", "L14", "digitally", "start", 0.0),
    ("assets.settle", "L14", "instantly", "start", 0.0),
    ("assets.word", "L15", "people", "start", 0.0),
    ("proof.uni", "L16", "university", "start", 0.0),
    ("proof.csiro", "L16", "csiro", "start", 0.0),
    ("proof.rba", "L17", "reserve", "start", 0.0),
    ("proof.money", "L17", "pilot", "start", 0.0),
    ("proof.acacia", "L17", "acacia", "start", 0.0),
    ("proof.redbelly", "L17", "redbelly", "start", 0.0),
    ("proof.three", "L17", "three", "start", 0.0),
    ("proof.carried", "L17", "carried", "start", 0.0),
    ("close.p1", "L18", "verified", "start", -0.1),
    ("close.p2", "L19", "rules", "start", -0.1),
    ("close.p3", "L20", "done", "start", -0.1),
    ("close.name", "L21", "that's", "start", -0.1),
]

SFX = [
    ("hook.send", "whoosh", 0.0, 0.9),
    ("hook.arrive", "chime_low", 0.0, 0.8),
    ("hook.fund", "whoosh_down", -0.1, 0.8),
    ("hook.days", "tick", 0.0, 0.8),
    ("hook.days", "tick", 0.42, 0.8),
    ("hook.days", "tick", 0.84, 0.8),
    ("problem.money", "pop", 0.0, 0.9),
    ("problem.record", "pop", 0.0, 0.9),
    ("problem.copies", "pop_high", 0.0, 0.6),
    ("problem.copies", "pop_high", 0.14, 0.6),
    ("problem.copies", "pop_high", 0.28, 0.6),
    ("problem.copies", "pop_high", 0.42, 0.6),
    ("problem.check", "tick_soft", 0.0, 0.9),
    ("problem.check", "tick_soft", 0.3, 0.9),
    ("problem.check", "tick_soft", 0.6, 0.9),
    ("onestep.logo", "impact", -0.02, 0.85),
    ("onestep.logo", "whoosh_long", -0.55, 0.7),
    ("onestep.together", "whoosh", 0.0, 0.8),
    ("onestep.swap", "whoosh", 0.0, 0.7),
    ("onestep.step", "lock", 0.15, 0.9),
    ("onestep.fail", "deny", 0.25, 0.9),
    ("onestep.final", "lock", 0.0, 1.0),
    ("onestep.final", "chime", 0.05, 0.7),
    ("people.crowd", "whoosh_down", -0.1, 0.6),
    ("people.verify", "pop_high", 0.0, 0.6),
    ("people.verify", "pop_high", 0.16, 0.6),
    ("people.verify", "pop_high", 0.32, 0.6),
    ("people.verify", "pop_high", 0.48, 0.6),
    ("people.verify", "pop_high", 0.64, 0.6),
    ("people.private", "lock", 0.0, 0.8),
    ("rules.list", "pop", 0.0, 0.8),
    ("rules.check", "tick", 0.0, 0.8),
    ("rules.check", "tick", 0.32, 0.8),
    ("rules.check", "tick", 0.64, 0.8),
    ("rules.check", "chime_low", 0.9, 0.6),
    ("rules.fail", "deny", 0.15, 0.9),
    ("assets.property", "pop", 0.0, 0.7),
    ("assets.loans", "pop", 0.0, 0.7),
    ("assets.bonds", "pop", 0.0, 0.7),
    ("assets.funds", "pop", 0.0, 0.7),
    ("assets.digital", "whoosh", 0.0, 0.8),
    ("assets.settle", "chime", 0.0, 0.6),
    ("assets.word", "pop_high", 0.0, 0.8),
    ("proof.uni", "pop", 0.0, 0.7),
    ("proof.csiro", "pop", 0.0, 0.7),
    ("proof.rba", "whoosh", -0.1, 0.7),
    ("proof.acacia", "pop_high", 0.0, 0.6),
    ("proof.redbelly", "chime_low", 0.0, 0.7),
    ("proof.carried", "whoosh", 0.0, 0.6),
    ("close.p1", "pop", 0.0, 0.8),
    ("close.p2", "pop", 0.0, 0.8),
    ("close.p3", "pop", 0.0, 0.8),
    ("close.name", "whoosh_long", 0.0, 0.7),
    ("endcard", "impact", 0.0, 0.9),
]


def norm(w):
    w = w.lower().replace("i.d.", "id").replace("c.s.i.r.o.", "csiro").replace("’", "'")
    return re.sub(r"[^a-z0-9']+", "", w).strip("'")


def tokens(text):
    return [t for t in re.split(r"\s+", text.strip()) if t]


def stretch(src, dst):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-af", f"aresample=48000:resampler=soxr,rubberband=tempo={TEMPO}:formant=preserved:pitchq=quality:window=standard",
        "-ac", "1", "-c:a", "pcm_f32le", str(dst)], check=True)


def merge_split_words(aw):
    """Whisper writes the name as two words ("Red Belly"); join them back."""
    out = []
    for w in aw:
        if out and norm(out[-1]["w"]) == "red" and norm(w["w"]).startswith("belly"):
            out[-1] = {"w": "Redbelly" + w["w"][5:], "start": out[-1]["start"], "end": w["end"]}
        else:
            out.append(w)
    return out


def align(script_words, asr_words, dur):
    """Map each script word to (start, end) using the Whisper words."""
    a = [norm(w) for w in script_words]
    b = [norm(w["w"]) for w in asr_words]
    times = [None] * len(a)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            w = asr_words[blk.b + k]
            times[blk.a + k] = (w["start"], w["end"])
    # Fill any gaps by spreading time over unmatched words, weighted by length.
    i = 0
    while i < len(a):
        if times[i] is None:
            j = i
            while j < len(a) and times[j] is None:
                j += 1
            t0 = times[i - 1][1] if i > 0 else 0.0
            t1 = times[j][0] if j < len(a) else dur
            lens = np.array([max(1, len(x)) for x in a[i:j]], float)
            edges = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(lens) / lens.sum()])
            for k in range(i, j):
                times[k] = (float(edges[k - i]), float(edges[k - i + 1]))
            i = j
        else:
            i += 1
    return times


SOFT_BREAK_BEFORE = {"and", "that", "to", "in", "at", "of", "but", "so", "if", "the", "a", "before",
                     "because", "while", "which", "who", "like", "from", "was", "can"}


def chunk_captions(words):
    """Split a line's words into one-line caption cues, choosing the breaks with
    the lowest total cost: break after punctuation if possible, otherwise before
    a small joining word, and never leave a tiny orphan."""
    n = len(words)
    text = lambda i, j: " ".join(w["text"] for w in words[i:j])
    best = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j):
            L = len(text(i, j))
            if L > MAX_CAPTION_CHARS:
                continue
            if j == n or words[j - 1]["text"][-1] in ",.?!":
                brk = 0.0
            elif words[j]["text"].lower() in SOFT_BREAK_BEFORE:
                brk = 1.5
            else:
                brk = 6.0
            cost = best[i] + ((L - 30) / 12) ** 2 + brk + (4.0 if L < 12 and n > 2 else 0.0)
            if cost < best[j]:
                best[j], back[j] = cost, i
    cues, j = [], n
    while j > 0:
        cues.append(words[back[j]:j])
        j = back[j]
    return cues[::-1]


def main():
    from faster_whisper import WhisperModel

    script = json.loads((ROOT / "src" / "script.json").read_text())
    vdir, odir = ROOT / "build" / "voice", ROOT / "build" / "voice48"
    odir.mkdir(parents=True, exist_ok=True)
    asr = WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)

    lines, cursor = [], INTRO
    for ln in script["lines"]:
        dst = odir / f"{ln['id']}.wav"
        stretch(vdir / f"{ln['id']}.wav", dst)
        y, sr = sf.read(dst)
        dur = len(y) / sr
        a16 = librosa.resample(y.astype(np.float32), orig_sr=sr, target_sr=16000)
        segs, _ = asr.transcribe(a16, word_timestamps=True, beam_size=5, language="en",
                                 initial_prompt=ln["text"])
        aw = [{"w": w.word.strip(), "start": float(w.start), "end": float(w.end)} for s in segs for w in s.words]
        aw = merge_split_words(aw)
        sw = tokens(ln["text"])
        times = align(sw, aw, dur)
        words = [{"text": t, "start": round(cursor + s, 3), "end": round(cursor + e, 3)} for t, (s, e) in zip(sw, times)]
        lines.append({"id": ln["id"], "scene": ln["scene"], "text": ln["text"], "facts": ln["facts"],
                      "start": round(cursor, 3), "end": round(cursor + dur, 3), "words": words,
                      "asr": " ".join(w["w"] for w in aw)})
        cursor += dur + ln["pause_after"] / TEMPO
        print(f"{ln['id']} {lines[-1]['start']:.2f}-{lines[-1]['end']:.2f} | {lines[-1]['asr']}", flush=True)

    endcard = round(lines[-1]["end"] + 0.45, 3)
    duration = round(endcard + ENDCARD_HOLD, 3)

    scenes = []
    for sc in script["scenes"]:
        first = next(l for l in lines if l["scene"] == sc["id"])
        start = 0.0 if not scenes else round(first["start"] - SCENE_LEAD, 3)
        scenes.append({"id": sc["id"], "name": sc["name"], "start": start})
    for i, sc in enumerate(scenes):
        sc["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else endcard

    cues = {"endcard": endcard}
    byid = {l["id"]: l for l in lines}
    for name, lid, word, edge, off in CUES:
        ws = byid[lid]["words"]
        match = next((w for w in ws if norm(w["text"]) == norm(word)), None)
        if match is None:
            raise SystemExit(f"cue {name}: word '{word}' not in {lid}")
        cues[name] = round(match[edge] + off, 3)

    sfx = [{"cue": c, "sound": s, "t": round(cues[c] + off, 3), "gain": g} for c, s, off, g in SFX]

    captions = []
    for l in lines:
        manual = next(x for x in script["lines"] if x["id"] == l["id"]).get("captions")
        if manual:
            groups, k = [], 0
            for chunk in manual:
                m = len(tokens(chunk))
                groups.append(l["words"][k:k + m])
                k += m
        else:
            groups = chunk_captions(l["words"])
        for grp in groups:
            captions.append({"line": l["id"], "start": grp[0]["start"], "end": grp[-1]["end"],
                             "text": " ".join(w["text"] for w in grp), "words": grp})
    for c in captions:
        c["start"] = round(max(0.0, c["start"] - 0.05), 3)
    for i, c in enumerate(captions):
        nxt = captions[i + 1]["start"] if i + 1 < len(captions) else c["end"] + 1.0
        c["end"] = round(min(nxt - 0.02, c["end"] + 0.6), 3)

    tl = {"fps": FPS, "width": 1920, "height": 1080, "duration": duration, "tempo": TEMPO,
          "last_verified": script["last_verified"], "scenes": scenes, "lines": lines,
          "cues": cues, "sfx": sfx, "captions": captions}
    (ROOT / "build" / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"duration {duration:.2f}s, {len(captions)} captions")


if __name__ == "__main__":
    main()
