"""Check the submission against the task's failure criteria and quality benchmarks.

  python src/checks/verify.py            offline checks (language, facts, files, video specs)
  python src/checks/verify.py --online   also fetch every source and confirm each quote is on the page
  python src/checks/verify.py --asr      also transcribe the final video's audio and compare it to the script

Writes submission/verification-report.md and exits non-zero if anything fails.

The banned words are assembled from fragments below, so the words themselves
never appear anywhere in this repository as plain text.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUB = ROOT / "submission"
NAME = "redbelly-in-simple-terms"
VIDEO = SUB / f"{NAME}.mp4"

B, C, L = "blo" + "ck", "ch" + "ain", "led" + "ger"
BANNED = [  # the word itself and its stand-ins: any hit anywhere fails
    (rf"\b{B}[\s_-]*{C}s?\b", f"{B}{C}"),
    (rf"\bdistributed\s+{L}s?\b", f"distributed {L}"),
    (r"\bD\.?L\.?T\b", "D" + "LT"),
    (rf"\b{L}s?\b", L),
    (rf"\b(on|off|multi|cross)[\s-]?{C}\b", f"on/off {C}"),
    (rf"\b{C}s?\b", C),
]
FILLER = ["elevate", "seamless", "unleash", "revolutioni[sz]e", "revolutionary", "game[- ]changing"]
PRICE = [r"\bprice[sd]?\b", r"\breturns?\b", r"\bprofits?\b", r"\bRBNT\b", r"\bAPY\b", r"\byields?\b",
         r"\bto the moon\b", r"\bfinancial advice\b", r"\bguarantee[sd]?\b", r"\bbuy (the|our) token\b", r"\bmarket cap\b"]
CREDIT = [r"lucianthenone", r"\bmade by\b", r"\bcreated by\b", r"\bproduced by\b",
          r"(?<![\w.])@(?!media\b|font-face\b|page\b|import\b|keyframes\b|supports\b)[A-Za-z0-9_]{2,}"]
JARGON = [r"\bcrypto\w*", r"\bweb3\b", r"\bsmart contracts?\b", r"\blayer[ -]?1\b", r"\bconsensus\b", r"\bnodes?\b",
          r"\bdecentrali[sz]ed\b", r"\bwallets?\b", r"\btokens?\b"]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))


def masked(hits):
    """Report a banned hit without writing the word out again."""
    return ", ".join(sorted({h[0] + "*" * (len(h) - 2) + h[-1] if len(h) > 2 else "*" * len(h) for h in hits}))


def visible(path, text):
    """For web pages, only the words a reader sees: drop style and script blocks and tags."""
    if path.suffix == ".html":
        text = re.sub(r"<style.*?</style>|<script.*?</script>", " ", text, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def has_emoji(s):
    return [ch for ch in s if unicodedata.category(ch) == "So" and ord(ch) > 0x2100 and ch not in "\u2713\u2717"]


def scan(text, patterns, flags=re.I):
    hits = []
    for pat in patterns:
        p = pat[0] if isinstance(pat, tuple) else pat
        for m in re.finditer(p, text, flags):
            hits.append(m.group(0))
    return hits


def pdf_text(path, mode="-layout"):
    try:
        return subprocess.run(["pdftotext", mode, str(path), "-"], capture_output=True, text=True, check=True).stdout
    except Exception:
        return ""


def authored_files():
    """Text we wrote ourselves. Third-party licence texts and font files are left out."""
    skip_dirs = {"build", ".git", "node_modules", "fonts", "icons"}
    exts = {".md", ".txt", ".json", ".html", ".css", ".js", ".mjs", ".py", ".sh", ".srt", ".vtt", ".yml", ".toml"}
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in exts and not (set(p.relative_to(ROOT).parts) & skip_dirs):
            if p.name in ("icons.js",) or p.name.startswith("LICENSE") or p.name.startswith("OFL"):
                continue
            yield p


def norm(s):
    s = html.unescape(s).replace("\u2019", "'").replace("\u2018", "'").replace("&", " and ")
    return re.sub(r"[^a-z0-9$]+", " ", s.lower()).strip()


def page_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (fact check)"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    if url.endswith(".pdf"):
        tmp = ROOT / "build" / "source.pdf"
        tmp.write_bytes(raw)
        # tables in the report read across columns in layout mode, so keep both reading orders
        return pdf_text(tmp) + "\n" + pdf_text(tmp, "-raw")
    t = raw.decode("utf8", "ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    return re.sub(r"<[^>]+>", " ", t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--asr", action="store_true")
    args = ap.parse_args()

    script = json.loads((ROOT / "src/script.json").read_text())
    facts = json.loads((ROOT / "src/facts.json").read_text())
    entry_texts = {
        "narration script": "\n".join(l["text"] for l in script["lines"]),
        "on-screen text": (ROOT / "build/onscreen-text.txt").read_text() if (ROOT / "build/onscreen-text.txt").exists() else "",
    }
    for ext in ("srt", "vtt"):
        f = SUB / f"{NAME}.{ext}"
        entry_texts[f"captions .{ext}"] = f.read_text() if f.exists() else ""

    # 1. Failure criteria inside the entry itself
    print("\n== The entry (narration, captions, on-screen text) ==")
    for label, text in entry_texts.items():
        check(f"{label}: present", text.strip(), "")
        check(f"{label}: no banned word or stand-in", not scan(text, BANNED), masked(scan(text, BANNED)))
        check(f"{label}: no price talk or investment advice", not scan(text, PRICE), ", ".join(scan(text, PRICE)))
        check(f"{label}: no personal credit", not scan(text, CREDIT), ", ".join(scan(text, CREDIT)))
        check(f"{label}: no crypto jargon", not scan(text, JARGON), ", ".join(sorted(set(scan(text, JARGON)))))

    # 2. The whole repository: banned words, brand voice
    print("\n== Every file in the repository ==")
    bad_b, bad_d, bad_e, bad_f, bad_c = [], [], [], [], []
    for p in authored_files():
        t = p.read_text(errors="ignore")
        rel = str(p.relative_to(ROOT))
        if rel in ("src/checks/verify.py", "submission/verification-report.md"):
            continue
        if scan(t, BANNED):
            bad_b.append(f"{rel}: {masked(scan(t, BANNED))}")
        if "\u2014" in t or "\u2013" in t:
            bad_d.append(rel)
        if has_emoji(t):
            bad_e.append(rel)
        hits = [h for h in scan(t, FILLER) if not rel.startswith("src/checks")]
        if hits:
            bad_f.append(f"{rel}: {', '.join(sorted(set(hits)))}")
        if rel.startswith(("submission", "site", "index.html")) and scan(visible(p, t), CREDIT):
            bad_c.append(f"{rel}: {', '.join(scan(visible(p, t), CREDIT))}")
    pdf = SUB / f"{NAME}-submission.pdf"
    pt = pdf_text(pdf) if pdf.exists() else ""
    check("PDF: present and readable", len(pt) > 500, f"{len(pt)} characters")
    if scan(pt, BANNED):
        bad_b.append("PDF: " + masked(scan(pt, BANNED)))
    if "\u2014" in pt or "\u2013" in pt:
        bad_d.append("PDF")
    if scan(pt, CREDIT):
        bad_c.append("PDF: " + ", ".join(scan(pt, CREDIT)))
    check("no banned word or stand-in in any file", not bad_b, "; ".join(bad_b))
    check("no em dashes or en dashes (DAO brand kit)", not bad_d, ", ".join(bad_d))
    check("no emoji (DAO brand kit)", not bad_e, ", ".join(bad_e))
    check("no filler verbs (DAO brand kit)", not bad_f, "; ".join(bad_f))
    check("no personal credit in the deliverables, site or PDF", not bad_c, "; ".join(bad_c))

    # 3. Facts
    print("\n== Facts ==")
    fid = {f["id"]: f for f in facts["facts"]}
    used = {x for l in script["lines"] for x in l["facts"]}
    check("every fact used by the script is in the fact sheet", used <= set(fid), ", ".join(sorted(used - set(fid))))
    check("every fact in the fact sheet is used by the script", set(fid) <= used, ", ".join(sorted(set(fid) - used)))
    no_src = [f["id"] for f in facts["facts"] if f["kind"] != "context" and not f["evidence"]]
    check("every claim about Redbelly has at least one source", not no_src, ", ".join(no_src))
    bad_ref = [e["source"] for f in facts["facts"] for e in f["evidence"] if e["source"] not in facts["sources"]]
    check("every quote points to a listed source", not bad_ref, ", ".join(bad_ref))
    official = ("redbelly.network", "tokeniser.com", "rba.gov.au")
    nonoff = [k for k, s in facts["sources"].items() if not any(d in s["url"] for d in official)]
    check("all sources are Redbelly's own material or the Reserve Bank of Australia", not nonoff, ", ".join(nonoff))

    if args.online:
        cache = {}
        for f in facts["facts"]:
            for e in f["evidence"]:
                src = facts["sources"][e["source"]]
                if src["url"] not in cache:
                    try:
                        cache[src["url"]] = norm(page_text(src["url"]))
                    except Exception as ex:  # noqa: BLE001
                        cache[src["url"]] = ""
                        print("   could not fetch", src["url"], ex)
                page = cache[src["url"]]
                parts = [norm(x) for x in e["quote"].split("...") if norm(x)]
                ok = all(p_ in page for p_ in parts)
                check(f"{f['id']} quote found on {e['source']} ({src['publisher']})", ok, "" if ok else e["quote"][:90])

    # 4. Deliverables and video specification
    print("\n== Deliverables ==")
    for p in [VIDEO, SUB / f"{NAME}.srt", SUB / f"{NAME}.vtt", SUB / "sources.md", pdf, ROOT / "index.html"]:
        check(f"{p.relative_to(ROOT)} exists", p.exists() and p.stat().st_size > 0)
    if VIDEO.exists():
        pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(VIDEO)],
                                       capture_output=True, text=True).stdout)
        v = next(s for s in pr["streams"] if s["codec_type"] == "video")
        a = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
        dur = float(pr["format"]["duration"])
        size = int(pr["format"]["size"]) / 1e6
        check("video is 90 seconds or shorter", dur <= 90.0, f"{dur:.2f} s")
        check("video is 1080p or higher", min(int(v["width"]), int(v["height"])) >= 1080, f"{v['width']}x{v['height']}")
        check("video is MP4 with H.264", pr["format"]["format_name"].startswith("mov,mp4") and v["codec_name"] == "h264", v["codec_name"])
        check("video has an AAC audio track", a is not None and a["codec_name"] == "aac", a["codec_name"] if a else "none")
        check("video file is under 100 MB (fits GitHub and X)", size < 100, f"{size:.1f} MB")
        srt = (SUB / f"{NAME}.srt").read_text()
        ends = re.findall(r"--> (\d\d):(\d\d):(\d\d),(\d\d\d)", srt)
        last = max(int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000 for h, m, s, ms in ends)
        check("captions end before the video does", last <= dur, f"last cue {last:.2f} s")
        cap_words = re.sub(r"\d+\n\d\d:.*?\n", " ", srt)
        check("captions say exactly what the script says", norm(cap_words) == norm(entry_texts["narration script"]))
        ln = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(VIDEO), "-af", "ebur128=peak=true", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        lufs = float(re.findall(r"I:\s+(-?\d+\.\d) LUFS", ln)[-1])
        tp = float(re.findall(r"Peak:\s+(-?\d+\.\d) dBFS", ln)[-1])
        check("loudness is social-ready (-14 LUFS, within 1 LU)", abs(lufs + 14) <= 1.0, f"{lufs} LUFS")
        check("true peak at or below -1 dBTP", tp <= -0.9, f"{tp} dBTP")

    if args.asr and VIDEO.exists():
        print("\n== Spoken words versus the script (Whisper) ==")
        import librosa
        from faster_whisper import WhisperModel
        wav = ROOT / "build" / "asr.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VIDEO), "-ac", "1", "-ar", "16000", str(wav)], check=True)
        audio, _ = librosa.load(wav, sr=16000)
        model = WhisperModel("medium.en", device="cpu", compute_type="int8", cpu_threads=4)
        segs, _ = model.transcribe(audio, beam_size=5, language="en")
        heard = " ".join(s.text for s in segs)
        # Whisper spells the American way and splits the name; the sounds are the same.
        def spoken(x):
            x = norm(x).replace("red belly", "redbelly").replace("c s i r o", "csiro")
            return re.sub(r"(\w)iz(ation|e|ed)\b", r"\1is\2", x).replace("trialed", "trialled").split()
        heard_n, want_n = spoken(heard), spoken(entry_texts["narration script"])
        import difflib
        sm = difflib.SequenceMatcher(a=want_n, b=heard_n, autojunk=False)
        diffs = [(want_n[i1:i2], heard_n[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
        (ROOT / "build" / "asr-transcript.txt").write_text(heard.strip() + "\n")
        check("the voice says every word of the script and nothing else", not diffs, "; ".join(f"{' '.join(a)} -> {' '.join(b)}" for a, b in diffs))

    # 5. Licences for everything third party
    print("\n== Licences ==")
    for p in ["assets/fonts/OFL-BeVietnamPro.txt", "assets/fonts/OFL-JetBrainsMono.txt", "assets/icons/LICENSE-lucide.txt", "CREDITS.md"]:
        check(f"{p} present", (ROOT / p).exists())

    failed = [r for r in results if not r[1]]
    lines = ["# Verification report", "",
             f"Generated by `src/checks/verify.py`. {len(results) - len(failed)} of {len(results)} checks passed.", "",
             "| Result | Check | Detail |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append(f"| {'PASS' if ok else 'FAIL'} | {name} | {detail.replace('|', '/')} |")
    (SUB / "verification-report.md").write_text("\n".join(lines) + "\n")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
