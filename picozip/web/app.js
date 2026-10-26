"use strict";

const COLORS = ["#56d4dd", "#7c8cff", "#3fb950", "#fbbf24", "#f47067"];

let DATA = null;
let timers = {};

// ---------- canvas helpers ----------
function fitCanvas(cv, cssH) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = cv.clientWidth;
  cv.style.height = cssH + "px";
  cv.width = Math.round(cssW * dpr);
  cv.height = Math.round(cssH * dpr);
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: cssW, hgt: cssH };
}

// ---------- presets ----------
const PARA = ("Compression works by removing redundancy. A text file repeats " +
  "common letters and whole words, so a dictionary coder can replace repeated " +
  "phrases with short references. Random bytes carry no redundancy at all, and " +
  "no lossless codec can shrink them. Huffman codes assign short bit strings to " +
  "frequent symbols, while LZ77 searches a sliding window for a previous " +
  "occurrence and emits a distance and a length.\n").repeat(8);

function makePreset(name) {
  if (name === "text") return PARA;
  if (name === "repetitive") return "ABCABCABC".repeat(120) + "AAAA".repeat(30);
  if (name === "runs") return "A".repeat(300) + "B".repeat(240) + "ab".repeat(160);
  if (name === "random") {
    const alpha = "0123456789abcdef";
    let s = "";
    for (let i = 0; i < 1200; i++)
      s += alpha[Math.floor(Math.random() * alpha.length)];
    return s;
  }
  return document.getElementById("text").value;
}

// ---------- tabs ----------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".tabbody").forEach((b) => b.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
    if (DATA) requestAnimationFrame(drawAll);
  });
});

// ---------- input ----------
const presetSel = document.getElementById("preset");
const textArea = document.getElementById("text");
textArea.value = makePreset("text");

presetSel.addEventListener("change", () => {
  if (presetSel.value !== "custom") {
    textArea.value = makePreset(presetSel.value);
    analyze();
  }
});
let debounce = null;
textArea.addEventListener("input", () => {
  presetSel.value = "custom";
  clearTimeout(debounce);
  debounce = setTimeout(analyze, 250);
});

async function analyze() {
  const status = document.getElementById("status");
  status.textContent = "分析中…";
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: textArea.value }),
    });
    DATA = await resp.json();
    renderCompress();
    renderHuffman();
    renderLzss();
    renderLzw();
    requestAnimationFrame(drawAll);
    status.textContent = "完成";
  } catch (e) {
    status.textContent = "请求失败：" + e.message;
  }
}

function drawAll() {
  drawHuffman();
  drawLzss();
  drawBench();
}

// ---------- helpers ----------
function fmt(n) {
  if (n == null) return "—";
  return n.toLocaleString("en-US");
}
function cls(ratio) {
  return ratio <= 1.0 ? "ok" : "bad";
}

