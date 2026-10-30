"""Build the submission PDF: cover, the entry, script, storyboard, facts, checks, production.

Writes build/pdf/submission.html, then prints it to
submission/redbelly-in-simple-terms-submission.pdf with Chromium (src/docs/pdf.mjs).
Run after build_site.py, which makes the storyboard images.
"""
import subprocess
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import BENCHMARKS, FAILURES, NAME, PRODUCTION, ROOT, STORYBOARD, load, long_date, mmss  # noqa: E402


def icon(name, size=16, color="currentColor"):
    svg = (ROOT / "assets/icons" / f"{name}.svg").read_text().split("-->", 1)[-1].strip()
    return svg.replace('width="24"', f'width="{size}"').replace('height="24"', f'height="{size}"').replace("currentColor", color)


CSS = """
@page{size:A4;margin:18mm 16mm 20mm}
@page :first{margin:0}
:root{--surface:#EDF1F4;--slate:#FFFFFF;--steel:#DDE6ED;--edge:#D3DBE1;--high:#DAE1E7;--container:#E6EBEF;--on:#0F1A22;--on2:#394853;
--outline:#596975;--ov:#C3CDD4;--brand:#EF5350;--primary:#B3272A;--ok:#15803D;--sans:"Be Vietnam Pro",sans-serif;--mono:"JetBrains Mono",monospace}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font:400 10pt/1.5 var(--sans);color:var(--on);background:#fff}
.cover{height:297mm;background:#1d3140;color:#f1f5f8;padding:20mm 18mm;display:flex;flex-direction:column;page-break-after:always;position:relative;overflow:hidden}
.cover .logo{height:16mm;width:auto;align-self:flex-start}
.cover .caps{color:#8fa1ad;margin-top:16mm}.cover .caps b{color:#ffb3ae}
.cover h1{font:700 34pt/1.05 var(--sans);letter-spacing:-.02em;margin:4mm 0 0}
.cover .lead{font-size:13pt;color:#c2ced6;max-width:150mm;margin:5mm 0 0;line-height:1.45}
.cover img.poster{width:100%;border-radius:3mm;border:0.3mm solid #34444f;margin-top:10mm}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:9mm}
.kv div{border-top:0.3mm solid #34444f;padding-top:2.5mm}
.kv .k{font:500 7.5pt/1.3 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:#8fa1ad}
.kv .v{font:600 12pt/1.3 var(--sans);color:#f1f5f8;margin-top:1mm}
.cover .foot{margin-top:auto;display:flex;justify-content:space-between;font:500 7.5pt var(--mono);letter-spacing:.06em;text-transform:uppercase;color:#8fa1ad}
.caps{font:700 7.5pt/1.2 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--outline)}
h2{font:700 19pt/1.15 var(--sans);letter-spacing:-.01em;margin:2mm 0 3mm}
h3{font:600 11pt/1.3 var(--sans);margin:0 0 1.5mm}
p{margin:0 0 2.5mm;max-width:165mm}
.muted{color:var(--outline)}
.sec{page-break-before:always}
.band{background:#1d3140;color:#f1f5f8;border-radius:2mm;padding:6mm 7mm;margin:4mm 0}
.band .caps{color:#8fa1ad}
.three{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin-top:3mm}
.three .c{background:#141f26;border:0.3mm solid #263641;border-radius:2mm;padding:4mm}
.three .c h3{color:#f1f5f8;display:flex;align-items:center;gap:2mm}
.three .c p{color:#c2ced6;font-size:9pt;margin:0}
table{width:100%;border-collapse:collapse;font-size:9pt}
th{text-align:left;font:700 7pt/1.2 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--outline);padding:2mm 2.5mm;border-bottom:0.4mm solid var(--ov)}
td{padding:2.2mm 2.5mm;border-bottom:0.25mm solid var(--high);vertical-align:top}
tr{page-break-inside:avoid}
td.tc{font:500 8.5pt var(--mono);color:var(--outline);white-space:nowrap}
table.script td{padding:1.5mm 2.5mm}table.script td.fx{white-space:nowrap;width:24mm}table.script .chip{margin:0 0.6mm 0 0}
.chip{display:inline-block;font:500 7pt/1 var(--mono);letter-spacing:.04em;padding:1.2mm 1.6mm;border-radius:1mm;border:0.25mm solid var(--ov);color:var(--on2);margin:0 1mm 1mm 0;white-space:nowrap}
.board{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
.board figure{margin:0;border:0.3mm solid var(--edge);border-radius:2mm;overflow:hidden;page-break-inside:avoid;background:#fff}
.board img{display:block;width:100%}
.board figcaption{padding:3mm 3.5mm;font-size:8.8pt;color:var(--on2)}
.board .mono{font:500 7.5pt var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--outline);margin-bottom:1mm}
.fact{border:0.3mm solid var(--edge);border-radius:2mm;padding:3.5mm 4mm;margin:0 0 3.5mm;page-break-inside:avoid}
.fact .hd{display:flex;gap:2.5mm;align-items:baseline}
.fact .hd .kind{margin-left:auto;font:500 7pt var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--outline);white-space:nowrap}
.fact q{display:block;quotes:none;margin:2mm 0 0;padding:2mm 3mm;border-left:0.8mm solid var(--brand);background:#F4F6F8;color:var(--on2);font-size:8.8pt}
.fact cite{display:block;font:500 7pt var(--mono);letter-spacing:.04em;text-transform:uppercase;font-style:normal;color:var(--outline);margin-top:1mm}
.src li{margin:0 0 1.5mm;font-size:8.8pt}.src a{color:var(--primary);word-break:break-all}
.status{display:inline-flex;align-items:center;gap:1.5mm;font:600 7.5pt var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--ok);white-space:nowrap}
.status i{width:1.8mm;height:1.8mm;border-radius:9999px;background:var(--ok);display:inline-block}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}
.card{border:0.3mm solid var(--edge);border-radius:2mm;padding:3.5mm 4mm}
.card p{font-size:8.8pt;color:var(--on2);margin:0}
code{font:500 8.5pt var(--mono);background:var(--container);padding:0.3mm 1.2mm;border-radius:1mm}
.files td:first-child{font:500 8.5pt var(--mono);white-space:nowrap}
"""


