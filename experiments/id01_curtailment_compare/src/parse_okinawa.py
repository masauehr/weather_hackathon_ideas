"""沖縄電力「過去の出力制御指示内容」PDF（沖縄本島、年度別）から、出力制御が実施された日付を抽出する。

九州電力送配電のExcelと同じ形式の報告書だが、PDFのテーブル抽出（pdfplumber）で読む。
1ページに4件程度の「通し番号」ブロックがあり、
- 行0: 通し番号（奇数列インデックス 3,5,7,9... に値がある）
- 行2: 再エネ出力制御期間（"M月D日(曜)\n時刻" の文字列。「出力制御なし」なら制御なし）
という構造は九州と共通（実測で確認）。日付文字列は曜日付き・年が無いため、
ファイル名（年度）から暦年を推定してパースする。
"""
import re
from pathlib import Path

import pdfplumber
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_PATH = BASE_DIR / "data" / "processed" / "okinawa_curtail_days.csv"

DATE_STR_RE = re.compile(r"^(\d{1,2})月(\d{1,2})日")


def parse_date_cell(val, fy_start_year: int):
    if not val or "出力制御なし" in val:
        return None
    m = DATE_STR_RE.match(val.strip())
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    year = fy_start_year if month >= 4 else fy_start_year + 1
    try:
        return pd.Timestamp(year, month, day).date()
    except ValueError:
        return None


def extract_pdf(path: Path, fy_start_year: int) -> list:
    dates = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                seq_row_idx = next((i for i, row in enumerate(table)
                                     if row and row[0] == "通し番号"), None)
                if seq_row_idx is None:
                    continue
                period_row = table[seq_row_idx + 2]
                seq_row = table[seq_row_idx]
                seq_cols = [i for i, v in enumerate(seq_row) if v and v.strip().isdigit()]
                for c in seq_cols:
                    if c < len(period_row):
                        d = parse_date_cell(period_row[c], fy_start_year)
                        if d:
                            dates.append(d)
    return dates


def main():
    rows = []
    for path in sorted(RAW_DIR.glob("okinawa_previous_control_*.pdf")):
        fy = int(path.stem.rsplit("_", 1)[-1])
        dates = extract_pdf(path, fy)
        for d in sorted(set(dates)):
            rows.append({"fiscal_year": fy, "date": d})
        print(f"{fy}年度: 制御日 {len(set(dates))}日")

    df = pd.DataFrame(rows).sort_values("date")
    df.to_csv(OUT_PATH, index=False)
    print(f"\n合計 制御日数: {len(df)}日（{df['date'].min()} 〜 {df['date'].max()}）")
    print(f"保存先: {OUT_PATH}")


if __name__ == "__main__":
    main()
