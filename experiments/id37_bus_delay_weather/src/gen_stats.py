"""bus_delay_log.csvから集計統計を作り、GitHub Pagesの監視ページ用stats.jsonに書き出す。

このstats.json自体は小さい(数KB)ため、生データ(data/、git除外)とは別にdocs/配下へ
コミット・pushして公開する想定（publish_stats.shが30分おきに実行）。
"""
import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BASE_DIR / "data" / "processed" / "bus_delay_log.csv"
OLD_LOG_PATH = BASE_DIR / "data" / "processed" / "bus_delay_log_before_weather.csv"
DOCS_DIR = BASE_DIR / "docs"
STATS_PATH = DOCS_DIR / "stats.json"


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    if not LOG_PATH.exists():
        stats = {"generated_at": pd.Timestamp.now().isoformat(), "total_observations": 0,
                 "note": "まだ観測データが無い"}
        STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
        print("観測データが無いため空のstats.jsonを作成")
        return

    df = pd.read_csv(LOG_PATH, parse_dates=["polled_at"])

    # 天気情報付与前(旧スキーマ)の累積件数も参考値として合算する
    old_count = 0
    if OLD_LOG_PATH.exists():
        old_count = sum(1 for _ in open(OLD_LOG_PATH)) - 1

    daily = (df.assign(date=df["polled_at"].dt.date)
               .groupby("date")
               .agg(n=("delay_seconds", "size"),
                    mean_delay=("delay_seconds", "mean"),
                    n_rain=("precipitation10m_mm", lambda s: (s.fillna(0) > 0).sum()))
               .reset_index())
    daily["date"] = daily["date"].astype(str)

    stats = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "total_observations": len(df) + old_count,
        "observations_with_weather": len(df),
        "observations_before_weather_tracking": old_count,
        "period_start": str(df["polled_at"].min()),
        "period_end": str(df["polled_at"].max()),
        "delay_seconds": {
            "mean": round(df["delay_seconds"].mean(), 1),
            "median": round(df["delay_seconds"].median(), 1),
            "max": round(df["delay_seconds"].max(), 1),
            "min": round(df["delay_seconds"].min(), 1),
        },
        "weather_coverage": {
            "rows_with_precipitation_data": int(df["precipitation10m_mm"].notna().sum()),
            "rows_total": len(df),
            "rows_with_rain_detected": int((df["precipitation10m_mm"].fillna(0) > 0).sum()),
        },
        "daily": daily.to_dict(orient="records"),
    }
    STATS_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"stats.json更新: 総観測数{stats['total_observations']}件, "
          f"期間{stats['period_start']}〜{stats['period_end']}")


if __name__ == "__main__":
    main()
