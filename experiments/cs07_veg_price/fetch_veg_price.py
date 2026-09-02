"""野菜卸売価格の時系列を用意する。

出力: data/cs07/veg_price.csv  （列: date, price）  price は円/kg（「総計」行の単価）

バックエンド（config.PRICE_BACKEND）:
- "vegetan_auto": ベジ探（農畜産業振興機構）を自動取得。鍵不要。
      1回のリクエスト = 1か月。VEG_YEAR_START〜VEG_YEAR_END の各月をループ取得。
      日別データは 2024年〜（それ以前は農水省「青果物卸売市場調査（日別調査）」を参照）。
- "manual": data/cs07/ に手で置いたファイルを読む。
      veg_price_manual.csv（列 date,price） か、ベジ探エクスポート SCH*.csv（複数可）。
- "estat": e-Stat API（要 ESTAT_APP_ID と config.STATS_DATA_ID）。

ベジ探の取得手順（自動）:
  GET  sch7.do?outPutKbn=4            … セッション確立（JSESSIONID）
  POST sch7.do CMD=search ...         … サーバ側セッションに検索条件を積む
  GET  sch7.do?CMD=downLoad&sv...=... … CSV（cp932）。sv* は空でも JS と同じ全項目を渡すこと（欠けると404）
"""

from __future__ import annotations

import csv
import glob
import io
import json
import os
import re
import time
import datetime as dt

import pandas as pd
import requests

from config import (DATA_DIR, PRICE_BACKEND, STATS_DATA_ID, ITEM_SLUG,
                    VEG_YEAR_START, VEG_YEAR_END,
                    VEGETAN_CITY, VEGETAN_ITEM_RUIBETU, VEGETAN_ITEM_CODE,
                    VEG_MONTHLY_YEAR_START, VEG_MONTHLY_YEAR_END,
                    VEGETAN_MARKET_MONTHLY, VEGETAN_RUIBETU_MONTHLY, VEGETAN_CODE_MONTHLY)

ESTAT_ENDPOINT = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
VEGETAN_BASE = "https://vegetan.alic.go.jp/vegetan/sch7.do"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
REQUEST_INTERVAL_SEC = 1.5


# ---------------------------------------------------------------- ベジ探 CSV パース
def _parse_vegetan_text(text: str, path_hint: str = "") -> pd.DataFrame:
    """ベジ探の入荷量・単価CSV（1ファイル=1か月）から (date, price) を作る。

      row0: [... , "YYYY年M月 東京都 レタス"]
      row1: [注記, "1日","", "2日","", ...]           ← 各ペアの前列に日付ラベル
      row2: ["産地","数量","単価","数量","単価", ...]  ← 単価列の位置
      row3: ["総計", 数量, 単価, ...]                   ← これを採用
    """
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or "卸売市場別入荷量" not in "".join(rows[0]):
        raise ValueError(f"ベジ探形式でない: {path_hint or text[:40]!r}")
    joined = "".join(rows[0])
    ym = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", joined)   # 日別/旬別: "YYYY年M月 ..."
    if ym:
        year, month = int(ym.group(1)), int(ym.group(2))
    else:                                                       # 月別: "YYYY年 ..." のみ
        y = re.search(r"(\d{4})\s*年", joined)
        if not y:
            raise ValueError(f"年を読めない: {rows[0]}")
        year, month = int(y.group(1)), None

    label_row, kind_row = rows[1], rows[2]
    total_row = next((r for r in rows if r and r[0].strip() in ("総計", "合計")), None)
    if total_row is None:
        return pd.DataFrame(columns=["date", "price"])  # データ無しの月

    recs = []
    for i, kind in enumerate(kind_row):
        if kind.strip() != "単価":
            continue
        label = label_row[i - 1] if 0 < i <= len(label_row) else ""
        dm, mm = re.search(r"(\d{1,2})\s*日", label), re.search(r"(\d{1,2})\s*月", label)
        if dm and month:
            day, mon = int(dm.group(1)), month
        elif mm:
            day, mon = 15, int(mm.group(1))
        else:
            continue
        if i >= len(total_row):
            break
        val = total_row[i].strip().replace(",", "")
        if not val:
            continue
        try:
            recs.append((dt.date(year, mon, day), float(val)))
        except ValueError:
            pass
    return pd.DataFrame(recs, columns=["date", "price"])


def _read_text_any(path: str) -> str:
    for enc in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return open(path, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"{path} の文字コードを判定できない。")


