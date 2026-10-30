"""Build the companion website (index.html at the repository root, images in site/img)
and submission/sources.md. Serving the page from the root means it works as is on
Vercel, GitHub Pages or any static host, and opened straight from disk.

The site follows the Redbelly DAO Task Board brand kit: dark slate by default with a
light theme, one red accent, Be Vietnam Pro for words, JetBrains Mono for machine values.
Storyboard images come from build/stills (made by src/video/render.mjs --stills).
"""
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import (BENCHMARKS, FAILURES, NAME, PRODUCTION, ROOT, STORYBOARD, load, long_date, mmss,  # noqa: E402
                     storyboard_times)

SITE = ROOT / "site"
IMG = SITE / "img"


def png(src, dst, width):
    im = Image.open(src).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.quantize(colors=256, dither=Image.Dither.FLOYDSTEINBERG).save(dst, optimize=True)


def icon(name, size=20):
    svg = (ROOT / "assets/icons" / f"{name}.svg").read_text()
    svg = svg.split("-->", 1)[-1].strip()
    svg = svg.replace('width="24"', f'width="{size}"').replace('height="24"', f'height="{size}"')
    return svg.replace("<svg", '<svg aria-hidden="true" focusable="false"', 1)


def images(d):
    IMG.mkdir(parents=True, exist_ok=True)
    stills = ROOT / "build/stills"
    times = storyboard_times(d["tl"]) + [d["poster_t"], d["og_t"]]
    subprocess.run(["node", str(ROOT / "src/video/render.mjs"), "--stills", ",".join(f"{t:.2f}" for t in times)], check=True)
    out = []
    for i, t in enumerate(storyboard_times(d["tl"]), 1):
        src = stills / f"t_{t:06.2f}.png"
        png(src, IMG / f"scene-{i:02d}.png", 960)
        out.append(f"site/img/scene-{i:02d}.png")
    poster = stills / f"t_{d['poster_t']:06.2f}.png"
    png(poster, IMG / "poster.png", 1280)
    og = Image.open(stills / f"t_{d['og_t']:06.2f}.png").convert("RGB")
    og = og.crop((0, 35, 1920, 1043)).resize((1200, 630), Image.LANCZOS)
    og.quantize(colors=256, dither=Image.Dither.FLOYDSTEINBERG).save(IMG / "og.png", optimize=True)
    shutil.copy(ROOT / "assets/brand/dao-logo-on-dark.png", IMG / "dao-logo-on-dark.png")
    shutil.copy(ROOT / "assets/brand/dao-logo-on-light.png", IMG / "dao-logo-on-light.png")
    shutil.copy(ROOT / "assets/brand/icon.png", IMG / "icon.png")  # square favicon from the DAO kit
    return out


def sources_md(d):
    f = d["facts"]
    lines = ["# Sources", "",
             f"Every fact about Redbelly in the video, and where it comes from. Facts last verified {long_date(f['last_verified'])}.",
             "Quotes are copied from the source. An ellipsis marks words left out.", "",
             "## Source list", ""]
    for sid, s in f["sources"].items():
        lines.append(f"- **{sid}** {s['publisher']}, *{s['title']}*. <{s['url']}> (accessed {long_date(s['accessed'])})")
    lines += ["", "## Facts, as said in the video", ""]
    for x in f["facts"]:
        lines.append(f"### {x['id']}. {x['claim']}")
        lines.append("")
        lines.append(f"{x['check']}")
        lines.append("")
        for e in x["evidence"]:
            pg = f", {e['page']}" if e.get("page") else ""
            lines.append(f"- {e['source']}{pg}: \"{e['quote']}\"")
        if not x["evidence"]:
            lines.append("- No source needed: everyday comparison, not a statement about Redbelly.")
        lines.append("")
    lines += ["## On-screen text that is not narration", ""]
    for o in f["on_screen"]:
        ref = f" Facts: {', '.join(o['facts'])}." if o.get("facts") else ""
        lines.append(f"- \"{o['text']}\" ({o['kind']}). {o.get('note', '')}{ref}".rstrip())
    (ROOT / "submission/sources.md").write_text("\n".join(lines) + "\n")