def build(d):
    f, tl, pr = d["facts"], d["tl"], d["probe"]
    secs = round(pr.get("duration", tl["duration"]))
    verified = long_date(f["last_verified"])
    logo = (ROOT / "site/img/dao-logo-on-dark.png").as_uri()
    poster = (ROOT / "site/img/poster.png").as_uri()
    checks = d["checks"]
    kv = [("Format", "Video, 16:9"), ("Length", f"{secs} seconds"), ("Resolution", f"{pr.get('w', 1920)} x {pr.get('h', 1080)}, {pr.get('fps', 30)} fps"),
          ("Captions", "Burned in, plus SRT"), ("Narration", f"{d['words']} words"), ("Facts", f"{len(f['facts'])}, verified {verified}")]
    kv_html = "".join(f'<div><div class="k">{k}</div><div class="v">{escape(v)}</div></div>' for k, v in kv)

    rows = "".join(f'<tr><td class="tc">{mmss(l["start"])}</td><td>{escape(l["text"])}</td><td class="fx">{"".join(f"<span class=chip>{x}</span>" for x in l["facts"])}</td></tr>' for l in tl["lines"])
    names = {s["id"]: s["name"] for s in tl["scenes"]}
    starts = {s["id"]: s["start"] for s in tl["scenes"]}
    board = "".join(
        f'<figure><img src="{(ROOT / "site/img" / f"scene-{i:02d}.png").as_uri()}"><figcaption><div class="mono">{i:02d} &nbsp; {mmss(starts[sid])} &nbsp; {escape(names[sid])}</div>{escape(desc)}</figcaption></figure>'
        for i, (sid, _, _, desc) in enumerate(STORYBOARD, 1))
    srcs = f["sources"]
    facts_html = ""
    for x in f["facts"]:
        kind = {"context": "Context", "redbelly": "About Redbelly", "definition": "Definition"}[x["kind"]]
        qs = "".join(f'<q>"{escape(e["quote"])}"<cite>{e["source"]} {escape(srcs[e["source"]]["publisher"])}{", " + e["page"] if e.get("page") else ""}</cite></q>' for e in x["evidence"])
        if not qs:
            qs = ""
        facts_html += f'<div class="fact"><div class="hd"><span class="chip">{x["id"]}</span><h3>{escape(x["claim"])}</h3><span class="kind">{kind}</span></div><p class="muted" style="font-size:8.8pt;margin:1mm 0 0">{escape(x["check"])}</p>{qs}</div>'
    src_list = "".join(f'<li><b>{sid}</b> {escape(s["publisher"])}, <i>{escape(s["title"])}</i>.<br><a href="{escape(s["url"])}">{escape(s["url"])}</a></li>' for sid, s in srcs.items())
    bench = "".join(f'<div class="card"><span class="status"><i></i>Met</span><h3 style="margin-top:2mm">{escape(a)}</h3><p>{escape(b)}</p></div>' for a, b in BENCHMARKS)
    fails = "".join(f'<tr><td style="width:32%">{escape(a)}</td><td><span class="status"><i></i>Clear</span></td><td>{escape(b)}</td></tr>' for a, b in FAILURES)
    prod = "".join(f'<tr><td style="font-weight:600;width:22%">{escape(a)}</td><td>{escape(b)}</td></tr>' for a, b in PRODUCTION)
    files = [(f"{NAME}.mp4", "The entry. 1920 x 1080, H.264 and AAC, captions burned in"),
             (f"{NAME}.srt", "Captions as a separate file (SubRip)"), (f"{NAME}.vtt", "Captions as a separate file (WebVTT)"),
             ("sources.md", "Source list with every quote"), ("transcript.txt", "Narration as plain text"),
             ("verification-report.md", "Output of the automated checks"), (f"{NAME}-submission.pdf", "This document")]
    files_html = "".join(f"<tr><td>{a}</td><td>{escape(b)}</td></tr>" for a, b in files)
    ideas = [("user-check", "Verified people", "Everyone trading has proved who they are, like showing ID at a bank, and their private details stay protected."),
             ("list-checks", "Rules built in", "Before a trade goes through, the system checks the buyer is allowed to buy it. If not, it does not happen."),
             ("arrow-left-right", "Done in one step", "Payment and ownership move together. If either side fails, nothing moves. Once it is done, it is final.")]
    ideas_html = "".join(f'<div class="c"><h3>{icon(ic, 14, "#ffb3ae")}{t}</h3><p>{escape(b)}</p></div>' for ic, t, b in ideas)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Redbelly in Simple Terms, submission</title>