# ---------------------------------------------------------------- ベジ探 自動取得
def _fetch_vegetan_month(sess: requests.Session, year: int, month: int) -> pd.DataFrame:
    sess.post(VEGETAN_BASE, timeout=30, headers={"Referer": VEGETAN_BASE}, data={
        "CMD": "search", "searchFlg": "0", "outPutKbn": "4",
        "baseYear": str(year), "baseMonthFr": str(month),
        "city": VEGETAN_CITY, "hinmokuRuibetu": VEGETAN_ITEM_RUIBETU,
        "hinmokuCode": VEGETAN_ITEM_CODE,
    })
    # JS が組む順で全 sv* を渡す（空でも必須。欠けると 404）
    qs = (f"CMD=downLoad&searchFlg=1&outPutKbn=4"
          f"&svBaseYear={year}&svBaseYearTo=&svBaseMonthFr={month}&svBaseMonthTo="
          f"&svCodeKbn=&svHinmokuRuibetu={VEGETAN_ITEM_RUIBETU}&svHinmokuCode={VEGETAN_ITEM_CODE}"
          f"&svMarketCode=&svHomeCode=&svNendo1=&svNendo2=&svNendo3=&svNendo4="
          f"&svCity={VEGETAN_CITY}")
    d = sess.get(f"{VEGETAN_BASE}?{qs}", timeout=30, headers={"Referer": VEGETAN_BASE})
    d.raise_for_status()
    if "octet-stream" not in d.headers.get("content-type", "") and "csv" not in d.headers.get("content-type", ""):
        raise RuntimeError(f"{year}-{month:02d}: CSVが返らない（{d.status_code} {d.headers.get('content-type')}）")
    return _parse_vegetan_text(d.content.decode("cp932", errors="replace"), f"{year}-{month:02d}")


def _fetch_vegetan_year_monthly(sess: requests.Session, year: int) -> pd.DataFrame:
    """ベジ探 月別（outPutKbn=1）を1年分。産地=総計行の月次単価を返す。"""
    sess.post(VEGETAN_BASE, timeout=30, headers={"Referer": VEGETAN_BASE}, data={
        "CMD": "search", "searchFlg": "0", "outPutKbn": "1",
        "baseYear": str(year), "baseYearTo": str(year),
        "baseMonthFr": "1", "baseMonthTo": "12",
        "marketCode": VEGETAN_MARKET_MONTHLY, "codeKbn": "1",
        "hinmokuRuibetu": VEGETAN_RUIBETU_MONTHLY, "hinmokuCode": VEGETAN_CODE_MONTHLY,
    })
    qs = (f"CMD=downLoad&searchFlg=1&outPutKbn=1"
          f"&svBaseYear={year}&svBaseYearTo={year}&svBaseMonthFr=1&svBaseMonthTo=12"
          f"&svCodeKbn=1&svHinmokuRuibetu={VEGETAN_RUIBETU_MONTHLY}&svHinmokuCode={VEGETAN_CODE_MONTHLY}"
          f"&svMarketCode={VEGETAN_MARKET_MONTHLY}&svHomeCode="
          f"&svNendo1=&svNendo2=&svNendo3=&svNendo4=&svCity=")
    d = sess.get(f"{VEGETAN_BASE}?{qs}", timeout=30, headers={"Referer": VEGETAN_BASE})
    d.raise_for_status()
    if "octet-stream" not in d.headers.get("content-type", "") and "csv" not in d.headers.get("content-type", ""):
        raise RuntimeError(f"{year}: CSVが返らない（{d.status_code} {d.headers.get('content-type')}）")
    return _parse_vegetan_text(d.content.decode("cp932", errors="replace"), str(year))


def _fetch_vegetan_monthly() -> pd.DataFrame:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    sess.get(VEGETAN_BASE, params={"outPutKbn": "1"}, timeout=30)
    frames = []
    for year in range(VEG_MONTHLY_YEAR_START, VEG_MONTHLY_YEAR_END + 1):
        try:
            df = _fetch_vegetan_year_monthly(sess, year)
        except (requests.HTTPError, RuntimeError) as e:
            print(f"  ベジ探(月別) {year}: スキップ（{type(e).__name__}）")
            continue
        print(f"  ベジ探(月別) {year}: {len(df)}点")
        frames.append(df)
        time.sleep(REQUEST_INTERVAL_SEC)
    out = (pd.concat(frames, ignore_index=True).drop_duplicates("date")
           .sort_values("date").reset_index(drop=True))
    if out.empty:
        raise SystemExit("ベジ探(月別)から1点も取れなかった。")
    return out


def _fetch_vegetan_auto() -> pd.DataFrame:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    sess.get(VEGETAN_BASE, params={"outPutKbn": "4"}, timeout=30)  # JSESSIONID
    frames = []
    today = dt.date.today()
    for year in range(VEG_YEAR_START, VEG_YEAR_END + 1):
        for month in range(1, 13):
            if dt.date(year, month, 1) > today:
                break
            try:
                df = _fetch_vegetan_month(sess, year, month)
            except (requests.HTTPError, RuntimeError) as e:
                print(f"  ベジ探 {year}-{month:02d}: スキップ（{type(e).__name__}: データ未提供か）")
                continue
            print(f"  ベジ探 {year}-{month:02d}: {len(df)}点")
            frames.append(df)
            time.sleep(REQUEST_INTERVAL_SEC)
    out = (pd.concat(frames, ignore_index=True)
           .drop_duplicates("date").sort_values("date").reset_index(drop=True))
    if out.empty:
        raise SystemExit("ベジ探から1点も取れなかった。コード（city/hinmoku）と期間を確認。")
    return out


