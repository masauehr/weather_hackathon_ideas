"""気象庁「過去の気象データ検索」(etrn) から日別の複数要素を取得する。

出典: 気象庁ホームページ https://www.data.jma.go.jp/stats/etrn/
daily_s1.php（気象官署）を月ごとに2ビュー取得してマージする。
  view=p1 : 降水量合計(idx3), 最高気温(idx7), 日照時間(idx16)
  view=a3 : 全天日射量 MJ/m^2 (idx10)   ※観測が無い官署は空欄→NaN

出力: data/cs07/jma_daily_<station>.csv  （列: date, precip_mm, tmax_c, sunshine_h, solar_mj）

注意: 1リクエスト=1か月・1ビュー。サーバ負荷に配慮して sleep する。
"""

from __future__ import annotations

import sys
import time
import datetime as dt

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import DATA_DIR, JMA_STATIONS, YEAR_START, YEAR_END

ETRN_URL = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
REQUEST_INTERVAL_SEC = 1.2
# データ行（0=日）における列位置
IDX = {
    "p1": {"precip_mm": 3, "tmax_c": 7, "sunshine_h": 16},
    "a3": {"solar_mj": 10},
}
# 妥当性レンジ（レイアウトずれ検知用）
SANE = {"precip_mm": (0, 700), "tmax_c": (-40, 45), "sunshine_h": (0, 24), "solar_mj": (0, 45)}
# '--'（現象なし）を 0.0 とみなす要素
DASH_ZERO = {"precip_mm", "sunshine_h"}


def _to_num(raw: str, dash_zero: bool) -> float:
    s = raw.strip()
    for mark in (")", "]", "*", " ", "&nbsp;"):
        s = s.replace(mark, "")
    if s == "--":
        return 0.0 if dash_zero else float("nan")
    if s in ("", "×", "///", "#"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _fetch_view(prec_no: int, block_no: str, year: int, month: int, view: str) -> pd.DataFrame:
    r = requests.get(ETRN_URL, timeout=30, params={
        "prec_no": prec_no, "block_no": block_no,
        "year": year, "month": month, "day": "", "view": view})
    r.raise_for_status()
    r.encoding = "shift_jis"
    table = BeautifulSoup(r.text, "html.parser").find("table", id="tablefix1")
    if table is None:
        raise RuntimeError(f"表なし {year}-{month:02d} {view} prec={prec_no} block={block_no}")

    cols = IDX[view]
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells or not cells[0].get_text(strip=True).isdigit():
            continue
        day = int(cells[0].get_text(strip=True))
        vals = [c.get_text(strip=True) for c in cells]
        rec = {"date": dt.date(year, month, day)}
        for name, i in cols.items():
            rec[name] = _to_num(vals[i], name in DASH_ZERO) if i < len(vals) else float("nan")
        rows.append(rec)

    df = pd.DataFrame(rows)
    for name in cols:
        valid = df[name].dropna()
        lo, hi = SANE[name]
        if len(valid) >= 5 and valid.between(lo, hi).mean() < 0.5:
            raise RuntimeError(f"{view}/{name} の列位置ずれ疑い ({year}-{month:02d}, 妥当率 {valid.between(lo, hi).mean():.2f})")
    return df


P1_ONLY = False   # main() で --p1only を見て切り替え（全天日射が不要なとき高速化）


def fetch_month(prec_no: int, block_no: str, year: int, month: int) -> pd.DataFrame:
    p1 = _fetch_view(prec_no, block_no, year, month, "p1")
    if P1_ONLY:
        p1["solar_mj"] = float("nan")
        return p1
    time.sleep(REQUEST_INTERVAL_SEC)
    a3 = _fetch_view(prec_no, block_no, year, month, "a3")
    return p1.merge(a3, on="date", how="outer")


def fetch_station(key: str) -> pd.DataFrame:
    st = JMA_STATIONS[key]
    frames, today = [], dt.date.today()
    for year in range(YEAR_START, YEAR_END + 1):
        for month in range(1, 13):
            if dt.date(year, month, 1) > today:
                break
            print(f"  {st['name']} {year}-{month:02d} ...", flush=True)
            frames.append(fetch_month(st["prec_no"], st["block_no"], year, month))
            time.sleep(REQUEST_INTERVAL_SEC)
    return pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)


def main(argv: list[str]) -> int:
    global P1_ONLY
    args = [a for a in argv[1:] if a != "--p1only"]
    P1_ONLY = "--p1only" in argv
    keys = args or list(JMA_STATIONS)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for key in keys:
        if key not in JMA_STATIONS:
            print(f"未知の地点キー: {key}（{list(JMA_STATIONS)}）", file=sys.stderr)
            continue
        print(f"[{key}] {JMA_STATIONS[key]['name']} を取得")
        df = fetch_station(key)
        out = DATA_DIR / f"jma_daily_{key}.csv"
        df.to_csv(out, index=False)
        miss = {c: int(df[c].isna().sum()) for c in ("precip_mm", "tmax_c", "sunshine_h", "solar_mj")}
        print(f"  -> {out}  ({len(df)}日, 欠測 {miss})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
