"""気象庁RSMC東京 台風ベストトラックデータ（テキスト形式）の取得・パース。

出典: 気象庁 RSMC東京－台風センター
      https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/besttrack.html

グローバルCLAUDE.mdの禁止事項により curl / wget は使わず、Pythonの requests を使う。
フォーマットは typhoon_track_dl/src/parse.py と同じ（既存資産のコードを参考に、
本スパイクでは自前で再取得・再パースする。データは気象庁の公開データ）。
"""
from pathlib import Path
import zipfile

import pandas as pd
import requests

BEST_TRACK_ALL_URL = (
    "https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/"
    "Besttracks/bst_all.zip"
)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

GRADE_LABELS = {
    2: "TD",
    3: "TS",
    4: "STS",
    5: "TY",
    6: "L",
    7: "ENTERING",
    9: "TS_OR_ABOVE",
}


def download(dest_dir: Path = RAW_DIR) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "bst_all.zip"
    resp = requests.get(BEST_TRACK_ALL_URL, timeout=30)
    resp.raise_for_status()
    zip_path.write_bytes(resp.content)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
        names = zf.namelist()
    return dest_dir / names[0]


def _year_from_2digit(yy: int) -> int:
    return 1900 + yy if yy >= 51 else 2000 + yy


def parse(path: Path) -> pd.DataFrame:
    """固定長テキストを観測点単位のDataFrameに変換する。

    columns: international_id, name, datetime, grade, grade_label,
             lat, lon, pressure, max_wind
    """
    records = []
    current_id = None
    current_name = None
    with open(path, encoding="ascii") as f:
        for line in f:
            if line.startswith("66666"):
                current_id = line[6:10].strip()
                current_name = line[30:50].strip()
                continue
            yy = int(line[0:2])
            mm = int(line[2:4])
            dd = int(line[4:6])
            hh = int(line[6:8])
            grade = int(line[13:14])
            lat = int(line[15:18]) / 10.0
            lon = int(line[19:23]) / 10.0
            pressure = int(line[24:28])
            wind_field = line[33:36].strip()
            max_wind = int(wind_field) if wind_field else None
            if max_wind == 0:
                max_wind = None
            year = _year_from_2digit(yy)
            records.append(
                {
                    "international_id": current_id,
                    "name": current_name,
                    "datetime": pd.Timestamp(year, mm, dd, hh),
                    "grade": grade,
                    "grade_label": GRADE_LABELS.get(grade, "UNKNOWN"),
                    "lat": lat,
                    "lon": lon,
                    "pressure": pressure,
                    "max_wind": max_wind,
                }
            )
    return pd.DataFrame.from_records(records)


def fetch_and_parse() -> pd.DataFrame:
    """既に取得済みならダウンロードを省略してパース済みCSVを返す。"""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED_DIR / "best_track.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["datetime"])

    raw_files = list(RAW_DIR.glob("bst_all.txt"))
    txt_path = raw_files[0] if raw_files else download()
    df = parse(txt_path)
    df.to_csv(csv_path, index=False)
    return df


if __name__ == "__main__":
    df = fetch_and_parse()
    print(f"観測点数: {len(df)}, 台風数: {df['international_id'].nunique()}")
    print(f"期間: {df['datetime'].min()} 〜 {df['datetime'].max()}")