# ---------------------------------------------------------------- 手動ファイル
def _read_plain_csv() -> pd.DataFrame | None:
    src = DATA_DIR / "veg_price_manual.csv"
    if not src.exists():
        return None
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            raw = pd.read_csv(src, encoding=enc)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            raw = None
    if raw is None:
        raise SystemExit(f"{src} を読めない。")
    raw = raw.rename(columns={c: str(c).strip() for c in raw.columns})
    low = {c.lower(): c for c in raw.columns}
    dcol = next((low[k] for k in low if k in ("date", "日付", "年月日", "調査日", "月日")), None) \
        or next((c for c in raw.columns if "日" in c or "年月" in c), None)
    pcol = next((low[k] for k in low if k in ("price", "価格", "卸売価格", "平均価格", "単価", "円/kg")), None) \
        or next((c for c in raw.columns if "価格" in c or "単価" in c), None)
    if not dcol or not pcol:
        raise SystemExit(f"date/price 列を特定できない: {list(raw.columns)}")
    df = raw[[dcol, pcol]].copy()
    df.columns = ["date", "price"]
    df["date"] = pd.to_datetime(df["date"].astype(str).str.replace("/", "-"), errors="coerce")
    df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "").str.replace("円", "").str.strip(),
                                errors="coerce")
    return df.dropna().sort_values("date").reset_index(drop=True)


def _read_vegetan_glob() -> pd.DataFrame | None:
    files = sorted(set(glob.glob(str(DATA_DIR / "SCH*.csv")) + glob.glob(str(DATA_DIR / "sch*.csv"))))
    if not files:
        return None
    frames = []
    for f in files:
        df = _parse_vegetan_text(_read_text_any(f), os.path.basename(f))
        print(f"  {os.path.basename(f)}: {len(df)}点")
        frames.append(df)
    return (pd.concat(frames, ignore_index=True)
            .drop_duplicates("date").sort_values("date").reset_index(drop=True))


def _read_manual() -> pd.DataFrame:
    df = _read_plain_csv()
    if df is None:
        df = _read_vegetan_glob()
    if df is None:
        raise SystemExit(
            f"{DATA_DIR} に価格ファイルが無い。veg_price_manual.csv か SCH*.csv を置くか、"
            "PRICE_BACKEND='vegetan_auto' にする。")
    return df


# ---------------------------------------------------------------- e-Stat
def _read_estat() -> pd.DataFrame:
    app_id = os.environ.get("ESTAT_APP_ID", "").strip()
    if not app_id or not STATS_DATA_ID:
        raise SystemExit("e-Stat には ESTAT_APP_ID と config.STATS_DATA_ID が必要。")
    r = requests.get(ESTAT_ENDPOINT, timeout=60,
                     params={"appId": app_id, "statsDataId": STATS_DATA_ID, "lang": "J", "metaGetFlg": "Y"})
    r.raise_for_status()
    js = r.json()
    (DATA_DIR / "estat_raw.json").write_text(json.dumps(js, ensure_ascii=False, indent=1))
    try:
        val = js["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    except KeyError:
        raise SystemExit("e-Stat 応答に VALUE が無い。estat_raw.json を確認。")
    df = pd.DataFrame(val if isinstance(val, list) else [val])
    t = df["@time"].astype(str).str.replace(r"0000$", "", regex=True)
    df["date"] = pd.to_datetime(t.str.slice(0, 8), format="%Y%m%d", errors="coerce")
    df["date"] = df["date"].fillna(pd.to_datetime(t.str.slice(0, 6), format="%Y%m", errors="coerce"))
    df["price"] = pd.to_numeric(df["$"], errors="coerce")
    out = df[["date", "price"]].dropna().sort_values("date").reset_index(drop=True)
    if out.empty:
        print(json.dumps(js["GET_STATS_DATA"]["STATISTICAL_DATA"].get("CLASS_INF", {}),
                         ensure_ascii=False, indent=1)[:4000])
        raise SystemExit("VALUE を (date,price) に落とせなかった。CLASS_INF を確認。")
    return out


# ----------------------------------------------------------------
def main() -> int:
    import sys
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if "--monthly" in sys.argv:      # ベジ探 月別（長期系列）
        df = _fetch_vegetan_monthly()
        suffix = "_monthly"
    else:
        backend = {"vegetan_auto": _fetch_vegetan_auto, "manual": _read_manual, "estat": _read_estat}
        if PRICE_BACKEND not in backend:
            raise SystemExit(f"PRICE_BACKEND が不正: {PRICE_BACKEND}")
        df = backend[PRICE_BACKEND]()
        suffix = ""
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["date", "price"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    if df.empty:
        raise SystemExit("有効な価格データが0件。")
    out = DATA_DIR / f"veg_price_{ITEM_SLUG}{suffix}.csv"
    df.to_csv(out, index=False)
    span = df["date"].diff().dt.days.median()
    print(f"-> {out}  ({len(df)}点, {df['date'].min().date()}〜{df['date'].max().date()}, 中央間隔~{span:.0f}日)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
