// 濡れない経路デモ。地図操作はLeaflet、データはすべて同一オリジンの server.py 経由
// （JMAのJSONにCORSヘッダーが無くブラウザから直接fetchできないため、サーバー側で代行する）。
// 経路は地図クリックで複数の経由地を追加し、server.py が OSRM で道路にスナップした経路を返す。
let map, jmaLayer;
let waypointMarkers = [];      // クリックで追加した経由地（生の緯度経度）
let previewLine = null;        // クリック中の直線プレビュー
let roadLine = null;           // 評価後、実際に道路に沿った経路
let pointMarkers = [];         // 評価後の各点（濡れる/晴れ）マーカー
let frames = { base: null, validtimes: [] };
let latestResult = null;

function tileUrl(basetime, validtime) {
  return `https://www.jma.go.jp/bosai/jmatile/data/nowc/${basetime}/none/${validtime}/surf/hrpns/{z}/{x}/{y}.png`;
}

async function main() {
  map = L.map("map").setView([35.6812, 139.7671], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors", maxZoom: 18,
  }).addTo(map);

  map.on("click", onMapClick);

  const res = await fetch("/api/frames");
  frames = await res.json();
  const slider = document.getElementById("frame-slider");
  slider.max = frames.validtimes.length; // 0=実況(base), 1..N=予測
  slider.value = 0;
  slider.addEventListener("input", () => updateFrame(parseInt(slider.value, 10)));
  updateFrame(0);

  document.getElementById("btn-eval").addEventListener("click", evaluate);
  document.getElementById("btn-clear").addEventListener("click", clearWaypoints);
}

function frameValidtime(idx) {
  return idx === 0 ? frames.base : frames.validtimes[idx - 1];
}

function formatJst(vt) {
  // "20260929021500" -> "02:15"
  return `${vt.slice(8, 10)}:${vt.slice(10, 12)}`;
}

function updateFrame(idx) {
  const vt = frameValidtime(idx);
  document.getElementById("frame-label").textContent =
    idx === 0 ? `実況 ${formatJst(vt)}` : `${idx * 5}分後 ${formatJst(vt)}`;
  if (jmaLayer) map.removeLayer(jmaLayer);
  jmaLayer = L.tileLayer(tileUrl(frames.base, vt), {
    opacity: 0.7, maxNativeZoom: 10, minZoom: 4, maxZoom: 18,
  }).addTo(map);
}

function onMapClick(e) {
  const idx = waypointMarkers.length + 1;
  const marker = L.marker(e.latlng, {
    icon: L.divIcon({ className: "waypoint-icon", html: `${idx}`, iconSize: [22, 22] }),
  }).addTo(map);
  waypointMarkers.push(marker);
  redrawPreview();
  updateWaypointUi();
}

function redrawPreview() {
  if (previewLine) map.removeLayer(previewLine);
  if (waypointMarkers.length >= 2) {
    previewLine = L.polyline(waypointMarkers.map((m) => m.getLatLng()), { color: "#a0aec0", dashArray: "6 6" }).addTo(map);
  }
}

function updateWaypointUi() {
  document.getElementById("waypoint-count").textContent = `経由地: ${waypointMarkers.length}点`;
  document.getElementById("btn-eval").disabled = waypointMarkers.length < 2;
}

function clearWaypoints() {
  waypointMarkers.forEach((m) => map.removeLayer(m));
  waypointMarkers = [];
  if (previewLine) { map.removeLayer(previewLine); previewLine = null; }
  if (roadLine) { map.removeLayer(roadLine); roadLine = null; }
  clearPointMarkers();
  updateWaypointUi();
  document.getElementById("result-summary").textContent = "経由地を指定して「評価」を押してください。";
  document.querySelector("#result-table tbody").innerHTML = "";
}

function clearPointMarkers() {
  pointMarkers.forEach((m) => map.removeLayer(m));
  pointMarkers = [];
}

async function evaluate() {
  const mode = document.getElementById("mode").value;
  const params = new URLSearchParams();
  waypointMarkers.forEach((m) => {
    const ll = m.getLatLng();
    params.append("points", `${ll.lat},${ll.lng}`);
  });
  params.append("mode", mode);
  document.getElementById("result-summary").textContent = "評価中…（道路経路を取得しています）";
  const res = await fetch(`/api/route?${params}`);
  const result = await res.json();
  if (result.error) {
    document.getElementById("result-summary").textContent = `エラー: ${result.error}`;
    return;
  }
  latestResult = result;
  renderResult(result);
}

function renderResult(result) {
  const best = result.best;
  const summary = document.getElementById("result-summary");
  const routing = result.used_road_routing ? "道路沿い（OSRM）" : "直線補間（道路経路が取得できず代替）";
  let text = best.wet_ratio === 0
    ? `${best.depart_offset_min}分後に出発すれば、経路上で雨に当たらない見込みです。`
    : `どの時間帯でも完全には避けられませんが、${best.depart_offset_min}分後の出発が最も濡れにくい見込みです（${best.wet_points}/${best.total_points}点で降雨）。`;
  text += ` [経路: ${routing}、距離${result.distance_m}m]`;
  summary.textContent = text;

  const tbody = document.querySelector("#result-table tbody");
  tbody.innerHTML = "";
  result.evals.forEach((e) => {
    const tr = document.createElement("tr");
    if (e.depart_offset_min === best.depart_offset_min) tr.classList.add("best");
    tr.innerHTML = `<td>${e.depart_offset_min}分後</td><td>${e.wet_points}/${e.total_points}</td><td>${Math.round(e.wet_ratio * 100)}%</td>`;
    tr.addEventListener("click", () => showPoints(e));
    tbody.appendChild(tr);
  });

  // 道路に沿った実際の経路ラインを描画
  if (roadLine) map.removeLayer(roadLine);
  roadLine = L.polyline(result.geometry.map((p) => [p.lat, p.lon]), { color: "#2b6cb0", weight: 4 }).addTo(map);

  showPoints(best);
}

function showPoints(evalRow) {
  clearPointMarkers();
  evalRow.points.forEach((p) => {
    const marker = L.circleMarker([p.lat, p.lon], {
      radius: 6, color: "#fff", weight: 1,
      fillColor: p.raining ? "#c53030" : "#2f855a", fillOpacity: 0.9,
    }).addTo(map);
    marker.bindTooltip(`${p.raining ? "☔ 雨" : "☀ 晴れ"}（到達 ${p.eta.slice(11, 16)}）`);
    pointMarkers.push(marker);
  });
}

main();
