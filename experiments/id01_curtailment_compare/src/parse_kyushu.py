"""九州電力送配電「過去の出力制御実績＿九州本土」Excelから、出力制御が実施された日付を抽出する。

シート構成（年度ごとに1シート、レイアウトは年度によって3パターンある。実測で確認）:
- 「通し番号」の行（2018年度=9行目、2019〜2022年度=10行目、2023〜2025年度=8行目）を探し、
  その3行下が「再エネ出力制御期間」（実際に制御された日付）の行という関係は全年度で共通。
- 日付の値は、新しい年度はdatetime型、古い年度は "10/13（土）" のような文字列（曜日付き）。
  文字列の場合は年度の開始年（4月始まり）から実際の暦年を推定してパースする。
- 「出力制御なし」等のテキストはスキップ（制御が実施されなかったケース）。
"""
import re
from pathlib import Path

import openpyxl
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "raw" / "kyushu_curtail_history.xlsx"
OUT_PATH = BASE_DIR / "data" / "processed" / "kyushu_curtail_days.csv"

DATE_STR_RE = re.compile(r"^(\d{1,2})/(\d{1,2})")


def fiscal_start_year(sheet_name: str) -> int:
    return int(re.match(r"(\d{4})", sheet_name).group(1))


def find_seq_row(ws, max_row: int = 15) -> int:
    for r in range(1, max_row + 1):
        for c in range(1, 6):
            v = ws.cell(row=r, column=c).value
            if isinstance(v, str) and "通し番号" in v:
                return r
    raise ValueError("「通し番号」の行が見つからない")


def parse_date_cell(val, fy_start_year: int):
    if hasattr(val, "date"):
        return val.date()
    if isinstance(val, str):
        m = DATE_STR_RE.match(val.strip())
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            year = fy_start_year if month >= 4 else fy_start_year + 1
            try:
                return pd.Timestamp(year, month, day).date()
            except ValueError:
                return None
    return None


def extract_sheet(ws, fy_start_year: int) -> list:
    """1つの年度シートから、制御が実施された日付のリストを返す。"""
    seq_row = find_seq_row(ws)
    period_row = seq_row + 3
    seq_cols = [c for c in range(1, ws.max_column + 1) if isinstance(ws.cell(row=seq_row, column=c).value, int)]
    dates = []
    for c in seq_cols:
        d = parse_date_cell(ws.cell(row=period_row, column=c).value, fy_start_year)
        if d:
            dates.append(d)
    return dates


def main():
    wb = openpyxl.load_workbook(RAW_PATH, data_only=True)
    rows = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        dates = extract_sheet(ws, fiscal_start_year(sheet_name))
        for d in sorted(set(dates)):
            rows.append({"fiscal_year_sheet": sheet_name, "date": d})
        print(f"{sheet_name}: 制御日 {len(set(dates))}日")

    df = pd.DataFrame(rows).sort_values("date")
    df.to_csv(OUT_PATH, index=False)
    print(f"\n合計 制御日数: {len(df)}日（{df['date'].min()} 〜 {df['date'].max()}）")
    print(f"保存先: {OUT_PATH}")


if __name__ == "__main__":
    main()
