"""都営バスのリアルタイム運行情報を定期的にポーリングし、遅延(秒)を算出して蓄積する。

背景: ODPTのodpt:Bus(リアルタイム位置情報)には、odpt:Train(列車)にあるodpt:delay
(遅延秒数)に相当するフィールドが無い。そのため、
  odpt:Busの odpt:fromBusstopPoleTime (実際にそのバス停を発車/通過した時刻)
  と、odpt:busTimetable で示される odpt:BusTimetable の該当バス停の予定時刻
を自分で突き合わせて delay_seconds = 実際 - 予定 を算出する。

ODPTは過去データのアーカイブを提供しないため、この蓄積は「今から定期実行して
自分でログを溜める」ことで初めて意味を持つ。cron/launchd等で例えば5分おきに
実行することを想定（1回の実行は数秒〜数十秒で完了する）。

出力: data/processed/bus_delay_log.csv に1行=1観測として追記する
（busroute, busstop, scheduled, actual, delay_seconds, polled_at 等）。
BusTimetableの取得結果は data/raw/busTimetable_cache.json にキャッシュし、
同じ便を何度もポーリングしても時刻表を毎回取得しないようにする。

天気側: 各バス停に最も近いアメダス観測点の10分降水量を同じ行に付与する
（コスト・精度を検討した結果、まずは軽量なアメダスから。詳細はfetch_amedas.py参照）。
バス停の緯度経度・名称は data/raw/busstop_latlon_cache.json にキャッシュする。
"""
import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd
import requests

from check_operators import get
import fetch_amedas

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

TIMETABLE_CACHE_PATH = RAW_DIR / "busTimetable_cache.json"
BUSSTOP_LATLON_CACHE_PATH = RAW_DIR / "busstop_latlon_cache.json"
LOG_PATH = PROCESSED_DIR / "bus_delay_log.csv"

OPERATOR = "odpt.Operator:Toei"


def load_timetable_cache() -> dict:
    if TIMETABLE_CACHE_PATH.exists():
        return json.loads(TIMETABLE_CACHE_PATH.read_text())
    return {}


def save_timetable_cache(cache: dict):
    TIMETABLE_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))


def fetch_timetable(tt_id: str, cache: dict, max_retry: int = 5) -> dict | None:
    if tt_id in cache:
        return cache[tt_id]
    for attempt in range(max_retry):
        try:
            results = get("odpt:BusTimetable", **{"owl:sameAs": tt_id})
            break
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                time.sleep(2 ** attempt)  # 1,2,4,8,16秒と待って再試行
                continue
            raise
    else:
        return None  # 上限まで429が続いた場合は今回はスキップ(次回ポーリングで再取得)

    obj = results[0] if results else None
    cache[tt_id] = obj
    time.sleep(0.3)  # 新規取得時のみ少し間隔を空け、429を未然に防ぐ
    return obj


def load_busstop_cache() -> dict:
    if BUSSTOP_LATLON_CACHE_PATH.exists():
        return json.loads(BUSSTOP_LATLON_CACHE_PATH.read_text())
    return {}


def save_busstop_cache(cache: dict):
    BUSSTOP_LATLON_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))


def fetch_busstop_info(busstop_id: str, cache: dict, max_retry: int = 5) -> dict | None:
    """バス停の{"lat", "lon", "name"}を返す。初回のみODPTに問い合わせ、以降はキャッシュを使う。"""
    if busstop_id in cache:
        return cache[busstop_id]
    for attempt in range(max_retry):
        try:
            results = get("odpt:BusstopPole", **{"owl:sameAs": busstop_id})
            break
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            raise
    else:
        return None

    if results and "geo:lat" in results[0]:
        info = {"lat": results[0]["geo:lat"], "lon": results[0]["geo:long"],
                "name": results[0].get("dc:title")}
    else:
        info = None
    cache[busstop_id] = info
    time.sleep(0.3)
    return info


