/* Redbelly in Simple Terms: motion graphics stage.
 * Every frame is a pure function of time: renderFrame(t) sets the whole picture,
 * so frames can be rendered in any order, in parallel, and always match the audio.
 * Times come from build/timeline.js (window.TL), anchored on spoken words. */
(() => {
  const TL = window.TL;
  const C = TL.cues;
  const S = Object.fromEntries(TL.scenes.map((s) => [s.id, s]));
  const W = 1920, H = 1080;

  // ------------------------------------------------------------ maths
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, k) => a + (b - a) * k;
  const E = {
    lin: (x) => x,
    out: (x) => 1 - Math.pow(1 - x, 3),
    out4: (x) => 1 - Math.pow(1 - x, 4),
    inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
    expo: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
    back: (x) => { const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
  };
  const p = (t, t0, d, e = E.out) => e(clamp((t - t0) / Math.max(d, 1e-4)));
  const between = (t, a, b) => t >= a && t < b;

  // ------------------------------------------------------------ dom helpers
  function el(parent, cls = "", html = "", tag = "div") {
    const d = document.createElement(tag);
    if (cls) d.className = cls;
    if (html) d.innerHTML = html;
    parent.appendChild(d);
    return d;
  }
  function at(node, x, y, w, h) {
    node.classList.add("abs");
    node._x = x; node._y = y;
    node.style.left = x + "px"; node.style.top = y + "px";
    if (w) node.style.width = w + "px";
    if (h) node.style.height = h + "px";
    node.style.transform = "translate(-50%,-50%)";
    return node;
  }
  function icon(name, size, color, stroke = 1.75) {
    const svg = (window.ICONS[name] || "").replace('stroke-width="2"', `stroke-width="${stroke}"`);
    return `<span class="ico" style="width:${size}px;height:${size}px;color:${color}">${svg}</span>`;
  }
  function logo(kind, w) {
    return `<span class="ico" style="width:${w}px">${window.LOGOS[kind]}</span>`;
  }
  // Set transform and opacity in one call. dx/dy are offsets from the anchor.
  function tf(node, { x = 0, y = 0, s = 1, r = 0, o = 1, blur = 0, sx = null } = {}) {
    const sc = sx == null ? `scale(${s})` : `scale(${sx},${s})`;
    node.style.transform = `translate(-50%,-50%) translate(${x}px,${y}px) ${sc} rotate(${r}deg)`;
    node.style.opacity = clamp(o);
    node.style.filter = blur > 0.05 ? `blur(${blur}px)` : "none";
    node.style.visibility = o <= 0.001 ? "hidden" : "visible";
  }
  // Standard entrance (and optional exit) used by most elements.
  function show(node, t, t0, t1 = null, o = {}) {
    const k = p(t, t0, o.d ?? 0.55, o.ease ?? E.out4);
    const q = t1 == null ? 0 : p(t, t1, o.od ?? 0.4, E.inOut);
    tf(node, {
      x: (o.x ?? 0) + (o.dx ?? 0) * (1 - k) + (o.ox ?? 0) * q,
      y: (o.y ?? 0) + (o.dy ?? 28) * (1 - k) + (o.oy ?? -18) * q,
      s: lerp(o.fs ?? 0.97, 1, k) * lerp(1, o.os ?? 0.98, q) * (o.s ?? 1),
      o: k * (1 - q),
      blur: (o.blur ?? 6) * (1 - k) + 6 * q,
    });
    return k * (1 - q);
  }
  function statusHTML(kind, text) { return `<span class="status ${kind}"><i></i>${text}</span>`; }
  function svgNode(parent, cls = "full") {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("class", cls);
    s.setAttribute("viewBox", `0 0 ${W} ${H}`);
    parent.appendChild(s);
    return s;
  }
  function sv(parent, tag, attrs) {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    parent.appendChild(n);
    return n;
  }

  // ------------------------------------------------------------ background
  // A quiet field of nodes and links: the "Kinetic Consensus" texture.
  const bg = document.getElementById("bg");
  const bgNodes = [];
  {
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const defs = sv(bg, "defs", {});
    const g1 = sv(defs, "radialGradient", { id: "glow", cx: "50%", cy: "50%", r: "50%" });
    sv(g1, "stop", { offset: "0%", "stop-color": "#EF5350", "stop-opacity": "0.16" });
    sv(g1, "stop", { offset: "100%", "stop-color": "#EF5350", "stop-opacity": "0" });
    const g2 = sv(defs, "radialGradient", { id: "vig", cx: "50%", cy: "45%", r: "75%" });
    sv(g2, "stop", { offset: "55%", "stop-color": "#0c1317", "stop-opacity": "0" });
    sv(g2, "stop", { offset: "100%", "stop-color": "#070c0f", "stop-opacity": "0.9" });
    const dots = sv(bg, "g", { fill: "#1a262e" });
    for (let y = 36; y < H; y += 48) for (let x = 36; x < W; x += 48) sv(dots, "circle", { cx: x, cy: y, r: 1.6 });
    for (let i = 0; i < 34; i++) bgNodes.push({ x: rnd() * W, y: rnd() * H, a: rnd() * 6.28, sp: 0.15 + rnd() * 0.25, r: 6 + rnd() * 26 });
    bg._links = sv(bg, "g", { stroke: "#1f2d36", "stroke-width": 1.5 });
    bg._nodes = sv(bg, "g", { fill: "#24343f" });
    bg._glow = sv(bg, "ellipse", { cx: 1500, cy: 260, rx: 760, ry: 560, fill: "url(#glow)" });
    sv(bg, "rect", { x: 0, y: 0, width: W, height: H, fill: "url(#vig)" });
  }
  function renderBg(t) {
    const pts = bgNodes.map((n) => ({ x: n.x + Math.cos(n.a + t * n.sp) * n.r, y: n.y + Math.sin(n.a * 1.3 + t * n.sp) * n.r }));
    let links = "";
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
      const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
      if (dx * dx + dy * dy < 230 * 230) links += `<line x1="${pts[i].x.toFixed(1)}" y1="${pts[i].y.toFixed(1)}" x2="${pts[j].x.toFixed(1)}" y2="${pts[j].y.toFixed(1)}"/>`;
    }
    bg._links.innerHTML = links;
    bg._nodes.innerHTML = pts.map((q) => `<circle cx="${q.x.toFixed(1)}" cy="${q.y.toFixed(1)}" r="3"/>`).join("");
    // the glow drifts to a new corner for each chapter
    const spots = { hook: [1500, 260], problem: [420, 820], onestep: [960, 330], people: [1480, 760], rules: [420, 300], assets: [1500, 300], proof: [960, 260], close: [960, 470] };
    let cx = 1500, cy = 260;
    for (const sc of TL.scenes) {
      const k = p(t, sc.start - 0.2, 1.6, E.inOut);
      cx = lerp(cx, spots[sc.id][0], k); cy = lerp(cy, spots[sc.id][1], k);
    }
    bg._glow.setAttribute("cx", cx.toFixed(1));
    bg._glow.setAttribute("cy", cy.toFixed(1));
  }

  // ------------------------------------------------------------ chrome
  const prog = document.getElementById("progress");
  const progBars = TL.scenes.map(() => el(el(prog), "", "", "span"));
  const chromeN = document.querySelector("#chrome-label .n");
  const chromeName = document.getElementById("chrome-name");
  const chromeBox = document.getElementById("chrome-label");
  function renderChrome(t) {
    let idx = 0;
    TL.scenes.forEach((sc, i) => { if (t >= sc.start) idx = i; });
    TL.scenes.forEach((sc, i) => {
      progBars[i].style.width = (i < idx ? 100 : i > idx ? 0 : 100 * clamp((t - sc.start) / (sc.end - sc.start))) + "%";
    });
    chromeN.textContent = String(idx + 1).padStart(2, "0");
    chromeName.textContent = TL.scenes[idx].name;
    const sc = TL.scenes[idx];
    const k = p(t, sc.start, 0.5) * (1 - p(t, sc.end - 0.25, 0.25));
    const fade = t >= C.endcard - 0.3 ? 1 - p(t, C.endcard - 0.3, 0.5) : 1;
    chromeBox.style.opacity = (idx === 0 ? 1 : 0.25 + 0.75 * k) * fade;
    prog.style.opacity = fade;
  }

  // ------------------------------------------------------------ captions
  const capbox = document.getElementById("capbox");
  let capKey = null;
  function renderCaptions(t) {
    const c = TL.captions.find((c) => t >= c.start && t < c.end);
    if (!c) { capbox.parentElement.style.opacity = 0; capKey = null; return; }
    if (capKey !== c.start) {
      capbox.innerHTML = c.words.map((w) => `<span class="w">${w.text}</span>`).join(" ");
      capKey = c.start;
    }
    // highlight exactly one word: the one being spoken now
    const spans = capbox.querySelectorAll(".w");
    let cur = -1;
    c.words.forEach((w, i) => { if (t >= w.start - 0.04) cur = i; });
    if (cur >= 0 && t > c.words[cur].end + 0.3) cur = -1;
    spans.forEach((s, i) => s.classList.toggle("on", i === cur));
    const k = p(t, c.start, 0.12, E.lin) * (1 - p(t, c.end - 0.1, 0.1, E.lin));
    capbox.parentElement.style.opacity = k;
  }

  // ------------------------------------------------------------ scenes
  const scenesRoot = document.getElementById("scenes");
  const scenes = [];
  function scene(id, build) {
    const root = el(scenesRoot, "scene");
    const update = build(root, S[id]);
    scenes.push({ id, root, update, sc: S[id] });
  }

  // 1. THE ODD DELAY ---------------------------------------------------------
  scene("hook", (root, sc) => {
    const t0 = C["hook.send"], t1 = C["hook.arrive"], tf_ = C["hook.fund"];
    const head = at(el(root, "h-xl center nowrap", "Send a photo"), 960, 190);
    const phone = (x, place) => at(el(root, "card", `
        <div style="position:absolute;inset:18px 18px 64px;border-radius:12px;background:var(--lowest);border:2px solid var(--high)"></div>
        <div class="caps" style="position:absolute;left:0;right:0;bottom:20px;text-align:center">${place}</div>`), x, 560, 250, 400);
    const pl = phone(520, "Sydney"), pr = phone(1400, "London");
    const svg = svgNode(root);
    const arcD = "M 600 470 C 760 170, 1160 170, 1320 470";
    sv(svg, "path", { d: arcD, fill: "none", stroke: "#34444f", "stroke-width": 4, "stroke-dasharray": "2 14", "stroke-linecap": "round" });
    const trail = sv(svg, "path", { d: arcD, fill: "none", stroke: "#EF5350", "stroke-width": 5, "stroke-linecap": "round" });
    const L = trail.getTotalLength();
    trail.setAttribute("stroke-dasharray", `${L} ${L}`);
    const photoHTML = `<div style="width:100%;height:100%;border-radius:10px;background:linear-gradient(160deg,#2c4556,#1d3140);display:flex;align-items:center;justify-content:center">${icon("image", 64, "#ffb3ae")}</div>`;
    const photo = at(el(root, "", photoHTML), 600, 470, 150, 116);
    const recv = at(el(root, "", photoHTML), 1400, 520, 182, 140);
    const delivered = at(el(root, "", statusHTML("ok", "Delivered")), 1400, 810);
    const stat = at(el(root, "h-lg nowrap accent", "1 second"), 960, 330);

    // part two: buying into a fund
    const head2 = at(el(root, "h-xl center nowrap", "Buy into a fund"), 960, 190);
    const you = at(el(root, "card", `<div style="display:flex;align-items:center;gap:22px;padding:30px 34px">${icon("banknote", 64, "#ffb3ae")}<div><div class="h-sm">You pay</div><div class="mono" style="margin-top:6px">Payment</div></div></div>`), 470, 580, 400, 150);
    const fund = at(el(root, "card", `<div style="display:flex;align-items:center;gap:22px;padding:30px 34px">${icon("chart-pie", 64, "#ffb3ae")}<div><div class="h-sm">You own</div><div class="mono" style="margin-top:6px">Fund units</div></div></div>`), 1450, 580, 400, 150);
    const svg2 = svgNode(root);
    sv(svg2, "line", { x1: 690, y1: 580, x2: 1230, y2: 580, stroke: "#34444f", "stroke-width": 4, "stroke-dasharray": "2 14", "stroke-linecap": "round" });
    const crawl = sv(svg2, "line", { x1: 690, y1: 580, x2: 690, y2: 580, stroke: "#FCD34D", "stroke-width": 5, "stroke-linecap": "round" });
    const cal = at(el(root, "ring", icon("calendar", 46, "#FCD34D")), 690, 580, 92, 92);
    cal.style.background = "var(--lowest)"; cal.style.border = "2px solid #FCD34D";
    const days = at(el(root, "h-lg nowrap warn", ""), 960, 340);
    const pending = at(el(root, "", statusHTML("warn", "Pending")), 960, 760);

    return (t) => {
      // photo part
      const outA = tf_ - 0.05;
      show(head, t, sc.start + 0.05, outA, { d: 0.6 });
      show(pl, t, sc.start + 0.1, outA, { dx: -40, dy: 0 });
      show(pr, t, sc.start + 0.2, outA, { dx: 40, dy: 0 });
      const fly = p(t, t0, Math.max(0.6, t1 - t0), E.inOut);
      trail.setAttribute("stroke-dashoffset", L * (1 - fly));
      const vis = (t > sc.start + 0.15 ? 1 : 0) * (1 - p(t, outA, 0.35));
      svg.style.opacity = vis * p(t, sc.start + 0.2, 0.5);
      const pt = trail.getPointAtLength(L * fly);
      const onFlight = between(t, t0 - 0.3, t1 + 0.05);
      tf(photo, { x: pt.x - 600, y: pt.y - 470, s: 1 + 0.18 * Math.sin(Math.PI * fly), r: -8 * Math.sin(Math.PI * fly), o: onFlight ? p(t, t0 - 0.3, 0.3) : 0 });
      show(recv, t, t1, outA, { fs: 0.8, dy: 0, d: 0.45, ease: E.back });
      show(delivered, t, t1 + 0.1, outA, { dy: 16 });
      show(stat, t, t1, outA, { fs: 0.85, ease: E.back });
      // fund part
      show(head2, t, tf_, null, { d: 0.6 });
      show(you, t, tf_ + 0.1, null, { dx: -40, dy: 0 });
      show(fund, t, tf_ + 0.2, null, { dx: 40, dy: 0 });
      const crawlK = clamp((t - (tf_ + 0.3)) / 14) * 0.5;        // it crawls and never arrives
      const cx = 690 + 540 * crawlK;
      crawl.setAttribute("x2", cx);
      svg2.style.opacity = p(t, tf_ + 0.2, 0.5);
      show(cal, t, tf_ + 0.3, null, { x: cx - 690, dy: 0, fs: 0.6, ease: E.back });
      let txt = "";
      if (t >= C["hook.days"]) txt = "1 business day";
      if (t >= C["hook.days"] + 0.42) txt = "2 business days";
      days.textContent = txt;
      show(days, t, C["hook.days"], null, { fs: 0.9, dy: 12 });
      if (between(t, C["hook.days"] + 0.42, C["hook.days"] + 0.7)) tf(days, { s: 1 + 0.06 * Math.sin(Math.PI * (t - C["hook.days"] - 0.42) / 0.28) });
      const pk = show(pending, t, C["hook.settle"] - 0.3, null, { dy: 16 });
      if (pk > 0.99) pending.style.opacity = 0.7 + 0.3 * Math.cos((t - C["hook.settle"]) * 5);
    };
  });

  // 2. TWO PLACES, MANY COPIES ----------------------------------------------
  scene("problem", (root, sc) => {
    const panel = (x, ic, title, label, st) => at(el(root, "card", `
      <div style="padding:30px 36px">
        <div style="display:flex;align-items:center;gap:20px">${icon(ic, 58, "#ffb3ae")}<div class="h-md">${title}</div></div>
        <div style="margin-top:28px;display:flex;align-items:center;justify-content:space-between;border-top:2px solid var(--high);padding-top:22px">
          <span class="mono">${label}</span>${st}</div></div>`), x, 380, 560, 236);
    const money = panel(560, "landmark", "The money", "Payment", statusHTML("ok", "Sent"));
    const rec = panel(1360, "file-text", "Who owns what", "Owner", statusHTML("warn", "Not updated"));
    const gap = at(el(root, "mono center", "Separate<br>systems"), 960, 380);
    const firms = ["Bank", "Registry", "Fund manager", "Trustee"];
    const xs = [390, 770, 1150, 1530];
    const copies = firms.map((f, i) => at(el(root, "card", `
      <div style="display:flex;align-items:center;gap:18px;padding:22px 26px">${icon("file-text", 44, "#c2ced6")}
      <div><div style="font-weight:600;font-size:28px">${f}</div><div class="mono" style="font-size:19px;margin-top:4px">Own copy</div></div></div>`), xs[i], 700, 330, 112));
    const marks = xs.map((x, i) => at(el(root, "ring", i === 2 ? icon("x", 30, "#0c1317", 3) : icon("check", 30, "#0c1317", 3)), x + 150, 650, 50, 50));
    marks.forEach((m, i) => { m.style.background = i === 2 ? "var(--warn)" : "var(--ok)"; });
    const glass = at(el(root, "ring", icon("search", 52, "#f1f5f8")), 390, 700, 110, 110);
    glass.style.background = "rgba(29,49,64,0.92)"; glass.style.border = "2px solid #8fa1ad";
    const recon = at(el(root, "", statusHTML("warn", "Checking they match")), 960, 560);

    return (t) => {
      show(money, t, sc.start + 0.1, null, { dx: -50, dy: 0 });
      show(rec, t, sc.start + 0.25, null, { dx: 50, dy: 0 });
      show(gap, t, sc.start + 0.5);
      copies.forEach((c, i) => show(c, t, C["problem.copies"] + i * 0.14, null, { dy: 40, fs: 0.9, ease: E.back }));
      const ck = C["problem.check"];
      const g = p(t, ck - 0.1, 1.15, E.inOut);
      const gx = lerp(390, 1530, g);
      tf(glass, { x: gx - 390, y: -8 * Math.sin(g * Math.PI * 6), o: p(t, ck - 0.2, 0.25) * (1 - p(t, ck + 1.3, 0.3)), s: 1 });
      marks.forEach((m, i) => {
        const when = ck - 0.1 + (i / 3) * 1.15 + 0.1;
        show(m, t, when, null, { fs: 0.3, dy: 0, d: 0.35, ease: E.back });
      });
      const rk = show(recon, t, ck + 0.2, null, { dy: 14 });
      if (rk > 0.99) recon.style.opacity = 0.75 + 0.25 * Math.cos((t - ck) * 6);
    };
  });

  // 3. ONE STEP -------------------------------------------------------------
  scene("onestep", (root, sc) => {
    const glow = at(el(root, ""), 960, 330, 900, 420);
    glow.style.background = "radial-gradient(closest-side, rgba(239,83,80,0.28), rgba(239,83,80,0))";
    const lg = at(el(root, "", logo("horizontal", 820)), 960, 330, 820, 228);
    const chipA = at(el(root, "chip", `${icon("globe", 28, "#ffb3ae")}Public network`), 790, 510);
    const chipB = at(el(root, "chip", `${icon("map-pin", 28, "#ffb3ae")}Built in Australia`), 1140, 510);
    const mini = (ic, txt) => `<div style="display:flex;align-items:center;gap:16px;padding:20px 28px">${icon(ic, 46, "#ffb3ae")}<span class="h-sm">${txt}</span></div>`;
    const mA = at(el(root, "card", mini("landmark", "The money")), 560, 720, 380, 100);
    const mB = at(el(root, "card", mini("file-text", "Who owns what")), 1360, 720, 420, 100);
    const merged = at(el(root, "card steel", `<div style="display:flex;align-items:center;justify-content:center;gap:16px;padding:20px 28px">${icon("landmark", 46, "#ffb3ae")}<span class="h-sm">+</span>${icon("file-text", 46, "#ffb3ae")}<span class="h-sm" style="margin-left:8px">Together, in one place</span></div>`), 960, 720, 640, 104);
    merged.style.borderColor = "#EF5350";

    // swap stage
    const party = (x, who, has) => at(el(root, "card", `
      <div style="padding:26px 30px;text-align:center">${icon("user", 60, "#c2ced6")}
      <div class="h-sm" style="margin-top:10px">${who}</div><div class="mono has" style="margin-top:8px">${has}</div></div>`), x, 560, 300, 230);
    const buyer = party(380, "Buyer", "Has the money");
    const seller = party(1540, "Seller", "Has the asset");
    const svg = svgNode(root);
    const track = sv(svg, "line", { x1: 620, y1: 560, x2: 1300, y2: 560, stroke: "#34444f", "stroke-width": 4, "stroke-dasharray": "2 14", "stroke-linecap": "round" });
    const ring = at(el(root, "ring"), 960, 560, 210, 210);
    const ringIcons = { idle: icon("arrow-left-right", 72, "#8fa1ad", 1.6), ok: icon("check", 84, "#86EFAC", 2.4), bad: icon("x", 84, "#EF5350", 2.4) };
    const setRing = (k) => { if (ring._k !== k) { ring._k = k; ring.innerHTML = ringIcons[k]; ring.style.borderColor = k === "ok" ? "#86EFAC" : k === "bad" ? "#EF5350" : "#34444f"; } };
    ring.style.border = "4px solid #34444f"; ring.style.background = "rgba(7,12,15,0.6)";
    const ringLbl = at(el(root, "mono center nowrap", "One step"), 960, 705);
    const token = (ic, col) => { const n = at(el(root, "ring", icon(ic, 52, col)), 0, 0, 108, 108); n.style.background = "#1d3140"; n.style.border = `3px solid ${col}`; return n; };
    const coin = token("banknote", "#ffb3ae");
    const deed = token("file-text", "#c2ced6");
    const failX = at(el(root, "ring", icon("x", 40, "#0c1317", 3.2)), 0, 0, 62, 62);
    failX.style.background = "var(--brand)";
    const okTxt = at(el(root, "", statusHTML("ok", "Step 1 of 1")), 960, 800);
    const failTxt = at(el(root, "", statusHTML("bad", "Nothing moves")), 960, 800);
    const finalTxt = at(el(root, "", statusHTML("ok", "Final")), 960, 800);
    const stamp = at(el(root, "", `<div style="display:flex;align-items:center;gap:14px;padding:14px 26px;border:4px solid var(--ok);border-radius:8px;color:var(--ok);font-family:var(--mono);font-weight:600;font-size:44px;letter-spacing:.08em;background:rgba(7,12,15,.85)">${icon("lock", 44, "#86EFAC", 2.2)}FINAL</div>`), 960, 560);
    const hasB = buyer.querySelector(".has"), hasS = seller.querySelector(".has");

    return (t) => {
      const tl = C["onestep.logo"], tsw = C["onestep.swap"];
      // logo reveal, then it moves up out of the way
      const up = p(t, tsw - 0.5, 0.7, E.inOut);
      const rev = p(t, tl, 0.9, E.out4);
      lg.style.clipPath = `inset(0 ${100 - 100 * rev}% 0 0)`;
      tf(lg, { y: lerp(0, -205, up), s: lerp(1.06, 1, rev) * lerp(1, 0.5, up), o: Math.min(1, rev * 3) });
      tf(glow, { y: lerp(0, -205, up), s: lerp(0.6, 1, p(t, tl, 1.2)) * lerp(1, 0.5, up), o: p(t, tl, 0.6) * (0.75 + 0.25 * Math.sin(t * 2)) * (1 - 0.6 * up) });
      show(chipA, t, C["onestep.public"], tsw - 0.5, { dy: 18 });
      show(chipB, t, C["onestep.australia"], tsw - 0.5, { dy: 18 });
      const tg = C["onestep.together"];
      const mk = p(t, tg, 0.6, E.inOut);
      const out = 1 - p(t, tsw - 0.5, 0.35);
      tf(mA, { x: lerp(0, 400, mk), o: p(t, tl + 0.4, 0.5) * (1 - p(t, tg + 0.35, 0.2)), y: 24 * (1 - p(t, tl + 0.4, 0.5)) });
      tf(mB, { x: lerp(0, -400, mk), o: p(t, tl + 0.5, 0.5) * (1 - p(t, tg + 0.35, 0.2)), y: 24 * (1 - p(t, tl + 0.5, 0.5)) });
      tf(merged, { s: lerp(0.85, 1, p(t, tg + 0.35, 0.5, E.back)), o: p(t, tg + 0.35, 0.3) * out });

      // the swap
      const vis = p(t, tsw - 0.35, 0.5);
      show(buyer, t, tsw - 0.4, null, { dx: -40, dy: 0 });
      show(seller, t, tsw - 0.3, null, { dx: 40, dy: 0 });
      svg.style.opacity = vis;
      tf(ring, { o: vis, s: lerp(0.8, 1, vis) });
            tf(ringLbl, { o: vis });

      const tStep = C["onestep.step"] + 0.15;
      const tFail = C["onestep.fail"], tNo = C["onestep.nothing"], tFin = C["onestep.final"];
      const reset = tFail - 0.3;
      let k, cx, dxx, fx = 0, fo = 0;
      let doneA = t >= tStep && t < reset, failed = false, finalDone = t >= tFin;
      if (t < reset) {
        k = p(t, tsw, tStep - tsw, E.inOut);
        cx = lerp(620, 1300, k); dxx = lerp(1300, 620, k);
        tf(coin, { x: cx, y: 560 - 90 * Math.sin(Math.PI * k), o: vis, s: 1 }); coin.style.left = "0px"; coin.style.top = "0px";
        tf(deed, { x: dxx, y: 560 + 90 * Math.sin(Math.PI * k), o: vis, s: 1 }); deed.style.left = "0px"; deed.style.top = "0px";
        setRing(doneA ? "ok" : "idle");
      } else if (t < tFin - 0.05) {
        // a failed attempt: the money starts, the asset side fails, everything returns
        const back = p(t, tNo, 0.55, E.inOut);
        const go = p(t, tFail, 0.45, E.out) * (1 - back);
        const fadeIn = p(t, reset, 0.25);
        tf(coin, { x: lerp(620, 800, go), y: 560 - 40 * Math.sin(Math.PI * go * 0.5), o: fadeIn });
        tf(deed, { x: 1300, y: 560, o: fadeIn });
        failed = t >= tFail + 0.2;
        fo = p(t, tFail + 0.2, 0.25, E.back) * (1 - p(t, tFin - 0.35, 0.25));
        tf(failX, { x: 1340, y: 515, o: fo, s: lerp(0.4, 1, fo) });
        setRing(failed ? "bad" : "idle");
      } else {
        k = p(t, tFin - 0.05, 0.55, E.inOut);
        tf(coin, { x: lerp(620, 1300, k), y: 560 - 90 * Math.sin(Math.PI * k), o: 1 - 0.0 * k });
        tf(deed, { x: lerp(1300, 620, k), y: 560 + 90 * Math.sin(Math.PI * k), o: 1 });
        setRing(k > 0.98 ? "ok" : "idle");
      }
      if (t >= tFail - 0.3) tf(failX, { x: 1340, y: 515, o: fo, s: lerp(0.4, 1, fo) }); else tf(failX, { o: 0 });
      hasB.textContent = (doneA || t >= tFin + 0.4) ? "Owns the asset" : "Has the money";
      hasS.textContent = (doneA || t >= tFin + 0.4) ? "Has the money" : "Has the asset";
      tf(okTxt, { o: doneA ? p(t, tStep, 0.25) * (1 - p(t, reset - 0.2, 0.2)) : 0, y: 0 });
      tf(failTxt, { o: failed ? p(t, tFail + 0.2, 0.25) * (1 - p(t, tFin - 0.3, 0.2)) : 0 });
      tf(finalTxt, { o: finalDone ? p(t, tFin + 0.45, 0.3) : 0 });
      const sk = p(t, tFin + 0.45, 0.4, E.back);
      tf(stamp, { o: t >= tFin + 0.45 ? p(t, tFin + 0.45, 0.15) : 0, s: lerp(1.6, 1, sk), r: lerp(-14, -5, sk) });
    };
  });

  // 4. VERIFIED PEOPLE --------------------------------------------------------
  scene("people", (root, sc) => {
    const head = at(el(root, "h-xl center nowrap", "Not a free-for-all"), 960, 190);
    const cols = 6, people = [];
    for (let r = 0; r < 2; r++) for (let c = 0; c < cols; c++) {
      const n = at(el(root, "ring", icon("user", 56, "#8fa1ad")), 560 + c * 160, 400 + r * 170, 124, 124);
      n.style.background = "var(--container)"; n.style.border = "3px solid var(--ov)";
      const b = el(n, "ring", icon("check", 22, "#0c1317", 3.4));
      Object.assign(b.style, { position: "absolute", right: "-4px", bottom: "-4px", width: "42px", height: "42px", background: "var(--ok)", opacity: 0 });
      people.push({ n, b, i: r * cols + c });
    }
    const idc = at(el(root, "card steel", `
      <div style="display:flex;align-items:center;justify-content:space-between;padding:26px 32px;border-bottom:2px solid #2c4556">
        <div style="display:flex;align-items:center;gap:18px">${icon("id-card", 54, "#ffb3ae")}<span class="h-sm">ID check</span></div>
        ${statusHTML("ok", "Verified")}</div>
      <div style="padding:22px 32px 26px">
        ${["Name", "Date of birth", "Address"].map((f) => `
        <div style="display:flex;align-items:center;justify-content:space-between;height:62px">
          <span class="mono" style="font-size:21px">${f}</span>
          <span class="field" style="position:relative;display:inline-block;width:300px;height:30px">
            <span class="bar" style="position:absolute;inset:0;border-radius:6px;background:#3a5466"></span>
            <span class="hid" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:flex-end;gap:10px;opacity:0">
              <span class="mono" style="font-size:20px;color:var(--on2)">Protected</span>${icon("lock", 26, "#86EFAC", 2.2)}</span>
          </span></div>`).join("")}
      </div>`), 960, 540, 700);
    const bars = idc.querySelectorAll(".bar"), hids = idc.querySelectorAll(".hid");
    const note = at(el(root, "", statusHTML("ok", "Identity proven, details kept private")), 960, 800);

    return (t) => {
      const tc = C["people.crowd"], tv = C["people.verify"], ti = C["people.id"], tp = C["people.private"];
      show(head, t, sc.start + 0.1, ti, { d: 0.6, oy: -30 });
      people.forEach(({ n, b, i }) => {
        const enter = p(t, sc.start + 0.3 + i * 0.04, 0.45, E.back);
        const vk = p(t, tv + i * 0.06, 0.3);
        const dim = p(t, ti - 0.1, 0.5, E.inOut);
        tf(n, { o: enter * lerp(1, 0.18, dim), s: lerp(0.6, 1, enter) * lerp(1, 0.92, dim), blur: 3 * dim });
        n.style.borderColor = vk > 0.5 ? "#86EFAC" : "#34444f";
        n.querySelector(".ico").style.color = vk > 0.5 ? "#f1f5f8" : "#8fa1ad";
        b.style.opacity = vk; b.style.transform = `scale(${lerp(0.4, 1, vk)})`;
      });
      show(idc, t, ti - 0.1, null, { dy: 40, fs: 0.92 });
      const hk = p(t, tp - 0.05, 0.4);
      bars.forEach((b, i) => { const k = p(t, tp - 0.05 + i * 0.12, 0.35); b.style.opacity = 1 - 0.85 * k; b.style.filter = `blur(${6 * k}px)`; });
      hids.forEach((h, i) => { h.style.opacity = p(t, tp + 0.05 + i * 0.12, 0.35); });
      show(note, t, tp + 0.35, null, { dy: 14 });
      void hk;
    };
  });

  // 5. RULES BUILT IN ---------------------------------------------------------
  scene("rules", (root, sc) => {
    const rules = ["Identity verified", "Eligible for this product", "Within limits"];
    const card = at(el(root, "card", `
      <div style="display:flex;align-items:center;gap:18px;padding:28px 34px;border-bottom:2px solid var(--high)">
        ${icon("book-open", 54, "#ffb3ae")}<span class="h-md">Product rules</span></div>
      <div style="padding:14px 34px 22px">${rules.map((r) => `
        <div style="display:flex;align-items:center;gap:22px;height:84px;border-bottom:2px solid var(--container)">
          <span class="ring mark" style="width:46px;height:46px;border:3px solid var(--ov);flex:none"></span>
          <span style="font-weight:500;font-size:31px">${r}</span></div>`).join("")}</div>`), 640, 500, 680, 420);
    const marks = [...card.querySelectorAll(".mark")];
    const req = (who) => at(el(root, "card", `
      <div style="display:flex;align-items:center;gap:20px;padding:24px 28px">${icon("user", 50, "#c2ced6")}
      <div><div class="h-sm">${who}</div><div class="mono" style="margin-top:6px">Buy request</div></div></div>
      <div class="st" style="padding:0 28px 24px"></div>`), 1420, 0, 480, 190);
    const a = req("Buyer A"), b = req("Buyer B");
    a._y = 390; b._y = 620; a.style.top = "390px"; b.style.top = "620px";
    const svg = svgNode(root);
    const la = sv(svg, "line", { x1: 985, y1: 390, x2: 1175, y2: 390, stroke: "#34444f", "stroke-width": 4, "stroke-dasharray": "2 12", "stroke-linecap": "round" });
    const lb = sv(svg, "line", { x1: 985, y1: 620, x2: 1175, y2: 620, stroke: "#34444f", "stroke-width": 4, "stroke-dasharray": "2 12", "stroke-linecap": "round" });
    a.querySelector(".st").innerHTML = statusHTML("idle", "Checking");
    b.querySelector(".st").innerHTML = statusHTML("idle", "Checking");
    const setMark = (m, kind) => {
      if (kind === m._k) return;
      m._k = kind;
      m.style.borderColor = kind === "ok" ? "#86EFAC" : kind === "bad" ? "#EF5350" : "#34444f";
      m.style.background = kind === "ok" ? "#86EFAC" : kind === "bad" ? "#EF5350" : "transparent";
      m.innerHTML = kind === "ok" ? icon("check", 26, "#0c1317", 3.4) : kind === "bad" ? icon("x", 26, "#0c1317", 3.4) : "";
    };
    return (t) => {
      const tl = C["rules.list"], tt = C["rules.trade"], tc = C["rules.check"], tfail = C["rules.fail"], tb = C["rules.blocked"];
      show(card, t, Math.min(tl - 0.3, sc.start + 0.15), null, { dx: -40, dy: 0 });
      show(a, t, tt - 0.1, null, { dx: 50, dy: 0 });
      la.style.opacity = p(t, tt, 0.4);
      const phaseB = t >= tfail - 0.15;
      marks.forEach((m, i) => {
        if (!phaseB) setMark(m, t >= tc + i * 0.32 ? "ok" : "none");
        else setMark(m, i === 0 && t >= tfail + 0.0 ? "ok" : i === 1 && t >= tfail + 0.3 ? "bad" : "none");
        const pop = phaseB ? p(t, tfail + (i === 0 ? 0 : 0.3), 0.3, E.back) : p(t, tc + i * 0.32, 0.3, E.back);
        m.style.transform = `scale(${m._k === "none" ? 1 : lerp(0.6, 1, pop)})`;
      });
      const approved = t >= tc + 0.9;
      const ast = approved ? "ok:Approved" : "idle:Checking";
      if (a._st !== ast) { a._st = ast; const [k, l] = ast.split(":"); a.querySelector(".st").innerHTML = statusHTML(k, l); }
      a.style.borderColor = approved ? "#86EFAC" : "var(--edge)";
      if (phaseB) { a.style.opacity = String(lerp(1, 0.45, p(t, tfail - 0.15, 0.4))); }
      show(b, t, tfail - 0.25, null, { dx: 50, dy: 0 });
      lb.style.opacity = p(t, tfail - 0.1, 0.4);
      const blocked = t >= tfail + 0.35;
      const bst = blocked ? "bad:Blocked" : "idle:Checking";
      if (b._st !== bst) { b._st = bst; const [k, l] = bst.split(":"); b.querySelector(".st").innerHTML = statusHTML(k, l); }
      b.style.borderColor = blocked ? "#EF5350" : "var(--edge)";
      if (blocked) {
        const sh = p(t, tfail + 0.35, 0.5, E.lin);
        const k2 = p(t, tfail - 0.25, 0.55, E.out4);
        tf(b, { x: Math.sin(sh * Math.PI * 6) * 14 * (1 - sh), o: k2 * lerp(1, 0.55, p(t, tb + 0.6, 0.6)) });
      }
    };
  });

  // 6. WHAT IT IS FOR ---------------------------------------------------------
  scene("assets", (root, sc) => {
    const items = [["house", "Property", "assets.property"], ["hand-coins", "Loans", "assets.loans"], ["scroll-text", "Bonds", "assets.bonds"], ["chart-pie", "Investment funds", "assets.funds"]];
    const xs = [420, 780, 1140, 1500];
    const tiles = items.map(([ic, name, cue], i) => {
      const n = at(el(root, "", `
        <div class="front card" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;backface-visibility:hidden">
          ${icon(ic, 84, "#c2ced6", 1.5)}<div class="h-sm center">${name}</div></div>
        <div class="back card steel" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;backface-visibility:hidden;transform:rotateY(180deg);border-top:5px solid #EF5350">
          ${icon(ic, 72, "#ffb3ae", 1.6)}<div class="h-sm center">${name}</div><div class="mono" style="font-size:19px">Digital version</div>
          <div class="st" style="height:52px;display:flex;align-items:center"></div></div>`), xs[i], 460, 330, 340);
      n.style.perspective = "1200px";
      const inner = document.createElement("div");
      Object.assign(inner.style, { position: "absolute", inset: 0, transformStyle: "preserve-3d" });
      while (n.firstChild) inner.appendChild(n.firstChild);
      n.appendChild(inner);
      n._inner = inner; n._cue = cue;
      n.querySelector(".st").innerHTML = statusHTML("ok", "Settled");
      return n;
    });
    const ahead = at(el(root, "h-xl center nowrap", "Things of real value"), 960, 190);
    const dict = at(el(root, "card", `
      <div style="padding:34px 46px">
        <div style="display:flex;align-items:baseline;gap:22px"><span class="h-lg">tokenisation</span><span class="body" style="font-style:normal;color:var(--outline)">noun</span></div>
        <div class="body" style="margin-top:14px;font-size:32px;color:var(--on)">Issuing and trading a real asset as a digital version.</div>
      </div>`), 960, 700, 1040, 210);
    dict.style.borderLeft = "6px solid #EF5350";
    return (t) => {
      const td = C["assets.digital"], ts = C["assets.settle"], tw = C["assets.word"];
      const up = p(t, tw - 0.35, 0.6, E.inOut);
      show(ahead, t, sc.start + 0.1, tw - 0.45, { d: 0.6 });
      tiles.forEach((n, i) => {
        const k = p(t, C[n._cue] - 0.12, 0.5, E.back);
        tf(n, { o: p(t, C[n._cue] - 0.12, 0.25), s: lerp(0.7, 1, k) * lerp(1, 0.72, up), y: lerp(0, -200, up) });
        const flip = p(t, td + i * 0.08, 0.7, E.inOut);
        n._inner.style.transform = `rotateY(${180 * flip}deg)`;
        const st = n.querySelector(".st");
        st.style.opacity = p(t, ts + i * 0.08, 0.25);
        st.style.transform = `scale(${lerp(0.7, 1, p(t, ts + i * 0.08, 0.35, E.back))})`;
      });
      show(dict, t, tw - 0.1, null, { dy: 40 });
    };
  });

  // 7. WHERE IT COMES FROM ----------------------------------------------------
  scene("proof", (root, sc) => {
    const org = (ic, title, sub) => `<div style="display:flex;align-items:center;gap:22px;padding:28px 34px">${icon(ic, 60, "#ffb3ae")}
      <div><div class="h-sm">${title}</div><div class="mono" style="margin-top:8px;font-size:19px">${sub}</div></div></div>`;
    const uni = at(el(root, "card", org("graduation-cap", "University of Sydney", "Research")), 540, 330, 620, 150);
    const csiro = at(el(root, "card", org("microscope", "CSIRO", "Australia's national science agency")), 1380, 330, 620, 150);
    const svg = svgNode(root);
    const l1 = sv(svg, "path", { d: "M 540 405 C 540 520, 800 560, 900 590", fill: "none", stroke: "#EF5350", "stroke-width": 4, "stroke-linecap": "round" });
    const l2 = sv(svg, "path", { d: "M 1380 405 C 1380 520, 1120 560, 1020 590", fill: "none", stroke: "#EF5350", "stroke-width": 4, "stroke-linecap": "round" });
    [l1, l2].forEach((l) => { const L = l.getTotalLength(); l._L = L; l.setAttribute("stroke-dasharray", `${L} ${L}`); });
    const iso = at(el(root, "", `<div style="display:flex;flex-direction:column;align-items:center;gap:14px">${logo("isotypeWhite", 120)}<span class="h-sm">Redbelly</span></div>`), 960, 670);

    const rba = at(el(root, "card", `<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 34px">
      <div style="display:flex;align-items:center;gap:22px">${icon("landmark", 60, "#ffb3ae")}<span class="h-md">Reserve Bank of Australia</span></div>
      <span class="acacia" style="opacity:0">${statusHTML("idle", "Project Acacia")}</span></div>`), 960, 215, 1080, 128);
    const coin = at(el(root, "", `<div style="display:flex;align-items:center;gap:18px">
      <span class="ring" style="width:84px;height:84px;background:#1d3140;border:3px solid #ffb3ae">${icon("coins", 44, "#ffb3ae")}</span>
      <span class="body" style="color:var(--on);font-size:30px">Pilot digital form of central bank money</span></div>`), 960, 375);
    const plat = (x, html, hi) => { const n = at(el(root, hi ? "card steel nowrap" : "card nowrap", `<div style="height:100%;display:flex;align-items:center;justify-content:center;gap:16px;padding:0 22px">${html}</div>`), x, 620, 430, 130); return n; };
    const p1 = plat(480, `<span class="h-sm muted">AP+ HashSphere</span>`);
    const p2 = plat(960, `${logo("isotypeWhite", 46)}<span class="h-sm">Redbelly Network</span>`, true);
    const p3 = plat(1440, `<span class="h-sm muted">Canvas Connect</span>`);
    const svg2 = svgNode(root);
    const paths = [[960, 420, 480, 555], [960, 420, 960, 555], [960, 420, 1440, 555]].map(([x1, y1, x2, y2]) => {
      const d = `M ${x1} ${y1} C ${x1} ${y1 + 70}, ${x2} ${y2 - 70}, ${x2} ${y2}`;
      const base = sv(svg2, "path", { d, fill: "none", stroke: "#34444f", "stroke-width": 3, "stroke-dasharray": "2 12", "stroke-linecap": "round" });
      const live = sv(svg2, "path", { d, fill: "none", stroke: "#ffb3ae", "stroke-width": 4, "stroke-linecap": "round" });
      const L = live.getTotalLength(); live.setAttribute("stroke-dasharray", `${L} ${L}`); live.setAttribute("stroke-dashoffset", L);
      return { base, live, L };
    });
    const one = at(el(root, "", statusHTML("ok", "1 of 3 platforms")), 960, 750);
    const src = at(el(root, "mono center nowrap", "Source: RBA and DFCRC, Project Acacia final report, May 2026"), 960, 830);
    src.style.fontSize = "20px";

    return (t) => {
      const tu = C["proof.uni"], tcs = C["proof.csiro"], tr = C["proof.rba"];
      const out = tr - 0.45;
      show(uni, t, tu - 0.25, out, { dx: -40, dy: 0 });
      show(csiro, t, tcs - 0.25, out, { dx: 40, dy: 0 });
      const lk = p(t, tcs + 0.1, 0.8, E.inOut) * (1 - p(t, out, 0.35));
      [l1, l2].forEach((l) => { l.setAttribute("stroke-dashoffset", l._L * (1 - p(t, tcs + 0.1, 0.8, E.inOut))); });
      svg.style.opacity = lk > 0 ? 1 - p(t, out, 0.35) : 0;
      show(iso, t, sc.start + 0.15, out, { fs: 0.8, ease: E.back });

      show(rba, t, tr - 0.1, null, { dy: -30 });
      rba.querySelector(".acacia").style.opacity = p(t, C["proof.acacia"], 0.35);
      show(coin, t, C["proof.money"] - 0.2, null, { dy: 20 });
      const ta = C["proof.acacia"];
      show(p1, t, ta + 0.0, null, { dy: 30 });
      show(p2, t, ta + 0.12, null, { dy: 30 });
      show(p3, t, ta + 0.24, null, { dy: 30 });
      svg2.style.opacity = p(t, ta, 0.4);
      const hi = p(t, C["proof.redbelly"], 0.4);
      p2.style.borderColor = hi > 0.5 ? "#EF5350" : "#2c4556";
      p2.style.boxShadow = `0 0 0 ${6 * hi}px rgba(239,83,80,${0.18 * hi})`;
      const tc = C["proof.carried"];
      paths.forEach((q, i) => q.live.setAttribute("stroke-dashoffset", q.L * (1 - p(t, tc - 0.1 + i * 0.08, 0.7, E.inOut))));
      show(one, t, C["proof.three"] - 0.1, null, { dy: 16, fs: 0.8, ease: E.back });
      show(src, t, C["proof.three"] + 0.3, null, { dy: 8 });
    };
  });

  // 8. THE THREE IDEAS --------------------------------------------------------
  scene("close", (root, sc) => {
    const pill = (x, ic, txt) => at(el(root, "card", `<div style="height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px">
      <span class="ring" style="width:120px;height:120px;background:#1d3140;border:3px solid #EF5350">${icon(ic, 60, "#f1f5f8")}</span>
      <span class="h-md center">${txt}</span></div>`), x, 500, 460, 330);
    const a = pill(450, "user-check", "Verified people");
    const b = pill(960, "list-checks", "Rules built in");
    const c = pill(1470, "arrow-left-right", "Done in one step");
    const glow = at(el(root, ""), 960, 470, 1100, 520);
    glow.style.background = "radial-gradient(closest-side, rgba(239,83,80,0.26), rgba(239,83,80,0))";
    const lg = at(el(root, "", logo("horizontal", 980)), 960, 470, 980, 272);
    const url = at(el(root, "nowrap", `<span style="font-family:var(--mono);font-weight:500;font-size:40px;letter-spacing:.02em;color:var(--on)">redbelly.network</span>`), 960, 690);
    const d = new Date(TL.last_verified + "T00:00:00Z");
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const ver = at(el(root, "mono center nowrap", `Facts last verified ${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}`), 960, 770);
    ver.style.fontSize = "20px";
    return (t) => {
      const tn = C["close.name"], te = C.endcard;
      show(a, t, C["close.p1"], tn, { dy: 40, fs: 0.85, ease: E.back, oy: 40 });
      show(b, t, C["close.p2"], tn + 0.05, { dy: 40, fs: 0.85, ease: E.back, oy: 40 });
      show(c, t, C["close.p3"], tn + 0.1, { dy: 40, fs: 0.85, ease: E.back, oy: 40 });
      const rev = p(t, tn + 0.25, 0.9, E.out4);
      lg.style.clipPath = `inset(0 ${100 - 100 * rev}% 0 0)`;
      const settle = p(t, te, 0.8, E.inOut);
      tf(lg, { s: lerp(1.05, 1, rev) * lerp(1, 0.86, settle), y: lerp(0, -40, settle), o: Math.min(1, rev * 3) });
      tf(glow, { o: p(t, tn + 0.25, 0.8) * (0.8 + 0.2 * Math.sin(t * 1.7)), s: lerp(0.7, 1, p(t, tn + 0.25, 1.2)), y: lerp(0, -40, settle) });
      show(url, t, te + 0.25, null, { dy: 18 });
      show(ver, t, te + 0.5, null, { dy: 12 });
    };
  });

  // ------------------------------------------------------------ frame
  function renderFrame(t) {
    renderBg(t);
    for (const s of scenes) {
      const start = s.sc.start, end = s.sc.end;
      const last = s.id === "close";
      const visible = t >= start - 0.01 && (last || t < end + 0.5);
      s.root.style.display = visible ? "block" : "none";
      if (!visible) continue;
      s.update(t);
      if (!last) {
        const q = p(t, end - 0.08, 0.45, E.inOut);
        s.root.style.opacity = 1 - q;
        s.root.style.transform = `translateY(${-26 * q}px)`;
        s.root.style.filter = q > 0.01 ? `blur(${8 * q}px)` : "none";
      }
    }
    renderChrome(t);
    renderCaptions(t);
    // the first and last frames fade from and to the base colour
    const st = document.getElementById("stage");
    st.style.opacity = Math.min(p(t, 0, 0.35, E.lin), 1 - p(t, TL.duration - 0.6, 0.6, E.lin));
  }
  window.renderFrame = renderFrame;
  window.__ready = document.fonts.ready.then(() => true);

  // Preview: open stage.html?t=12.5 for a still, or with no query to play in real time.
  const q = new URLSearchParams(location.search);
  if (!q.has("render")) {
    if (q.has("t")) renderFrame(parseFloat(q.get("t")));
    else {
      const t0 = performance.now();
      const loop = () => { renderFrame(((performance.now() - t0) / 1000) % TL.duration); requestAnimationFrame(loop); };
      loop();
    }
  }
})();
