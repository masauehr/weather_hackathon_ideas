"""ODPT(公共交通オープンデータ)が対応しているバス事業者を実際に調べる偵察スクリプト。

目的: 「バス遅延×天気」の検証プロトタイプを、電車が無い地域で作りたい。だがODPTの
カバー範囲は事業者によってバラバラで、Web検索では確定情報が得られなかった
（ckan.odpt.orgの検索では沖縄のバス事業者が0件だった）。実際のAPIで
「どの事業者が、遅延がわかるリアルタイムデータ(odpt:Bus、GTFS-RT)を提供しているか」を
一覧化し、電車のない地域を選べるようにする。

使い方: .envに ODPT_API_KEY を設定して実行（.env.exampleを参照）。
  cd experiments/id37_bus_delay_weather/src && python check_operators.py
"""
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).resolve().parents[3]  # weather_hackathon_ideas/
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.environ["ODPT_API_KEY"]
BASE = "https://api.odpt.org/api/v4"


def get(path: str, **params):
    params["acl:consumerKey"] = API_KEY
    r = requests.get(f"{BASE}/{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    operators = get("odpt:Operator")
    print(f"登録事業者数(全体・鉄道含む): {len(operators)}\n")

    # 【重要】ODPT仕様書で確認した事実: odpt:Bus(バスのリアルタイム情報)には
    # odpt:Train にある odpt:delay(遅延秒数) に相当するフィールドが無い。
    # バスの遅延は「リアルタイムの通過時刻(odpt:fromBusstopPoleTime)」と
    # 「時刻表(odpt:BusstopPoleTimetable)の予定時刻」を自分で突き合わせて算出する必要がある。
    # そのため、ここでは「odpt:Bus(現在運行中の車両)が1件でも取れる事業者」と
    # 「odpt:BusstopPoleTimetable(突き合わせ用の時刻表)が取れる事業者」の両方を確認し、
    # 遅延を計算できる事業者を特定する。
    bus_capable = []
    for op in operators:
        op_id = op.get("owl:sameAs", op.get("@id", ""))
        title = op.get("dc:title", op_id)
        try:
            buses = get("odpt:Bus", **{"odpt:operator": op_id})
        except requests.HTTPError:
            continue
        if not buses:
            continue
        try:
            timetables = get("odpt:BusstopPoleTimetable", **{"odpt:operator": op_id})
        except requests.HTTPError:
            timetables = []
        bus_capable.append((title, op_id, len(buses), len(timetables)))

    print(f"バスのリアルタイム位置情報(odpt:Bus)を1件以上返した事業者: {len(bus_capable)}\n")
    for title, op_id, n_bus, n_tt in bus_capable:
        tt_mark = f"時刻表あり({n_tt}件) → 遅延を算出可能" if n_tt else "時刻表取得不可 → 遅延算出不可"
        print(f"- {title} ({op_id}): 現在運行中 {n_bus}件, {tt_mark}")

    if not bus_capable:
        print("現時点で稼働中のバス(odpt:Bus)を返した事業者は無かった"
              "（深夜等で運行していない可能性もあるため、時間を変えて再実行推奨）。")


if __name__ == "__main__":
    main()