def scheduled_time_for_stop(timetable: dict, busstop_id: str, actual_dt: dt.datetime):
    """時刻表の中から、指定したバス停の予定時刻を探し、actual_dtと同じ日付のdatetimeで返す。"""
    for row in timetable.get("odpt:busTimetableObject", []):
        if row.get("odpt:busstopPole") != busstop_id:
            continue
        time_str = row.get("odpt:departureTime") or row.get("odpt:arrivalTime")
        if not time_str:
            continue
        h, m = (int(x) for x in time_str.split(":")[:2])
        # 深夜バス(24時以降を 24:xx, 25:xx 等で表現する場合)に対応
        extra_days, h = divmod(h, 24)
        return actual_dt.replace(hour=h, minute=m, second=0, microsecond=0) + dt.timedelta(days=extra_days)
    return None


def poll_once() -> pd.DataFrame:
    cache = load_timetable_cache()
    busstop_cache = load_busstop_cache()
    amedas_stations = fetch_amedas.load_station_table()
    try:
        amedas_obs, amedas_time = fetch_amedas.fetch_latest_observations()
    except requests.RequestException as e:
        print(f"アメダス取得失敗(今回は降水量なしで続行): {e}")
        amedas_obs, amedas_time = {}, None

    buses = get("odpt:Bus", **{"odpt:operator": OPERATOR})
    polled_at = dt.datetime.now().isoformat()

    rows = []
    for bus in buses:
        tt_id = bus.get("odpt:busTimetable")
        from_pole = bus.get("odpt:fromBusstopPole")
        from_time_str = bus.get("odpt:fromBusstopPoleTime")
        if not (tt_id and from_pole and from_time_str):
            continue

        timetable = fetch_timetable(tt_id, cache)
        if timetable is None:
            continue

        actual_dt = dt.datetime.fromisoformat(from_time_str)
        scheduled_dt = scheduled_time_for_stop(timetable, from_pole, actual_dt)
        if scheduled_dt is None:
            continue

        delay_seconds = (actual_dt - scheduled_dt).total_seconds()

        # バス停に最も近いアメダス観測点の10分降水量を付与
        station_code, station_name, station_dist_km, precip10m = None, None, None, None
        busstop_info = fetch_busstop_info(from_pole, busstop_cache)
        if busstop_info and amedas_obs:
            station_code, station_dist_km = fetch_amedas.nearest_station(
                busstop_info["lat"], busstop_info["lon"], amedas_stations)
            station_name = amedas_stations[station_code]["name"]
            precip10m = amedas_obs.get(station_code, {}).get("precipitation10m", [None])[0]

        rows.append({
            "polled_at": polled_at,
            "bus_id": bus.get("owl:sameAs"),
            "busroute": bus.get("odpt:busroute"),
            "busstop": from_pole,
            "busstop_name": busstop_info["name"] if busstop_info else None,
            "scheduled_time": scheduled_dt.isoformat(),
            "actual_time": actual_dt.isoformat(),
            "delay_seconds": delay_seconds,
            "amedas_time": amedas_time,
            "amedas_station": station_name,
            "amedas_station_dist_km": round(station_dist_km, 2) if station_dist_km is not None else None,
            "precipitation10m_mm": precip10m,
        })

    save_timetable_cache(cache)
    save_busstop_cache(busstop_cache)
    return pd.DataFrame(rows)


def main():
    df = poll_once()
    print(f"今回取得: {len(df)}件の遅延観測")
    if len(df):
        print(f"遅延(秒)の分布: 平均{df['delay_seconds'].mean():.0f}秒, "
              f"最大{df['delay_seconds'].max():.0f}秒, 最小{df['delay_seconds'].min():.0f}秒")
        n_rain = (df["precipitation10m_mm"].fillna(0) > 0).sum()
        print(f"降水量を付与できた行: {df['precipitation10m_mm'].notna().sum()}/{len(df)}"
              f"（うち直近10分に降水あり: {n_rain}件）")
        df.to_csv(LOG_PATH, mode="a", header=not LOG_PATH.exists(), index=False)
        print(f"保存先: {LOG_PATH}（累積 {sum(1 for _ in open(LOG_PATH)) - 1}件）")


if __name__ == "__main__":
    main()
