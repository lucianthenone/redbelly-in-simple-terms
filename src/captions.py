"""Write the caption files and the plain transcript from build/timeline.json.

Outputs (in submission/):
  redbelly-in-simple-terms.srt   SubRip, the format X accepts for uploaded captions
  redbelly-in-simple-terms.vtt   WebVTT, for the website player
  transcript.txt                 the narration as plain text, one line per sentence
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "redbelly-in-simple-terms"


def ts(t, sep):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main():
    tl = json.loads((ROOT / "build" / "timeline.json").read_text())
    out = ROOT / "submission"
    out.mkdir(exist_ok=True)
    caps = tl["captions"]
    srt = "\n".join(f"{i}\n{ts(c['start'], ',')} --> {ts(c['end'], ',')}\n{c['text']}\n" for i, c in enumerate(caps, 1))
    vtt = "WEBVTT\n\n" + "\n".join(f"{ts(c['start'], '.')} --> {ts(c['end'], '.')}\n{c['text']}\n" for c in caps)
    (out / f"{NAME}.srt").write_text(srt)
    (out / f"{NAME}.vtt").write_text(vtt)
    (out / "transcript.txt").write_text("\n".join(l["text"] for l in tl["lines"]) + "\n")
    print(f"{len(caps)} caption cues written")


if __name__ == "__main__":
    main()
