"""気象庁「過去の気象データ検索」(etrn) daily_s1.php から日照時間だけを取得する。

cs07_veg_price/fetch_jma_daily.py の p1 ビュー取得パターンを流用（日射量a3は今回不要のため省略）。
出典: 気象庁ホームページ https://www.data.jma.go.jp/stats/etrn/
"""
import datetime as dt
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ETRN_URL = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php"
REQUEST_INTERVAL_SEC = 1.0
IDX_SUNSHINE = 16  # daily_s1.php p1ビューの日照時間列（cs07_veg_priceで実測確認済み）

STATIONS = {
    "fukuoka": {"prec_no": 82, "block_no": "47807", "name": "福岡（九州エリアの代表点）"},
    "naha": {"prec_no": 91, "block_no": "47936", "name": "那覇（沖縄エリアの代表点）"},
}

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "data" / "processed"


def fetch_month(prec_no: int, block_no: str, year: int, month: int) -> pd.DataFrame:
    r = requests.get(ETRN_URL, timeout=30, params={
        "prec_no": prec_no, "block_no": block_no,
        "year": year, "month": month, "day": "", "view": "p1"})
    r.raise_for_status()
    r.encoding = "shift_jis"
    table = BeautifulSoup(r.text, "html.parser").find("table", id="tablefix1")
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells or not cells[0].get_text(strip=True).isdigit():
            continue
        day = int(cells[0].get_text(strip=True))
        vals = [c.get_text(strip=True) for c in cells]
        raw = vals[IDX_SUNSHINE] if IDX_SUNSHINE < len(vals) else ""
        s = raw.strip().replace(")", "").replace("]", "")
        sunshine_h = 0.0 if s == "--" else (float(s) if s not in ("", "×", "///", "#") else float("nan"))
        rows.append({"date": dt.date(year, month, day), "sunshine_h": sunshine_h})
    return pd.DataFrame(rows)


def fetch_station(key: str, year_start: int, month_start: int, year_end: int, month_end: int) -> pd.DataFrame:
    st = STATIONS[key]
    frames, today = [], dt.date.today()
    y, m = year_start, month_start
    while (y, m) <= (year_end, month_end):
        if dt.date(y, m, 1) > today:
            break
        print(f"  {st['name']} {y}-{m:02d} ...", flush=True)
        frames.append(fetch_month(st["prec_no"], st["block_no"], y, m))
        time.sleep(REQUEST_INTERVAL_SEC)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)


def main():
    df = fetch_station("fukuoka", 2018, 10, 2026, 3)
    df.to_csv(OUT_DIR / "sunshine_fukuoka.csv", index=False)
    print(f"福岡: {len(df)}日分 → {OUT_DIR / 'sunshine_fukuoka.csv'}")

    df2 = fetch_station("naha", 2022, 4, 2026, 3)
    df2.to_csv(OUT_DIR / "sunshine_naha.csv", index=False)
    print(f"那覇: {len(df2)}日分 → {OUT_DIR / 'sunshine_naha.csv'}")


if __name__ == "__main__":
    sys.exit(main())
