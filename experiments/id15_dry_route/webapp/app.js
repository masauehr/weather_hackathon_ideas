// 濡れない経路デモ。地図操作はLeaflet、データはすべて同一オリジンの server.py 経由
// （JMAのJSONにCORSヘッダーが無くブラウザから直接fetchできないため、サーバー側で代行する）。
let map, jmaLayer, routeLine, startMarker, endMarker, pointMarkers = [];
let frames = { base: null, validtimes: [] };
let clickState = "start"; // "start" -> "end" -> "start"（リセット）
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
    idx === 0 ? `実況 ${formatJst(vt)}` : `${(idx) * 5}分後 ${formatJst(vt)}`;
  if (jmaLayer) map.removeLayer(jmaLayer);
  jmaLayer = L.tileLayer(tileUrl(frames.base, vt), {
    opacity: 0.7, maxNativeZoom: 10, minZoom: 4, maxZoom: 18,
  }).addTo(map);
}

function onMapClick(e) {
  if (clickState === "start") {
    if (startMarker) map.removeLayer(startMarker);
    if (endMarker) { map.removeLayer(endMarker); endMarker = null; }
    if (routeLine) { map.removeLayer(routeLine); routeLine = null; }
    clearPointMarkers();
    startMarker = L.marker(e.latlng, { title: "出発地" }).addTo(map);
    clickState = "end";
    document.getElementById("btn-eval").disabled = true;
  } else {
    endMarker = L.marker(e.latlng, { title: "到着地" }).addTo(map);
    routeLine = L.polyline([startMarker.getLatLng(), endMarker.getLatLng()], { color: "#2b6cb0" }).addTo(map);
    clickState = "start";
    document.getElementById("btn-eval").disabled = false;
  }
}

function clearPointMarkers() {
  pointMarkers.forEach((m) => map.removeLayer(m));
  pointMarkers = [];
}

async function evaluate() {
  const mode = document.getElementById("mode").value;
  const s = startMarker.getLatLng(), en = endMarker.getLatLng();
  const params = new URLSearchParams({
    start_lat: s.lat, start_lon: s.lng, end_lat: en.lat, end_lon: en.lng, mode,
  });
  document.getElementById("result-summary").textContent = "評価中…";
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
  if (best.wet_ratio === 0) {
    summary.textContent = `${best.depart_offset_min}分後に出発すれば、経路上で雨に当たらない見込みです。`;
  } else {
    summary.textContent = `どの時間帯でも完全には避けられませんが、${best.depart_offset_min}分後の出発が最も濡れにくい見込みです（${best.wet_points}/${best.total_points}点で降雨）。`;
  }

  const tbody = document.querySelector("#result-table tbody");
  tbody.innerHTML = "";
  result.evals.forEach((e) => {
    const tr = document.createElement("tr");
    if (e.depart_offset_min === best.depart_offset_min) tr.classList.add("best");
    tr.innerHTML = `<td>${e.depart_offset_min}分後</td><td>${e.wet_points}/${e.total_points}</td><td>${Math.round(e.wet_ratio * 100)}%</td>`;
    tr.addEventListener("click", () => showPoints(e));
    tbody.appendChild(tr);
  });
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
