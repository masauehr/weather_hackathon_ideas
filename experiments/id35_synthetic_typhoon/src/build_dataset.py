"""台風ごとの中心気圧の時系列を、ライフサイクル基準（発生0%〜消滅100%）で
固定長（N_POINTS点）にリサンプリングし、生成モデルの学習データにまとめる。

- 中心気圧は全期間（1951〜）で記録されているため全台風を対象にする（生成対象）。
- 最大風速は台風強度（TS〜TY）の期間のみ記録され、発生直後(TD)や温帯低気圧化後(L)
  では欠測になる（実データで確認）。時系列としては使わず、台風ごとの
  「記録されている中での最大風速（peak_wind_kt）」という1台風1値のスカラーとして
  持つ（気圧-風速関係の妥当性チェックで使う。1977年以降のみ記録あり）。
- 観測点が少なすぎる台風（N_POINTS未満）は補間の意味が薄いため除外する。
"""
from pathlib import Path

import numpy as np
import pandas as pd

from fetch_besttrack import fetch_and_parse, PROCESSED_DIR

N_POINTS = 20
MIN_OBS = 8


def resample_lifecycle(values: np.ndarray, n_points: int = N_POINTS) -> np.ndarray:
    """観測点数が可変の時系列を、ライフサイクル比率(0〜1)基準でn_points点に線形補間する。"""
    t_src = np.linspace(0.0, 1.0, len(values))
    t_dst = np.linspace(0.0, 1.0, n_points)
    return np.interp(t_dst, t_src, values)


def build(min_year: int = 1951) -> pd.DataFrame:
    """台風ID毎に (pressure_0..pressure_{N-1}, wind_0..wind_{N-1}, peak_wind_pressure等) の
    1行にまとめたDataFrameを返す。"""
    df = fetch_and_parse()
    df = df[df["datetime"].dt.year >= min_year].copy()

    rows = []
    for tid, g in df.groupby("international_id"):
        g = g.sort_values("datetime")
        if len(g) < MIN_OBS:
            continue
        pressure = g["pressure"].to_numpy(dtype=float)
        pressure_seq = resample_lifecycle(pressure)

        wind = g["max_wind"].to_numpy(dtype=float)
        has_wind = np.isfinite(wind).any()
        peak_wind_kt = np.nanmax(wind) if has_wind else np.nan

        row = {
            "international_id": tid,
            "name": g["name"].iloc[0],
            "year": g["datetime"].dt.year.iloc[0],
            "n_obs": len(g),
            "min_pressure": pressure.min(),
            "peak_wind_kt": peak_wind_kt,
            "has_wind": has_wind,
        }
        for i in range(N_POINTS):
            row[f"pressure_{i}"] = pressure_seq[i]
        rows.append(row)

    return pd.DataFrame.from_records(rows)


if __name__ == "__main__":
    out = build()
    out_path = PROCESSED_DIR / "typhoon_sequences.csv"
    out.to_csv(out_path, index=False)
    n_with_wind = out["has_wind"].sum()
    print(f"台風数: {len(out)}（うち風速データあり: {n_with_wind}）")
    print(f"最低気圧の分布: min={out['min_pressure'].min()}, "
          f"median={out['min_pressure'].median()}, max={out['min_pressure'].max()}")
    print(f"保存先: {out_path}")
