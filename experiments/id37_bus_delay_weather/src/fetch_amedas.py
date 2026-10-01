"""気象庁アメダスの実況データを取得し、指定した緯度経度に最も近い観測点の
10分降水量を返す。バス停ごとの最寄り観測点を求め、バス遅延と突き合わせるために使う。

コスト・精度の検討（ユーザーとの相談で「軽量なアメダスから始める」と決定）:
- ナウキャスト(250mメッシュ)の方が空間代表性は高いが、データ量・実装コストが重い。
- アメダスは観測点そのものの実測値で精度は高いが、観測点が疎（東京都心部で数点）。
  まずアメダスでパイプラインを完成させ、弱い/ノイジーな結果が出た場合に
  該当イベントだけナウキャストで再検証する、という段階的な方針。

データソース: 気象庁 bosai JSON (無料・登録不要)
  - 観測点一覧: https://www.jma.go.jp/bosai/amedas/const/amedastable.json
  - 最新時刻: https://www.jma.go.jp/bosai/amedas/data/latest_time.txt
  - 観測値: https://www.jma.go.jp/bosai/amedas/data/map/{YYYYMMDDHHMMSS}.json
"""
import datetime as dt
import json
import math
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STATION_TABLE_PATH = RAW_DIR / "amedas_stations.json"
STATION_TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
LATEST_TIME_URL = "https://www.jma.go.jp/bosai/amedas/data/latest_time.txt"
OBS_URL_TEMPLATE = "https://www.jma.go.jp/bosai/amedas/data/map/{ts}.json"


def _dms_to_deg(dms: list) -> float:
    """[度, 分]形式(分は60進)を10進の度に変換する。"""
    deg, minute = dms
    return deg + minute / 60


def load_station_table() -> dict:
    """観測点一覧を取得(初回のみダウンロードしローカルにキャッシュ)。
    {station_code: {"name": str, "lat": float, "lon": float}} を返す。
    降水量の無い観測点(風向風速専用等)は除く。
    """
    if STATION_TABLE_PATH.exists():
        raw = json.loads(STATION_TABLE_PATH.read_text())
    else:
        r = requests.get(STATION_TABLE_URL, timeout=30)
        r.raise_for_status()
        raw = r.json()
        STATION_TABLE_PATH.write_text(json.dumps(raw, ensure_ascii=False))

    stations = {}
    for code, info in raw.items():
        # elems の1文字目が"1"なら降水量を観測している(気象庁の仕様)
        if not info.get("elems", "")[:1] == "1":
            continue
        stations[code] = {
            "name": info["kjName"],
            "lat": _dms_to_deg(info["lat"]),
            "lon": _dms_to_deg(info["lon"]),
        }
    return stations


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_station(lat: float, lon: float, stations: dict) -> tuple[str, float]:
    """指定した緯度経度に最も近い観測点の(station_code, 距離km)を返す。"""
    best_code, best_dist = None, float("inf")
    for code, info in stations.items():
        d = _haversine_km(lat, lon, info["lat"], info["lon"])
        if d < best_dist:
            best_code, best_dist = code, d
    return best_code, best_dist


def fetch_latest_observations() -> tuple[dict, str]:
    """最新時刻の全観測点データを取得する。(観測データdict, 観測時刻ISO文字列) を返す。"""
    r = requests.get(LATEST_TIME_URL, timeout=15)
    r.raise_for_status()
    latest_time_str = r.text.strip()
    latest_dt = dt.datetime.fromisoformat(latest_time_str)
    ts = latest_dt.strftime("%Y%m%d%H%M%S")

    r = requests.get(OBS_URL_TEMPLATE.format(ts=ts), timeout=30)
    r.raise_for_status()
    return r.json(), latest_time_str


if __name__ == "__main__":
    stations = load_station_table()
    print(f"降水量を観測している観測点数: {len(stations)}")

    obs, obs_time = fetch_latest_observations()
    print(f"観測時刻: {obs_time}")

    # テスト: テレコムセンター駅前(都営バスのバス停)に最も近い観測点
    code, dist = nearest_station(35.617403, 139.778878, stations)
    station = stations[code]
    precip = obs.get(code, {}).get("precipitation10m", [None, None])[0]
    print(f"最寄り観測点: {station['name']}({code}), 距離{dist:.1f}km, 10分降水量={precip}mm")