<link rel="stylesheet" href="{(ROOT / 'assets/fonts/fonts.css').as_uri()}"><style>{CSS}</style></head><body>

<div class="cover">
  <img class="logo" src="{logo}" alt="Redbelly DAO">
  <div class="caps"><b>Redbelly DAO task submission</b> &nbsp; Video entry</div>
  <h1>Redbelly in Simple Terms</h1>
  <p class="lead">What Redbelly does and why it matters, in {secs} seconds of everyday language. Made for a friend, a parent or a business owner who has never touched crypto.</p>
  <img class="poster" src="{poster}" alt="">
  <div class="kv">{kv_html}</div>
  <div class="foot"><span>Facts last verified {verified}</span><span>Not posted publicly before judging</span></div>
</div>

<div>
  <div class="caps">01 &nbsp; The entry</div>
  <h2>Three ideas, said in plain words</h2>
  <p>The video opens with a question anyone has felt: a photo crosses the world in a second, so why does buying into a fund still take two business days? The answer is that the money and the record of who owns what live in different places, and different firms keep their own copies. Redbelly brings the two together.</p>
  <p>From there the video makes three points, each with its own scene, and the close repeats them as the line a viewer will remember.</p>
  <div class="band"><div class="caps">The takeaway</div><div class="three">{ideas_html}</div></div>
  <p>It then names the idea (tokenisation), shows what it is used for (property, loans, bonds and investment funds), and ends on where Redbelly comes from: research at the University of Sydney and CSIRO, and a place as one of three platforms that carried the Reserve Bank of Australia's pilot digital money in Project Acacia.</p>
  <h3 style="margin-top:6mm">What is in the submission</h3>
  <table class="files"><tbody>{files_html}</tbody></table>
  <p class="muted" style="margin-top:4mm">All files are in the <code>submission/</code> folder of the repository. The companion website, <code>index.html</code> at the repository root, plays the video and carries the same material.</p>
