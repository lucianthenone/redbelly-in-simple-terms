// Prints build/pdf/submission.html to the submission PDF with Chromium.
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(join(root, "build/pdf/submission.html")).href, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);
await page.pdf({
  path: join(root, "submission/redbelly-in-simple-terms-submission.pdf"),
  format: "A4",
  printBackground: true,
  preferCSSPageSize: true,
  displayHeaderFooter: true,
  headerTemplate: "<span></span>",
  footerTemplate: `<div style="width:100%;padding:0 16mm;font:8px sans-serif;color:#596975;display:flex;justify-content:space-between">
    <span>Redbelly in Simple Terms</span><span class="pageNumber"></span></div>`,
});
await browser.close();
console.log("submission PDF written");
