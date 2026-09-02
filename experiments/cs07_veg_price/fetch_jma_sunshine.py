"""気象庁「過去の気象データ検索」(etrn) から日別の日照時間を取得する。

出典: 気象庁ホームページ https://www.data.jma.go.jp/stats/etrn/
- daily_s1.php（気象官署）の「主な要素」表を月ごとに取得してパースする。
- 出力: data/cs07/jma_sunshine_<station>.csv  （列: date, sunshine_h）

注意:
- 1回のアクセスで1か月分。サーバ負荷に配慮して 1 リクエストごとに sleep する。
- より大量・多要素が必要になったら obsdl（POST API）へ移行する。今回は1地点・1要素なので etrn で十分。
"""

from __future__ import annotations

import io
import sys
import time
import datetime as dt

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import DATA_DIR, JMA_STATIONS, YEAR_START, YEAR_END

ETRN_URL = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
SUNSHINE_IDX = 16  # 「主な要素」表のデータ行における日照時間(h)の列位置（0=日）
REQUEST_INTERVAL_SEC = 1.5
MISSING_TOKENS = {"", "×", "///", "#", "--]", "×]"}


def _to_hours(raw: str) -> float:
    """セル文字列を日照時間[h]に変換。'--'=現象なし=0.0、欠測はNaN。"""
    s = raw.strip()
    # 準正常値/資料不足の記号を除去
    for mark in (")", "]", "*", " "):
        s = s.replace(mark, "")
    if s == "--":
        return 0.0
    if s in MISSING_TOKENS or s == "":
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def fetch_month(prec_no: int, block_no: str, year: int, month: int) -> pd.DataFrame:
    params = {"prec_no": prec_no, "block_no": block_no,
              "year": year, "month": month, "day": "", "view": "p1"}
    r = requests.get(ETRN_URL, params=params, timeout=30)
    r.raise_for_status()
    r.encoding = "shift_jis"
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", id="tablefix1")
    if table is None:
        raise RuntimeError(f"表が見つからない: {year}-{month:02d} prec={prec_no} block={block_no}")

    records = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        head = cells[0].get_text(strip=True)
        if not head.isdigit():
            continue
        day = int(head)
        vals = [c.get_text(strip=True) for c in cells]
        if len(vals) <= SUNSHINE_IDX:
            continue
        records.append((dt.date(year, month, day), _to_hours(vals[SUNSHINE_IDX])))

    df = pd.DataFrame(records, columns=["date", "sunshine_h"])
    # レイアウト変化の簡易検知: 実測値(非NaN)が5個以上あり、その大半が 0〜24h の外なら異常。
    # 当月など「ほぼ空」の月は NaN が多くて当然なので誤検知しないよう非NaNだけで見る。
    valid = df["sunshine_h"].dropna()
    if len(valid) >= 5 and valid.between(0, 24).mean() < 0.5:
        raise RuntimeError(f"日照時間の列位置がずれている可能性 (妥当率={valid.between(0, 24).mean():.2f})")
    return df


def fetch_station(key: str) -> pd.DataFrame:
    st = JMA_STATIONS[key]
    frames = []
    today = dt.date.today()
    for year in range(YEAR_START, YEAR_END + 1):
        for month in range(1, 13):
            if dt.date(year, month, 1) > today:
                break
            print(f"  {st['name']} {year}-{month:02d} ...", flush=True)
            frames.append(fetch_month(st["prec_no"], st["block_no"], year, month))
            time.sleep(REQUEST_INTERVAL_SEC)
    df = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    return df


def main(argv: list[str]) -> int:
    keys = argv[1:] or [k for k in JMA_STATIONS]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for key in keys:
        if key not in JMA_STATIONS:
            print(f"未知の地点キー: {key}（{list(JMA_STATIONS)}）", file=sys.stderr)
            continue
        print(f"[{key}] {JMA_STATIONS[key]['name']} を取得")
        df = fetch_station(key)
        out = DATA_DIR / f"jma_sunshine_{key}.csv"
        df.to_csv(out, index=False)
        n_missing = int(df["sunshine_h"].isna().sum())
        print(f"  -> {out}  ({len(df)}日, 欠測 {n_missing}日)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