</div>

<div class="sec">
  <div class="caps">02 &nbsp; Script</div>
  <h2>Every word of the narration</h2>
  <p>{d['words']} words in 21 lines. Timecodes are from the final cut. The chips show the facts each line relies on (section 04).</p>
  <table class="script"><thead><tr><th>Time</th><th>Narration</th><th>Facts</th></tr></thead><tbody>{rows}</tbody></table>
</div>

<div class="sec">
  <div class="caps">03 &nbsp; Storyboard</div>
  <h2>Eight scenes, one idea each</h2>
  <p>Frames taken from the finished video, with the burned-in captions a viewer sees with the sound off.</p>
  <div class="board">{board}</div>
</div>

<div class="sec">
  <div class="caps">04 &nbsp; Fact check</div>
  <h2>Where every fact comes from</h2>
  <p>Every statement about Redbelly is backed by Redbelly's own public material or by the Reserve Bank of Australia. Quotes are copied from the source and an ellipsis marks words left out. Facts last verified {verified}.</p>
  {facts_html}
  <h3 style="margin-top:6mm">Sources</h3>
  <ol class="src" style="padding-left:5mm;margin:0">{src_list}</ol>
</div>

<div class="sec">
  <div class="caps">05 &nbsp; Checks</div>
  <h2>The brief, point by point</h2>
  <p>{f"{checks[0]} of {checks[1]} automated checks pass" if checks else "Automated checks"}. The checker is <code>src/checks/verify.py</code>; its full output is <code>verification-report.md</code>.</p>
  <div class="grid3">{bench}</div>
  <h3 style="margin-top:6mm">Failure criteria</h3>
  <table><thead><tr><th>Criterion</th><th>Status</th><th>How it is avoided</th></tr></thead><tbody>{fails}</tbody></table>
</div>

<div class="sec">
  <div class="caps">06 &nbsp; Production</div>
  <h2>How it was made</h2>
  <p>Everything is built from source in the repository, so every frame and every sound can be rebuilt and inspected.</p>
  <table><tbody>{prod}</tbody></table>
  <h3 style="margin-top:6mm">Licences</h3>
  <p>No stock footage, photos, music or samples. The voice model is MIT licensed. Music and sound effects are synthesised in code for this entry. Be Vietnam Pro and JetBrains Mono are under the SIL Open Font License. Icons are Lucide, under the ISC licence. The Redbelly and Redbelly DAO logos come unaltered from the official brand kits. Full details are in <code>CREDITS.md</code>.</p>
</div>
</body></html>
"""


def main():
    d = load()
    out = ROOT / "build/pdf"
    out.mkdir(parents=True, exist_ok=True)
    (out / "submission.html").write_text(build(d))
    subprocess.run(["node", str(ROOT / "src/docs/pdf.mjs")], check=True)


if __name__ == "__main__":
    main()