CSS = """
:root{color-scheme:dark;--surface:#0c1317;--deep:#0a1014;--lowest:#070c0f;--low:#111a20;--container:#17222a;--high:#223039;
--slate:#141f26;--steel:#1d3140;--edge:#263641;--on:#f1f5f8;--on2:#c2ced6;--outline:#8fa1ad;--ov:#34444f;--brand:#EF5350;
--brand-hover:#f95a56;--primary:#ffb3ae;--ok:#86EFAC;--warn:#FCD34D;
--sans:"Be Vietnam Pro",ui-sans-serif,system-ui,sans-serif;--mono:"JetBrains Mono",ui-monospace,monospace}
:root[data-theme=light]{color-scheme:light;--surface:#EDF1F4;--deep:#EDF1F4;--lowest:#FFFFFF;--low:#F4F6F8;--container:#E6EBEF;
--high:#DAE1E7;--slate:#FFFFFF;--steel:#DDE6ED;--edge:#D3DBE1;--on:#0F1A22;--on2:#394853;--outline:#596975;--ov:#C3CDD4;
--brand-hover:#D93E3B;--primary:#B3272A;--ok:#15803D;--warn:#A16207}
@media (prefers-color-scheme:light){:root:not([data-theme=dark]){color-scheme:light;--surface:#EDF1F4;--deep:#EDF1F4;--lowest:#FFFFFF;
--low:#F4F6F8;--container:#E6EBEF;--high:#DAE1E7;--slate:#FFFFFF;--steel:#DDE6ED;--edge:#D3DBE1;--on:#0F1A22;--on2:#394853;
--outline:#596975;--ov:#C3CDD4;--brand-hover:#D93E3B;--primary:#B3272A;--ok:#15803D;--warn:#A16207}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--deep);color:var(--on);font:400 17px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--primary);text-underline-offset:3px}a:hover{color:var(--brand)}
.wrap{max-width:1280px;margin:0 auto;padding:0 64px}
@media (max-width:760px){.wrap{padding:0 16px}body{font-size:16px}}
header.top{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--deep) 82%,transparent);backdrop-filter:blur(14px);
border-bottom:1px solid var(--edge)}
header.top .wrap{display:flex;align-items:center;gap:24px;height:72px}
header.top img{height:40px;width:auto;display:block}
.logo-light{display:none!important}
:root[data-theme=light] .logo-dark{display:none!important}:root[data-theme=light] .logo-light{display:block!important}
@media (prefers-color-scheme:light){:root:not([data-theme=dark]) .logo-dark{display:none!important}:root:not([data-theme=dark]) .logo-light{display:block!important}}
nav{display:flex;gap:22px;margin-left:auto;flex-wrap:wrap}
nav a{color:var(--on2);text-decoration:none;font-weight:600;font-size:14px}nav a:hover{color:var(--on)}
.theme{background:none;border:1px solid var(--ov);color:var(--on2);border-radius:4px;padding:7px 10px;cursor:pointer;display:inline-flex}
.theme:hover{border-color:var(--brand);color:var(--on)}
@media (max-width:860px){nav{display:none}.theme{margin-left:auto}}
.hero{background:#1d3140;color:#f1f5f8;border-bottom:1px solid #263641}
.hero .wrap{padding-top:56px;padding-bottom:56px;display:grid;grid-template-columns:1fr;gap:28px}
.caps{font:700 12px/1.2 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--outline)}
.hero .caps{color:#8fa1ad}.hero .caps b{color:#ffb3ae;font-weight:700}
h1{font:700 48px/1.08 var(--sans);letter-spacing:-.02em;margin:10px 0 0}
@media (max-width:760px){h1{font-size:36px}}
.lead{font-size:19px;color:#c2ced6;max-width:70ch;margin:14px 0 0}
.player{border-radius:8px;overflow:hidden;border:1px solid #34444f;background:#070c0f;aspect-ratio:16/9}
.player video{width:100%;height:100%;display:block}
.meta{display:flex;flex-wrap:wrap;gap:10px 22px;font:500 13px/1.4 var(--mono);letter-spacing:.05em;text-transform:uppercase;color:#c2ced6}
.meta span b{color:#f1f5f8;font-weight:600}
.btns{display:flex;flex-wrap:wrap;gap:12px}
.btn{display:inline-flex;align-items:center;gap:10px;padding:12px 18px;border-radius:4px;font:600 15px/1 var(--sans);text-decoration:none;white-space:nowrap}
.btn.primary{background:#EF5350;color:#fff}.btn.primary:hover{background:#f95a56;color:#fff}
.btn.ghost{border:1px solid #34444f;color:#f1f5f8}.btn.ghost:hover{border-color:#EF5350;color:#fff}
section{padding:72px 0;border-bottom:1px solid var(--edge)}
section .head{max-width:75ch;margin-bottom:32px}
h2{font:700 32px/1.15 var(--sans);letter-spacing:-.01em;margin:8px 0 10px}
h3{font:600 20px/1.3 var(--sans);margin:0 0 6px}
p{margin:0 0 12px;max-width:75ch}.muted{color:var(--outline)}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
@media (max-width:900px){.grid3,.grid2{grid-template-columns:1fr}}
.card{background:var(--slate);border:1px solid var(--edge);border-radius:8px}
.card .ch{padding:18px 22px;border-bottom:1px solid var(--edge);display:flex;align-items:center;gap:12px}
.card .cb{padding:18px 22px}
.idea .ch svg{color:var(--primary)}
.mono{font:500 13px/1.4 var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--outline)}
.status{display:inline-flex;align-items:center;gap:8px;font:600 13px/1 var(--mono);letter-spacing:.05em;text-transform:uppercase;white-space:nowrap}
.status i{width:8px;height:8px;border-radius:9999px;background:var(--ok);display:inline-block}.status{color:var(--ok)}
table{width:100%;border-collapse:collapse;font-size:16px}
th{text-align:left;font:700 12px/1.2 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--outline);padding:12px 14px;border-bottom:1px solid var(--ov)}
td{padding:14px;border-bottom:1px solid var(--high);vertical-align:top}
td.tc{font:500 14px/1.5 var(--mono);color:var(--outline);white-space:nowrap}
.tablebox{background:var(--slate);border:1px solid var(--edge);border-radius:8px;overflow-x:auto}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:500 12px/1 var(--mono);letter-spacing:.05em;padding:6px 8px;border-radius:4px;border:1px solid var(--ov);color:var(--on2);text-decoration:none;white-space:nowrap}
.chip:hover{border-color:var(--brand);color:var(--on)}
.scene img{display:block;width:100%;height:auto;border-bottom:1px solid var(--edge);border-radius:8px 8px 0 0}
.scene .cb p{color:var(--on2);font-size:16px;margin:0}
.fact{scroll-margin-top:90px}
.fact blockquote{margin:12px 0 0;padding:12px 16px;border-left:3px solid var(--brand);background:var(--low);border-radius:0 4px 4px 0;color:var(--on2);font-size:15px}
.fact blockquote cite{display:block;margin-top:8px;font:500 12px/1.4 var(--mono);letter-spacing:.04em;text-transform:uppercase;font-style:normal}
.fact .kind{margin-left:auto}
.cols{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}@media (max-width:900px){.cols{grid-template-columns:1fr}}
ol.src{padding-left:22px;margin:0}ol.src li{margin:0 0 10px}
code{font:500 14px var(--mono);background:var(--container);padding:2px 6px;border-radius:4px}
pre{font:500 14px/1.6 var(--mono);background:var(--lowest);border:1px solid var(--edge);border-radius:8px;padding:18px;overflow-x:auto;color:var(--on2)}
.files td:first-child{font:500 14px var(--mono)}
footer{padding:40px 0 64px;color:var(--outline);font-size:14px}
footer .wrap{display:flex;flex-wrap:wrap;gap:12px 32px;justify-content:space-between}
:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
"""


