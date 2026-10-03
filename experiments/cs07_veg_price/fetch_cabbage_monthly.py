"""キャベツの月別 入荷量・単価（東京都中央市場計）を5年分取得する。

出力:
  data/cs07/vegetan_monthly_raw/cabbage_YYYY.csv  … ベジ探の生CSV（cp932のまま）
  data/cs07/veg_qty_cabbage_monthly.csv           … 列: date, qty_kg, price（総計行）

取得手順は fetch_veg_price.py と同じ（ベジ探 sch7.do, outPutKbn=1 月別）:
  GET  sch7.do?outPutKbn=1              … セッション確立
  POST sch7.do CMD=search ...           … 検索条件をセッションに積む
  GET  sch7.do?CMD=downLoad&sv*=...     … CSV（sv* は空でも全項目必須）
1リクエスト=1年。リクエスト間隔 REQUEST_INTERVAL_SEC を必ず空ける（サーバー負荷配慮）。

使い方: python fetch_cabbage_monthly.py [開始年] [終了年]   （既定 2021 2025）
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import sys
import time

import pandas as pd
import requests

from config import DATA_DIR

VEGETAN_BASE = "https://vegetan.alic.go.jp/vegetan/sch7.do"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
REQUEST_INTERVAL_SEC = 3.0

MARKET = "7"            # 東京都中央市場計
RUIBETU = "9999020"     # 葉茎菜類
ITEM_CODE = "317000"    # キャベツ（市場品目）
RAW_DIR = DATA_DIR / "vegetan_monthly_raw"


def _fetch_year(sess: requests.Session, year: int) -> str:
    sess.post(VEGETAN_BASE, timeout=30, headers={"Referer": VEGETAN_BASE}, data={
        "CMD": "search", "searchFlg": "0", "outPutKbn": "1",
        "baseYear": str(year), "baseYearTo": str(year),
        "baseMonthFr": "1", "baseMonthTo": "12",
        "marketCode": MARKET, "codeKbn": "1",
        "hinmokuRuibetu": RUIBETU, "hinmokuCode": ITEM_CODE,
    })
    qs = (f"CMD=downLoad&searchFlg=1&outPutKbn=1"
          f"&svBaseYear={year}&svBaseYearTo={year}&svBaseMonthFr=1&svBaseMonthTo=12"
          f"&svCodeKbn=1&svHinmokuRuibetu={RUIBETU}&svHinmokuCode={ITEM_CODE}"
          f"&svMarketCode={MARKET}&svHomeCode="
          f"&svNendo1=&svNendo2=&svNendo3=&svNendo4=&svCity=")
    d = sess.get(f"{VEGETAN_BASE}?{qs}", timeout=30, headers={"Referer": VEGETAN_BASE})
    d.raise_for_status()
    ctype = d.headers.get("content-type", "")
    if "octet-stream" not in ctype and "csv" not in ctype:
        raise RuntimeError(f"{year}: CSVが返らない（{d.status_code} {ctype}）")
    (RAW_DIR / f"cabbage_{year}.csv").write_bytes(d.content)
    return d.content.decode("cp932", errors="replace")


def _parse(text: str, year: int) -> pd.DataFrame:
    """総計行から月ごとの (数量, 単価) を取り出す。"""
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or "卸売市場別入荷量" not in "".join(rows[0]):
        raise ValueError(f"ベジ探形式でない: {year}")
    label_row, kind_row = rows[1], rows[2]
    total = next((r for r in rows if r and r[0].strip() == "総計"), None)
    if total is None:
        return pd.DataFrame(columns=["date", "qty_kg", "price"])
    recs = []
    for i, kind in enumerate(kind_row):
        if kind.strip() != "数量" or i >= len(label_row):
            continue
        label = label_row[i]
        if not label.endswith("月"):    # 「年計」列は除外
            continue
        month = int(label.rstrip("月"))
        qty = total[i].strip().replace(",", "") if i < len(total) else ""
        price = total[i + 1].strip().replace(",", "") if i + 1 < len(total) else ""
        if not qty:
            continue
        recs.append((dt.date(year, month, 1), float(qty), float(price) if price else None))
    return pd.DataFrame(recs, columns=["date", "qty_kg", "price"])


def main() -> int:
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2021
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    sess.get(VEGETAN_BASE, params={"outPutKbn": "1"}, timeout=30)
    frames = []
    for year in range(y0, y1 + 1):
        df = _parse(_fetch_year(sess, year), year)
        print(f"  ベジ探(月別) キャベツ {year}: {len(df)}か月")
        frames.append(df)
        if year < y1:
            time.sleep(REQUEST_INTERVAL_SEC)
    out = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    dst = DATA_DIR / "veg_qty_cabbage_monthly.csv"
    out.to_csv(dst, index=False)
    print(f"-> {dst}  ({len(out)}点, {out['date'].min()}〜{out['date'].max()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
