"""ID-15 検証: 「濡れない経路・出発時刻」を、気象庁の高解像度降水ナウキャストで評価する。

経路は実際の道路網ではなく、2点間を等間隔に補間した直線（MVPの簡略化。限界はREADME参照）。
出発時刻を5分ずつ遅らせた候補それぞれについて、経路上の各点をその通過予定時刻の
ナウキャスト画像で調べ、「濡れる点の割合」が最小の出発時刻を推す。

出典: 気象庁ホームページ（高解像度降水ナウキャスト）
"""
import math
import sys
from datetime import datetime, timedelta

import fetch_nowcast as fn

WALK_MPS = 4.8 * 1000 / 3600   # 徒歩 4.8km/h
BIKE_MPS = 15.0 * 1000 / 3600  # 自転車 15km/h


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def interpolate_route(start, end, n_points=10):
    """(lat,lon) の2点間を n_points 個の等間隔点に補間し、各点の累積距離(m)も返す。"""
    (lat1, lon1), (lat2, lon2) = start, end
    total = haversine_m(lat1, lon1, lat2, lon2)
    pts = []
    for i in range(n_points):
        t = i / (n_points - 1)
        lat = lat1 + (lat2 - lat1) * t
        lon = lon1 + (lon2 - lon1) * t
        pts.append({"lat": lat, "lon": lon, "dist_m": total * t})
    return pts, total


def _parse(vt):
    return datetime.strptime(vt, "%Y%m%d%H%M%S")


def _fmt(dt):
    return dt.strftime("%Y%m%d%H%M%S")


def nearest_validtime(target_dt, available_vts, base_dt):
    """target_dt 以前で最も近い利用可能な validtime を返す（無ければ最新の実況=baseを使う）。"""
    candidates = [v for v in available_vts if _parse(v) <= target_dt]
    if not candidates:
        return _fmt(base_dt)
    return max(candidates, key=_parse)


def evaluate(route_pts, total_dist_m, speed_mps, depart_offset_min, base, vts):
    """出発を depart_offset_min 分後にした場合の、経路各点の濡れ判定を返す。"""
    base_dt = _parse(base)
    depart_dt = base_dt + timedelta(minutes=depart_offset_min)
    results = []
    for pt in route_pts:
        elapsed_s = pt["dist_m"] / speed_mps
        eta = depart_dt + timedelta(seconds=elapsed_s)
        vt = nearest_validtime(eta, vts, base_dt)
        r = fn.rain_at(pt["lon"], pt["lat"], base, vt)
        results.append({**pt, "eta": eta, "validtime": vt, **r})
    wet = sum(1 for r in results if r["raining"])
    return {"depart_offset_min": depart_offset_min, "wet_points": wet, "total_points": len(results),
            "wet_ratio": wet / len(results), "points": results}


def recommend(start, end, speed_mps, n_points=10, max_wait_min=30):
    route_pts, total_dist_m = interpolate_route(start, end, n_points)
    base, vts = fn.current_forecast()
    step = 5
    offsets = list(range(0, max_wait_min + 1, step))
    evals = [evaluate(route_pts, total_dist_m, speed_mps, off, base, vts) for off in offsets]
    best = min(evals, key=lambda e: (e["wet_ratio"], e["depart_offset_min"]))
    return {"base": base, "distance_m": round(total_dist_m), "evals": evals, "best": best}


def main():
    # デモ: 東京駅 → 皇居外苑（直線・約1.7km）。実況で雨が観測されている地点で検証。
    start = (35.6812, 139.7671)  # 東京駅
    end = (35.6852, 139.7528)    # 皇居外苑あたり
    mode = sys.argv[1] if len(sys.argv) > 1 else "walk"
    speed = WALK_MPS if mode == "walk" else BIKE_MPS

    result = recommend(start, end, speed)
    print(f"基準時刻(実況): {result['base']} / 距離: {result['distance_m']}m / 移動手段: {mode}")
    print(f"{'出発(分後)':>10} {'濡れる点':>8} {'/':1}{'全点':>4} {'比率':>6}")
    for e in result["evals"]:
        mark = " ←最良" if e is result["best"] else ""
        print(f"{e['depart_offset_min']:>10} {e['wet_points']:>8} / {e['total_points']:>4} {e['wet_ratio']*100:>5.0f}%{mark}")

    best = result["best"]
    if best["wet_ratio"] == 0:
        print(f"\n→ {best['depart_offset_min']}分後に出発すれば、経路上で雨に当たらない見込みです。")
    else:
        print(f"\n→ どの時間帯でも完全には避けられませんが、{best['depart_offset_min']}分後の出発が最も濡れにくい見込みです"
              f"（{best['wet_points']}/{best['total_points']}点で降雨）。")


if __name__ == "__main__":
    main()