def page(d, scenes):
    f, tl, pr = d["facts"], d["tl"], d["probe"]
    dur = pr.get("duration", tl["duration"])
    secs = round(dur)
    verified = long_date(f["last_verified"])
    checks = d["checks"]
    checks_txt = f"{checks[0]} of {checks[1]} automated checks pass" if checks else "Automated checks"

    ideas = [("user-check", "Verified people", "Everyone trading has proved who they are, a bit like showing ID at a bank, and their private details stay protected.", ["F09", "F10"]),
             ("list-checks", "Rules built in", "Before any trade goes through, the system checks the buyer is allowed to buy that product. If not, the trade does not happen.", ["F11"]),
             ("arrow-left-right", "Done in one step", "Payment and ownership move together. If either side fails, nothing moves. Once it is done, it is final.", ["F07", "F08"])]
    ideas_html = "".join(
        f'<div class="card idea"><div class="ch">{icon(ic, 26)}<h3 style="margin:0">{t}</h3></div><div class="cb"><p>{escape(body)}</p>'
        f'<div class="chips">{"".join(f"<a class=chip href=#{x}>{x}</a>" for x in fx)}</div></div></div>'
        for ic, t, body, fx in ideas)

    rows = "".join(
        f'<tr><td class="tc">{mmss(l["start"])}</td><td>{escape(l["text"])}</td>'
        f'<td><div class="chips">{"".join(f"<a class=chip href=#{x}>{x}</a>" for x in l["facts"])}</div></td></tr>'
        for l in tl["lines"])

    names = {s["id"]: s["name"] for s in tl["scenes"]}
    starts = {s["id"]: s["start"] for s in tl["scenes"]}
    board = "".join(
        f'<figure class="card scene" style="margin:0"><img src="{src}" width="960" height="540" alt="Frame from scene {i}, {escape(names[sid])}">'
        f'<div class="cb"><div class="mono" style="margin-bottom:6px">{i:02d} &nbsp; {mmss(starts[sid])} &nbsp; {escape(names[sid])}</div><p>{escape(desc)}</p></div></figure>'
        for i, ((sid, _, _, desc), src) in enumerate(zip(STORYBOARD, scenes), 1))

    srcs = f["sources"]
    facts_html = ""
    for x in f["facts"]:
        kind = {"context": "Context", "redbelly": "About Redbelly", "definition": "Definition"}[x["kind"]]
        qs = "".join(
            f'<blockquote>"{escape(e["quote"])}"<cite><a href="{escape(srcs[e["source"]]["url"])}">{e["source"]} {escape(srcs[e["source"]]["publisher"])}</a>'
            f'{", " + e["page"] if e.get("page") else ""}</cite></blockquote>' for e in x["evidence"])
        if not qs:
            qs = ""
        facts_html += (f'<div class="card fact" id="{x["id"]}"><div class="ch"><span class="chip">{x["id"]}</span><h3 style="margin:0">{escape(x["claim"])}</h3>'
                       f'<span class="mono kind">{kind}</span></div><div class="cb"><p class="muted">{escape(x["check"])}</p>{qs}</div></div>')
    src_list = "".join(f'<li><a href="{escape(s["url"])}">{escape(s["publisher"])}, {escape(s["title"])}</a> <span class="mono">({sid})</span></li>' for sid, s in srcs.items())

    bench = "".join(f'<div class="card"><div class="ch"><span class="status"><i></i>Met</span></div><div class="cb"><h3>{escape(a)}</h3><p class="muted">{escape(b)}</p></div></div>' for a, b in BENCHMARKS)
    fails = "".join(f'<tr><td>{escape(a)}</td><td><span class="status"><i></i>Clear</span></td><td>{escape(b)}</td></tr>' for a, b in FAILURES)
    prod = "".join(f'<tr><td style="font-weight:600;white-space:nowrap">{escape(a)}</td><td>{escape(b)}</td></tr>' for a, b in PRODUCTION)

    files = [(f"submission/{NAME}.mp4", "The entry. 1920 x 1080, H.264 and AAC, captions burned in"),
             (f"submission/{NAME}.srt", "Captions as a separate file (SubRip)"),
             (f"submission/{NAME}.vtt", "Captions as a separate file (WebVTT)"),
             (f"submission/{NAME}-submission.pdf", "Submission document: script, storyboard, facts, sources and checks"),
             ("submission/sources.md", "The source list with every quote"),
             ("submission/transcript.txt", "The narration as plain text"),
             ("submission/verification-report.md", "Output of the automated checks")]
    files_html = "".join(f'<tr><td><a href="{p}">{p.split("/")[-1]}</a></td><td>{escape(t)}</td></tr>' for p, t in files)

    meta = (f'<span><b>{secs} s</b> long</span><span><b>{pr.get("w", 1920)} x {pr.get("h", 1080)}</b></span><span><b>{pr.get("fps", 30)} fps</b></span>'
            f'<span><b>H.264</b> + AAC</span><span>Captions <b>burned in</b> + SRT</span><span><b>{d["words"]}</b> words</span>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Redbelly in Simple Terms</title>
<meta name="description" content="A {secs} second video that explains what Redbelly does and why it matters, in everyday language.">
<meta property="og:title" content="Redbelly in Simple Terms">
<meta property="og:description" content="What Redbelly does and why it matters, in {secs} seconds of everyday language.">
<meta property="og:image" content="site/img/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="noindex">
<link rel="icon" type="image/png" sizes="512x512" href="site/img/icon.png">
<link rel="stylesheet" href="assets/fonts/fonts.css">
<style>{CSS}</style>
<script>try{{const t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body>
<header class="top"><div class="wrap">
  <img class="logo-dark" src="site/img/dao-logo-on-dark.png" alt="Redbelly DAO" width="56" height="40">
  <img class="logo-light" src="site/img/dao-logo-on-light.png" alt="Redbelly DAO" width="56" height="40">
  <nav><a href="#watch">Watch</a><a href="#idea">The idea</a><a href="#script">Script</a><a href="#storyboard">Storyboard</a><a href="#facts">Facts</a><a href="#checks">Checks</a><a href="#files">Files</a></nav>
  <button class="theme" id="theme" aria-label="Switch between light and dark theme">{icon("sun-moon", 18)}</button>
</div></header>

<div class="hero" id="watch"><div class="wrap">
  <div>
    <div class="caps"><b>Redbelly DAO task</b> &nbsp; Video entry</div>
    <h1>Redbelly in Simple Terms</h1>
    <p class="lead">A {secs} second video that explains what Redbelly does and why it matters, for someone who has never touched crypto. It never uses the word the task rules out, or any stand-in for it.</p>
  </div>
  <div class="player"><video controls preload="metadata" poster="site/img/poster.png" src="submission/{NAME}.mp4"></video></div>
  <div class="meta">{meta}</div>
  <div class="btns">
    <a class="btn primary" href="submission/{NAME}.mp4" download>{icon("file-check-2", 18)}Download video</a>
    <a class="btn ghost" href="submission/{NAME}-submission.pdf">{icon("file-text", 18)}Submission PDF</a>
    <a class="btn ghost" href="submission/{NAME}.srt" download>{icon("scroll-text", 18)}Captions</a>
  </div>
</div></div>

<main>
<section id="idea"><div class="wrap">
  <div class="head"><div class="caps">The idea</div><h2>Three ideas, said in plain words</h2>
  <p>The video opens with a question anyone has felt: a photo crosses the world in a second, so why does buying into a fund still take two business days? The answer is that the money and the record of who owns what live in different places. Redbelly brings them together. The rest of the video is three ideas, and the close repeats them.</p></div>
  <div class="grid3">{ideas_html}</div>
</div></section>

<section id="script"><div class="wrap">
  <div class="head"><div class="caps">Script</div><h2>Every word of the narration</h2>
  <p>{d["words"]} words in 21 lines. Timecodes are from the final cut. Each line links to the facts it relies on.</p></div>
  <div class="tablebox"><table><thead><tr><th>Time</th><th>Narration</th><th>Facts</th></tr></thead><tbody>{rows}</tbody></table></div>
</div></section>

<section id="storyboard"><div class="wrap">
  <div class="head"><div class="caps">Storyboard</div><h2>Eight scenes, one idea each</h2>
  <p>Frames taken from the finished video. The burned-in captions are what a viewer sees with the sound off.</p></div>
  <div class="grid2">{board}</div>
</div></section>

<section id="facts"><div class="wrap">
  <div class="head"><div class="caps">Fact check</div><h2>Where every fact comes from</h2>
  <p>Every statement about Redbelly is backed by Redbelly's own public material or by the Reserve Bank of Australia. Quotes are copied from the source, and an ellipsis marks words left out. Facts last verified {verified}.</p></div>
  <div style="display:grid;gap:16px">{facts_html}</div>
  <div class="card" style="margin-top:24px"><div class="ch"><h3 style="margin:0">Sources</h3></div><div class="cb"><ol class="src">{src_list}</ol></div></div>
</div></section>

<section id="checks"><div class="wrap">
  <div class="head"><div class="caps">Checks</div><h2>The brief, point by point</h2>
  <p>{checks_txt}. The checker lives in <code>src/checks/verify.py</code> and its last report is in <code>submission/verification-report.md</code>.</p></div>
  <div class="grid3">{bench}</div>
  <div class="tablebox" style="margin-top:24px"><table><thead><tr><th>Failure criterion</th><th>Status</th><th>How it is avoided</th></tr></thead><tbody>{fails}</tbody></table></div>
</div></section>

<section id="made"><div class="wrap">
  <div class="head"><div class="caps">Production</div><h2>How it was made</h2>
  <p>Everything is built from source in this repository, so every frame and every sound can be rebuilt and inspected. Licences for the fonts, icons and logos are in <code>CREDITS.md</code>.</p></div>
  <div class="tablebox"><table><tbody>{prod}</tbody></table></div>
  <pre>bash src/build.sh          # timeline, music, mix, picture, encode, captions, site, PDF, checks
python src/checks/verify.py --online --asr   # re-check sources and the spoken words</pre>
</div></section>

<section id="files" style="border-bottom:0"><div class="wrap">
  <div class="head"><div class="caps">Files</div><h2>Deliverables</h2></div>
  <div class="tablebox files"><table><tbody>{files_html}</tbody></table></div>
</div></section>
</main>

<footer><div class="wrap"><span>Facts last verified {verified}.</span><span>Built to the Redbelly DAO Task Board brand kit.</span></div></footer>
<script>
document.getElementById("theme").addEventListener("click",()=>{{
  const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":!matchMedia("(prefers-color-scheme: light)").matches;
  r.dataset.theme=dark?"light":"dark";try{{localStorage.setItem("theme",r.dataset.theme)}}catch(e){{}}
}});
</script>
</body>
</html>
"""


def main():
    d = load()
    tl = d["tl"]
    d["poster_t"] = round(tl["cues"]["onestep.together"] + 0.55, 2)
    d["og_t"] = round(tl["duration"] - 1.0, 2)
    scenes = images(d)
    (ROOT / "index.html").write_text(page(d, scenes))
    sources_md(d)
    print("index.html and submission/sources.md written")


if __name__ == "__main__":
    main()
