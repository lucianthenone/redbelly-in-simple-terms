// Frame-accurate renderer for the stage.
//   node src/video/render.mjs --stills 3.2,10,24.5   -> build/stills/t_<time>.png
//   node src/video/render.mjs                         -> build/video/picture.mkv (lossless)
// Each worker owns one Chromium page and a contiguous block of frames, and pipes
// PNG frames into its own lossless ffmpeg segment. Segments are joined at the end.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright"); // resolved through NODE_PATH or a local install
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const tl = JSON.parse(readFileSync(join(root, "build/timeline.json"), "utf8"));
writeFileSync(join(root, "build/timeline.js"), `window.TL = ${JSON.stringify(tl)};\n`);
const url = pathToFileURL(join(root, "src/video/stage.html")).href + "?render=1";
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("pageerror", (e) => { console.error("page error:", e.message); process.exitCode = 1; });
  await page.goto(url);
  await page.evaluate(() => window.__ready);
  const cdp = await page.context().newCDPSession(page);
  return { page, cdp };
}

// Every piece of text the stage can show, for the language checks in src/checks/verify.py.
async function dumpText(page) {
  const text = await page.evaluate(() => {
    const out = [];
    const walk = document.createTreeWalker(document.getElementById("scenes"), NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) { const v = walk.currentNode.nodeValue.replace(/\s+/g, " ").trim(); if (v) out.push(v); }
    window.TL.scenes.forEach((s) => out.push(s.name));
    return out.join("\n");
  });
  writeFileSync(join(root, "build/onscreen-text.txt"), text + "\n");
}

async function grab(cdp) {
  const { data } = await cdp.send("Page.captureScreenshot", { format: "png", optimizeForSpeed: true, captureBeyondViewport: false });
  return Buffer.from(data, "base64");
}

async function stills(times) {
  const browser = await chromium.launch();
  const { page, cdp } = await openPage(browser);
  await dumpText(page);
  const out = join(root, "build/stills");
  mkdirSync(out, { recursive: true });
  for (const t of times) {
    await page.evaluate((t) => window.renderFrame(t), t);
    writeFileSync(join(out, `t_${t.toFixed(2).padStart(6, "0")}.png`), await grab(cdp));
  }
  await browser.close();
  console.log(`wrote ${times.length} stills to build/stills`);
}

async function full() {
  const fps = tl.fps, total = Math.round(tl.duration * fps);
  const workers = parseInt(opt("--workers", "3"), 10);
  const out = join(root, "build/video");
  mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  { const { page } = await openPage(browser); await dumpText(page); await page.close(); }
  const per = Math.ceil(total / workers);
  const started = Date.now();
  let done = 0;
  const jobs = [...Array(workers).keys()].map(async (w) => {
    const a = w * per, b = Math.min(total, a + per);
    const { page, cdp } = await openPage(browser);
    const seg = join(out, `seg_${w}.mkv`);
    const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-c:v", "png", "-i", "-",
      "-c:v", "libx264rgb", "-preset", "ultrafast", "-qp", "0", seg], { stdio: ["pipe", "inherit", "inherit"] });
    for (let f = a; f < b; f++) {
      await page.evaluate((t) => window.renderFrame(t), f / fps);
      const buf = await grab(cdp);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
      done++;
      if (w === 0 && f % 60 === 0) {
        const el = (Date.now() - started) / 1000;
        console.log(`frames ${done}/${total}  ${(done / el).toFixed(1)} fps  eta ${((total - done) / (done / el)).toFixed(0)} s`);
      }
    }
    ff.stdin.end();
    await new Promise((r) => ff.on("close", r));
    await page.close();
    return seg;
  });
  const segs = await Promise.all(jobs);
  await browser.close();
  writeFileSync(join(out, "segments.txt"), segs.map((s) => `file '${s}'`).join("\n") + "\n");
  await new Promise((res, rej) => {
    const p = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(out, "segments.txt"), "-c", "copy", join(out, "picture.mkv")], { stdio: "inherit" });
    p.on("close", (c) => (c === 0 ? res() : rej(new Error("concat failed"))));
  });
  console.log(`rendered ${total} frames in ${((Date.now() - started) / 1000).toFixed(0)} s -> build/video/picture.mkv`);
}

if (args.includes("--stills")) await stills(opt("--stills", "0").split(",").map(Number));
else await full();