// ---------- compress tab ----------
function renderCompress() {
  const d = DATA;
  const cards = document.getElementById("cards");
  cards.innerHTML = [
    card("原始字节", fmt(d.original_size)),
    card("熵", d.entropy.bits_per_byte + "<small> bit/byte</small>", true),
    card("熵下界", fmt(d.entropy.ideal_bytes) + "<small> bytes</small>"),
    card("容器头", "20<small> bytes</small>"),
  ].join("");

  const tb = document.querySelector("#codec-table tbody");
  tb.innerHTML = "";
  d.codecs.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td>${r.name}</td><td>${fmt(r.payload_size)}</td>` +
      `<td>${fmt(r.file_size)}</td>` +
      `<td class="${cls(r.ratio)}">${r.ratio == null ? "—" : r.ratio.toFixed(3)}</td>` +
      `<td>${r.encode_ms.toFixed(2)}</td><td>${r.decode_ms.toFixed(2)}</td>` +
      `<td class="${r.roundtrip ? "ok" : "bad"}">${r.roundtrip ? "✓" : "✗"}</td>`;
    tb.appendChild(tr);
  });

  const bars = document.getElementById("bars");
  const maxRatio = Math.max(1.1, ...d.codecs.map((r) => r.ratio || 1));
  bars.innerHTML = d.codecs.map((r, i) => {
    const pct = Math.min(100, (r.ratio / maxRatio) * 100);
    return `<div class="bar-row">
      <div class="bar-name">${r.name}</div>
      <div class="bar-track"><div class="bar-fill"
        style="width:${pct}%;background:${COLORS[i]}"></div></div>
      <div class="bar-val">${r.ratio == null ? "—" : (r.ratio * 100).toFixed(1) + "%"}</div>
    </div>`;
  }).join("");
}

function card(k, v, accent) {
  return `<div class="card${accent ? " accent" : ""}"><div class="k">${k}</div>` +
    `<div class="v">${v}</div></div>`;
}

// ---------- huffman ----------
function renderHuffman() {
  const h = DATA.huffman;
  document.getElementById("huff-cards").innerHTML = [
    card("不同符号", h.codes.length),
    card("平均码长", h.mean_length.toFixed(3) + "<small> bit</small>", true),
    card("熵", h.entropy.toFixed(3) + "<small> bit/byte</small>"),
    card("合并次数", h.merges.length),
  ].join("");
  const tb = document.querySelector("#huff-table tbody");
  tb.innerHTML = h.codes.slice(0, 80).map((c) => {
    const shown = c.symbol >= 32 && c.symbol < 127 ?
      String.fromCharCode(c.symbol) : "0x" + c.symbol.toString(16).padStart(2, "0");
    return `<tr><td>${shown}</td><td>${c.count}</td><td>${c.length}</td>` +
      `<td style="font-family:monospace;color:var(--accent)">${c.code}</td></tr>`;
  }).join("");
  const slider = document.getElementById("huff-slider");
  slider.max = Math.max(1, h.merges.length);
  slider.value = h.merges.length;
  document.getElementById("huff-step").textContent =
    `${h.merges.length}/${h.merges.length} 次合并`;
  slider.oninput = () => { drawHuffman(); };
  document.getElementById("huff-play").onclick = () => play("huff", slider);
}

function drawHuffman() {
  const h = DATA.huffman;
  if (!h) return;
  const cv = document.getElementById("huff-canvas");
  const { ctx, w, hgt } = fitCanvas(cv, 460);
  ctx.clearRect(0, 0, w, hgt);
  if (!h.tree.nodes.length) {
    ctx.fillStyle = "#8b98a9";
    ctx.fillText("（空输入）", 20, 30);
    return;
  }
  const slider = document.getElementById("huff-slider");
  const step = parseInt(slider.value, 10);
  document.getElementById("huff-step").textContent =
    `${step}/${h.merges.length} 次合并`;

  // nodes that exist after `step` merges
  const created = new Set();
  h.tree.nodes.forEach((n) => { if (n.leaf) created.add(n.id); });
  for (let i = 0; i < step; i++) created.add(h.merges[i].node);

  const xs = h.tree.nodes.filter((n) => n.leaf).map((n) => n.x);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const maxDepth = Math.max(...h.tree.nodes.map((n) => n.y));
  const padL = 30, padR = 30, padT = 30, padB = 44;
  const X = (x) => padL + ((x - minX) / Math.max(1, maxX - minX)) * (w - padL - padR);
  const Y = (y) => padT + (y / Math.max(1, maxDepth)) * (hgt - padT - padB);
  const byId = {};
  h.tree.nodes.forEach((n) => { byId[n.id] = n; });

  // edges
  h.tree.edges.forEach((e) => {
    const parent = byId[e.from];
    if (!created.has(parent.id)) return;
    if (parent.y >= maxDepth) return; // edge created only when parent exists
    const child = byId[e.to];
    if (!created.has(child.id)) return;
    ctx.strokeStyle = e.bit === 0 ? "#5a6b80" : "#56d4dd";
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(X(parent.x), Y(parent.y));
    ctx.lineTo(X(child.x), Y(child.y));
    ctx.stroke();
    ctx.fillStyle = e.bit === 0 ? "#8b98a9" : "#56d4dd";
    ctx.font = "10px monospace";
    ctx.fillText(e.bit, (X(parent.x) + X(child.x)) / 2 + 2,
      (Y(parent.y) + Y(child.y)) / 2 - 2);
  });

  // nodes
  h.tree.nodes.forEach((n) => {
    if (!created.has(n.id)) return;
    const x = X(n.x), y = Y(n.y);
    ctx.beginPath();
    ctx.arc(x, y, n.leaf ? 13 : 15, 0, Math.PI * 2);
    ctx.fillStyle = n.leaf ? "#1a2330" : "#14202c";
    ctx.fill();
    ctx.strokeStyle = n.leaf ? "#7c8cff" : "#56d4dd";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = "#e6edf3";
    ctx.font = "9px monospace";
    ctx.textAlign = "center";
    if (n.leaf) {
      const shown = n.symbol >= 32 && n.symbol < 127 ?
        String.fromCharCode(n.symbol) : n.symbol.toString(16);
      ctx.fillText(shown, x, y + 3);
      ctx.fillStyle = "#8b98a9";
      ctx.fillText(n.weight, x, y + 26);
    } else {
      ctx.fillText(n.weight, x, y + 3);
    }
    ctx.textAlign = "left";
  });
}

// ---------- lzss ----------
function renderLzss() {
  const z = DATA.lzss;
  document.getElementById("lzss-cards").innerHTML = [
    card("token 数", z.total_tokens, true),
    card("窗口", fmt(z.window) + "<small> bytes</small>"),
    card("最短匹配", z.min_match + "<small> bytes</small>"),
    card("最长匹配", z.max_match + "<small> bytes</small>"),
  ].join("");
  const tb = document.querySelector("#lzss-table tbody");
  tb.innerHTML = z.tokens.map((t, i) => {
    if (t.kind === "lit") {
      const shown = t.byte >= 32 && t.byte < 127 ?
        String.fromCharCode(t.byte) : "0x" + t.byte.toString(16);
      return `<tr><td>${i}</td><td>${t.pos}</td>` +
        `<td><span class="tag lit">literal</span></td>` +
        `<td>—</td><td>—</td><td>${shown}</td></tr>`;
    }
    return `<tr><td>${i}</td><td>${t.pos}</td>` +
      `<td><span class="tag match">match</span></td>` +
      `<td>${t.distance}</td><td>${t.length}</td><td>—</td></tr>`;
  }).join("");
  const slider = document.getElementById("lzss-slider");
  slider.max = Math.max(0, z.tokens.length - 1);
  slider.value = 0;
  slider.oninput = () => drawLzss();
  document.getElementById("lzss-play").onclick = () => play("lzss", slider);
}

function drawLzss() {
  const z = DATA.lzss;
  const cv = document.getElementById("lzss-canvas");
  const { ctx, w, hgt } = fitCanvas(cv, 220);
  ctx.clearRect(0, 0, w, hgt);
  const text = DATA.original_text;
  const k = parseInt(document.getElementById("lzss-slider").value, 10) || 0;
  const tok = z.tokens[k];
  if (!tok) return;
  document.getElementById("lzss-step").textContent =
    `token ${k + 1}/${z.tokens.length}  @${tok.pos}`;

  const len = tok.kind === "match" ? tok.length : 1;
  let start = Math.max(0, tok.pos - 18);
  let end = Math.min(text.length, tok.pos + len + 20);
  if (tok.kind === "match") start = Math.max(0, Math.min(start, tok.from));
  const cells = end - start;
  const cell = Math.max(10, Math.min(26, (w - 40) / Math.max(1, cells)));
  const x0 = 20, y0 = 70, ch = 26;

  function idx(i) { return x0 + (i - start) * cell; }
  for (let i = start; i < end; i++) {
    const x = idx(i);
    let fill = "#1a2330", stroke = "#253040";
    if (i >= tok.pos && i < tok.pos + len) {
      fill = tok.kind === "match" ? "rgba(251,191,36,.30)" : "rgba(124,140,255,.30)";
      stroke = tok.kind === "match" ? "#fbbf24" : "#7c8cff";
    }
    if (tok.kind === "match" && i >= tok.from && i < tok.from + len) {
      fill = "rgba(63,185,80,.22)";
      stroke = "#3fb950";
    }
    ctx.fillStyle = fill;
    ctx.strokeStyle = stroke;
    ctx.fillRect(x, y0, cell - 1, ch);
    ctx.strokeRect(x, y0, cell - 1, ch);
    ctx.fillStyle = "#e6edf3";
    ctx.font = "11px monospace";
    ctx.textAlign = "center";
    const c = text.charCodeAt(i);
    ctx.fillText(c >= 32 && c < 127 ? text[i] : "·", x + cell / 2, y0 + 17);
    ctx.fillStyle = "#5a6b80";
    ctx.font = "8px monospace";
    ctx.fillText(i, x + cell / 2, y0 + ch + 12);
  }
  ctx.textAlign = "left";
  ctx.fillStyle = "#fbbf24";
  ctx.font = "12px sans-serif";
  if (tok.kind === "match") {
    ctx.fillText("→ 回退 distance=" + tok.distance + " 复制 length=" +
      tok.length + "（绿=源  黄=目标）", 20, 30);
  } else {
    const shown = tok.byte >= 32 && tok.byte < 127 ?
      String.fromCharCode(tok.byte) : "0x" + tok.byte.toString(16);
    ctx.fillText("→ 输出字面量 " + shown, 20, 30);
  }
}

// ---------- lzw ----------
function renderLzw() {
  const z = DATA.lzw;
  document.getElementById("lzw-cards").innerHTML = [
    card("输出步数", z.frames.length + (z.total > z.frames.length ? "+" : ""), true),
    card("码位宽度", "12<small> bit</small>"),
    card("码表上限", fmt(z.max_codes)),
    card("初始符号", "256 + CLEAR/END"),
  ].join("");
  const slider = document.getElementById("lzw-slider");
  slider.max = Math.max(0, z.frames.length - 1);
  slider.value = 0;
  slider.oninput = () => drawLzw();
  document.getElementById("lzw-play").onclick = () => play("lzw", slider);
  drawLzw();
}

function drawLzw() {
  const z = DATA.lzw;
  const k = parseInt(document.getElementById("lzw-slider").value, 10) || 0;
  const shown = z.frames.slice(0, k + 1);
  document.getElementById("lzw-step").textContent =
    `步 ${k + 1}/${z.frames.length}`;
  const tb = document.querySelector("#lzw-table tbody");
  tb.innerHTML = shown.map((f, i) => {
    const phrase = (f.phrase || "").replace(/\n/g, "↵");
    const added = f.added == null ? "—" :
      f.added.replace(/\n/g, "↵");
    return `<tr><td>${i + 1}</td><td style="color:var(--accent)">${f.code}</td>` +
      `<td style="font-family:monospace">${escapeHtml(phrase)}</td>` +
      `<td style="font-family:monospace;color:var(--green)">${escapeHtml(added)}</td>` +
      `<td>${f.dict_size}</td></tr>`;
  }).join("");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
}

// ---------- bench ----------
function drawBench() {
  const rows = DATA.codecs;
  const cv = document.getElementById("bench-canvas");
  const { ctx, w, hgt } = fitCanvas(cv, 420);
  ctx.clearRect(0, 0, w, hgt);
  const padL = 56, padR = 20, padT = 24, padB = 60;
  const plotW = w - padL - padR;
  const plotH = hgt - padT - padB;
  const maxR = Math.max(1.05, ...rows.map((r) => r.ratio || 1));
  const Y = (r) => padT + plotH - (r / maxR) * plotH;
  const n = rows.length;
  const slot = plotW / n;
  const bw = Math.min(70, slot * 0.55);

  // grid + y labels
  ctx.strokeStyle = "#253040";
  ctx.fillStyle = "#8b98a9";
  ctx.font = "11px monospace";
  for (let g = 0; g <= 5; g++) {
    const val = (maxR * g / 5);
    const y = Y(val);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.fillText(val.toFixed(2), 8, y + 4);
  }
  // ratio=1 line
  ctx.strokeStyle = "#5a6b80";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(padL, Y(1));
  ctx.lineTo(w - padR, Y(1));
  ctx.stroke();
  ctx.setLineDash([]);

  // entropy bound
  const ideal = DATA.entropy.ideal_bytes / Math.max(1, DATA.original_size);
  if (ideal <= maxR) {
    ctx.strokeStyle = "#3fb950";
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, Y(ideal));
    ctx.lineTo(w - padR, Y(ideal));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#3fb950";
    ctx.fillText("Shannon 下界 " + ideal.toFixed(3), padL + 6, Y(ideal) - 5);
  }

  // bars
  rows.forEach((r, i) => {
    const x = padL + slot * i + (slot - bw) / 2;
    const y = Y(r.ratio || 0);
    ctx.fillStyle = COLORS[i];
    ctx.fillRect(x, y, bw, padT + plotH - y);
    ctx.fillStyle = "#e6edf3";
    ctx.font = "bold 12px monospace";
    ctx.textAlign = "center";
    ctx.fillText((r.ratio || 0).toFixed(3), x + bw / 2, y - 6);
    ctx.fillStyle = "#8b98a9";
    ctx.font = "11px sans-serif";
    ctx.save();
    ctx.translate(x + bw / 2, padT + plotH + 16);
    ctx.rotate(-0.35);
    ctx.fillText(r.name, 0, 0);
    ctx.restore();
    ctx.textAlign = "left";
  });
  ctx.fillStyle = "#5a6b80";
  ctx.font = "10px monospace";
  ctx.fillText("虚线 = 1.0（原始大小）；绿虚线 = 熵下界；柱越高越差", padL, hgt - 8);
}

// ---------- playback ----------
function play(name, slider) {
  if (timers[name]) {
    clearInterval(timers[name]);
    timers[name] = null;
    return;
  }
  timers[name] = setInterval(() => {
    let v = parseInt(slider.value, 10) + 1;
    if (v > parseInt(slider.max, 10)) {
      clearInterval(timers[name]);
      timers[name] = null;
      return;
    }
    slider.value = v;
    if (name === "huff") drawHuffman();
    if (name === "lzss") drawLzss();
    if (name === "lzw") drawLzw();
  }, 350);
}

window.addEventListener("resize", () => DATA && requestAnimationFrame(drawAll));
analyze();
