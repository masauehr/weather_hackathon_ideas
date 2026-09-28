// ID-32 デモUI。webui/data.json（fetch_chart.py + vlm_read.py + validate.py の実測結果）を表示するだけの
// 静的ビュー。読者切替（一般/こども）は同じ判定結果を言い換えて出し分ける。
let DATA = null;
let readerMode = "general";

async function main() {
  const res = await fetch("data.json");
  DATA = await res.json();

  document.getElementById("chart-time").textContent = DATA.chart_time_jst;
  document.getElementById("pattern-badge").textContent = DATA.pattern;
  setConfidenceBadge(DATA.confidence);

  renderImageTabs();
  renderExplain();
  renderGuardrail();

  document.getElementById("btn-general").addEventListener("click", () => setReaderMode("general"));
  document.getElementById("btn-kids").addEventListener("click", () => setReaderMode("kids"));
}

function setConfidenceBadge(conf) {
  const el = document.getElementById("confidence-badge");
  el.textContent = `確信度 ${conf.toFixed(2)}`;
  el.classList.remove("high", "mid", "low");
  if (conf >= 0.7) el.classList.add("high");
  else if (conf >= 0.6) el.classList.add("mid");
  else el.classList.add("low");
}

function renderImageTabs() {
  const tabs = document.getElementById("image-tabs");
  tabs.innerHTML = "";
  DATA.images.forEach((img, i) => {
    const btn = document.createElement("button");
    btn.textContent = img.label;
    if (i === 0) btn.classList.add("active");
    btn.addEventListener("click", () => {
      document.getElementById("chart-image").src = img.src;
      tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
    tabs.appendChild(btn);
  });
  document.getElementById("chart-image").src = DATA.images[0].src;
}

function setReaderMode(mode) {
  readerMode = mode;
  document.getElementById("btn-general").classList.toggle("active", mode === "general");
  document.getElementById("btn-kids").classList.toggle("active", mode === "kids");
  renderExplain();
}

function renderExplain() {
  const content = DATA[readerMode];
  document.getElementById("today-text").textContent = content.today;
  document.getElementById("tomorrow-text").textContent = content.tomorrow;

  const evList = document.getElementById("evidence-list");
  evList.innerHTML = "";
  content.evidence.forEach((e) => {
    const li = document.createElement("li");
    li.textContent = e;
    evList.appendChild(li);
  });

  const cpList = document.getElementById("checkpoints-list");
  cpList.innerHTML = "";
  content.check_points.forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c;
    cpList.appendChild(li);
  });

  document.getElementById("caveats-text").textContent = DATA.caveats;
}

function renderGuardrail() {
  const tbody = document.querySelector("#guardrail-table tbody");
  tbody.innerHTML = "";
  DATA.guardrail_checks.forEach((c) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="verdict ${c.verdict}">${c.verdict}</span></td>
      <td>${c.label}</td>
      <td>${c.detail}</td>
    `;
    tbody.appendChild(tr);
  });

  const acc = DATA.accuracy_note;
  document.getElementById("accuracy-note").textContent =
    `複数事例での検証（${acc.n}件・7パターン）: 正答 ${acc.correct}/${acc.n}。` +
    `${acc.strong.join("・")}は強いが、${acc.weak}`;

  document.getElementById("source-text").textContent = DATA.source;
}

main();
