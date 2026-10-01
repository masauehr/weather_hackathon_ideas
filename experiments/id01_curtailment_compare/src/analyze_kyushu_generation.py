"""九州電力送配電の実際の発電量（エリア風力・太陽光発電量、日次合計）と、気象データ
（実測の日照時間・全天日射量、および各種予報手法のシミュレーション値）の相関を検証する。

注意: 発電量は「出力制御後」の値であり、かつ風力・太陽光の合計（九州は太陽光が主体と
推測されるが厳密には混在）。制御が発生した日は「天気が良いのに発電量が増えない/落ちる」
という逆転が起きるため、相関を見る際は制御日と非制御日を分けて確認する。
"""
from pathlib import Path

import numpy as np
import pandas as pd

from logistic_model import build_dataset
from backtest_kyushu_forecast_methods import build_backtest_dataset

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def main():
    gen = pd.read_csv(PROCESSED_DIR / "kyushu_wind_solar_daily.csv", parse_dates=["date"])
    gen["wind_solar_mwh"] = gen["wind_solar_kwh"] / 1000

    solar_mj = pd.read_csv(PROCESSED_DIR / "solar_fukuoka.csv", parse_dates=["date"])
    backtest = build_backtest_dataset()  # sunshine_h(実測) / amgsds_proxy_h / simplified_h / is_curtailed

    df = gen.merge(backtest, on="date", how="inner").merge(solar_mj, on="date", how="inner")
    print(f"比較対象: {len(df)}日（{df['date'].min().date()} 〜 {df['date'].max().date()}）\n")

    print("=== 実際の発電量[MWh]との相関（全日） ===")
    for col, name in [("sunshine_h", "実測日照時間"), ("solar_mj", "実測全天日射量"),
                       ("amgsds_proxy_h", "AMGSDS風(快晴バイアス補正)"), ("simplified_h", "簡略化")]:
        r = df["wind_solar_mwh"].corr(df[col])
        print(f"  {name:28s} r={r:.3f}")

    print("\n=== 非制御日のみでの相関（出力制御による頭打ちを除く） ===")
    non_curtailed = df[~df["is_curtailed"]]
    print(f"  (n={len(non_curtailed)})")
    for col, name in [("sunshine_h", "実測日照時間"), ("solar_mj", "実測全天日射量"),
                       ("amgsds_proxy_h", "AMGSDS風(快晴バイアス補正)"), ("simplified_h", "簡略化")]:
        r = non_curtailed["wind_solar_mwh"].corr(non_curtailed[col])
        print(f"  {name:28s} r={r:.3f}")

    print("\n=== 制御日 vs 非制御日の発電量レベル（天気が同程度でも制御で頭打ちになるか） ===")
    clear_days = df[df["weather_class"].isin(["快晴", "晴れ"])]
    for label, sub in [("快晴/晴れ×制御日", clear_days[clear_days["is_curtailed"]]),
                        ("快晴/晴れ×非制御日", clear_days[~clear_days["is_curtailed"]])]:
        print(f"  {label}: n={len(sub)}  発電量平均={sub['wind_solar_mwh'].mean():.1f}MWh  "
              f"実測日照時間平均={sub['sunshine_h'].mean():.2f}h")

    out_path = PROCESSED_DIR / "kyushu_generation_merged.csv"
    df.to_csv(out_path, index=False)
    print(f"\n保存先: {out_path}")


if __name__ == "__main__":
    main()
