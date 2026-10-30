"""Shared data and words for the website and the PDF, built from the source files."""
import json
import re
import subprocess
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = "redbelly-in-simple-terms"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def long_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MONTHS[m - 1]} {y}"


def load():
    script = json.loads((ROOT / "src/script.json").read_text())
    facts = json.loads((ROOT / "src/facts.json").read_text())
    tl = json.loads((ROOT / "build/timeline.json").read_text())
    video = ROOT / "submission" / f"{NAME}.mp4"
    probe = {}
    if video.exists():
        pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                                       capture_output=True, text=True).stdout)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        num, den = (int(x) for x in v["r_frame_rate"].split("/"))
        probe = {"duration": float(pr["format"]["duration"]), "size_mb": int(pr["format"]["size"]) / 1e6,
                 "w": int(v["width"]), "h": int(v["height"]), "fps": round(num / den)}
    report = ROOT / "submission" / "verification-report.md"
    rep = report.read_text() if report.exists() else ""
    m = re.search(r"(\d+) of (\d+) checks passed", rep)
    checks = (int(m.group(1)), int(m.group(2))) if m else None
    words = sum(len(l["text"].split()) for l in script["lines"])
    return {"script": script, "facts": facts, "tl": tl, "probe": probe, "checks": checks, "words": words,
            "fact_by_id": {f["id"]: f for f in facts["facts"]}}


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


STORYBOARD = [
    ("hook", "hook.settle", 0.35, "A photo crosses the world in a second. Buying into a fund sits at Pending for two business days. The gap between the two sets up the question."),
    ("problem", "problem.check", 1.45, "The money and the record of who owns what sit in separate systems. Four firms keep their own copies and someone checks they match. One does not."),
    ("onestep", "onestep.final", 1.05, "Redbelly arrives. Payment and ownership swap in a single step. When one side fails, nothing moves. When the swap completes, it is final."),
    ("people", "people.private", 1.0, "A crowd turns verified one person at a time. An ID check shows that identity is proven while the personal details stay hidden."),
    ("rules", "rules.blocked", 0.35, "The product's rules run before every trade. Buyer A passes all three checks. Buyer B is not eligible, so the trade is blocked."),
    ("assets", "assets.word", 1.0, "Property, loans, bonds and investment funds become digital versions that settle almost instantly. A dictionary card names the idea: tokenisation."),
    ("proof", "proof.three", 1.2, "Research at the University of Sydney and CSIRO leads to Redbelly. In Project Acacia, the Reserve Bank of Australia's pilot digital money ran on three platforms. Redbelly is one of them."),
    ("close", "endcard", 1.6, "Verified people. Rules built in. Done in one step. Then the logo, the web address and the date the facts were last checked."),
]


def storyboard_times(tl):
    out = []
    for sid, cue, off, _ in STORYBOARD:
        sc = next(s for s in tl["scenes"] if s["id"] == sid)
        t = min(tl["cues"][cue] + off, (sc["end"] - 0.12) if sid != "close" else tl["duration"] - 0.8)
        out.append(round(t, 2))
    return out


BENCHMARKS = [
    ("Someone with no crypto knowledge understands it after one watch",
     "One everyday comparison opens the video: a photo arrives in a second, a fund takes two business days. Everything after that answers why. The ID-at-a-bank comparison carries the identity idea. The video uses none of the usual jargon, and the checker scans for it: no crypto, token, wallet, node or consensus."),
    ("Original, memorable and easy to share",
     "The whole explanation lands on three short ideas that the close repeats: verified people, rules built in, done in one step. Captions are burned in for sound-off viewing on X. The music, sound and animation were all made for this entry."),
    ("Every fact about Redbelly is correct",
     "Every statement about Redbelly maps to a fact in the fact sheet, and every fact carries a quote from Redbelly's own material or from the Reserve Bank of Australia. The checker re-fetches each source and confirms each quote is still on the page."),
]

FAILURES = [
    ("The banned word or a stand-in appears anywhere", "Scanned in the narration, the captions, every piece of on-screen text, this site, the PDF and every file in the repository. The usual stand-ins and abbreviations are checked as well."),
    ("Any factual error about Redbelly", "16 facts, each tied to quotes from public Redbelly, Tokeniser and Reserve Bank of Australia material, last verified on the date below."),
    ("Entry posted publicly before judging", "The video has not been posted on X or any other channel. The DAO posts the winner."),
    ("Price talk, investment advice or promises of returns", "None. The script never mentions a token, a price, a yield or a return, and the checker scans for them."),
    ("Unlicensed music, images or footage", "No stock media at all. Music and sound are synthesised in code, the animation is drawn in code, and fonts, icons and logos are used under the licences listed in CREDITS.md."),
    ("AI generated text submitted without checking", "Every line was checked against the sources in the fact sheet. The final audio is transcribed and compared word for word with the script, so the voice cannot add or change a word."),
    ("Personal credit inside the deliverable", "No names, handles, signatures, watermarks or made-by lines in the video, the captions, the site or the PDF."),
]

PRODUCTION = [
    ("Script", "21 lines in src/script.json, each tagged with the facts it relies on. Written to be read aloud: one idea per sentence."),
    ("Voice", "Chatterbox Turbo, an open-weights voice model under the MIT licence, with its built-in voice. Four takes of every line. Each take is transcribed with Whisper and only takes that match the script word for word can be chosen. The chosen takes are slowed by 5 percent with Rubber Band, formants preserved, for an easy pace."),
    ("Music and sound", "Composed in code in src/audio/music.py: warm pads, a plucked arpeggio, bass and light percussion at 96 BPM. The groove lands on the Redbelly reveal. Sound effects are synthesised the same way. The music ducks under the voice and the mix is mastered to -14 LUFS."),
    ("Picture", "Eight HTML and SVG scenes in the DAO Task Board palette and type. Each frame is a pure function of time, rendered in Chromium at 1920 x 1080 and 60 frames per second, then encoded with x264."),
    ("Timing", "Every animation and sound effect is anchored to a spoken word, using Whisper word timings, so the picture moves when the voice says the word."),
]
