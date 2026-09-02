"""CS-07 の GO/NO-GO 判定。

産地の週次日照（平年比）と、数週後の卸売価格（季節調整後）の相関を、
ラグ 0〜8 週で見る。仮説どおりなら ラグ2〜4週で「日照↓ → 価格↑」= 負の相関。

入力:
  data/cs07/jma_sunshine_<PRODUCER_STATION>.csv  (date, sunshine_h)
  data/cs07/veg_price.csv                        (date, price)
出力:
  experiments/cs07_veg_price/out/lag_corr.png
  experiments/cs07_veg_price/out/summary.txt
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from config import (DATA_DIR, OUT_DIR, PRODUCER_STATION, PRICE_ITEM, ITEM_SLUG,
                    LAG_WEEKS, GO_LAGS, GO_P)


def _week_start(s: pd.Series) -> pd.Series:
    """日付をその週（月曜始まり）の開始日に丸める。"""
    d = pd.to_datetime(s)
    return d - pd.to_timedelta(d.dt.weekday, unit="D")


def load_sunshine_weekly() -> pd.DataFrame:
    src = DATA_DIR / f"jma_sunshine_{PRODUCER_STATION}.csv"
    df = pd.read_csv(src, parse_dates=["date"])
    df["wk"] = _week_start(df["date"])
    g = df.groupby("wk").agg(sunshine_sum=("sunshine_h", "sum"),
                             n_days=("sunshine_h", "count"),
                             n_valid=("sunshine_h", lambda x: x.notna().sum()))
    g = g[g["n_valid"] >= 5].copy()  # 欠測が多い週は捨てる
    g["woy"] = g.index.isocalendar().week.astype(int).values
    clim = g.groupby("woy")["sunshine_sum"].transform("mean")
    g["sun_ratio"] = g["sunshine_sum"] / clim          # 平年比（1.0 が平年並み）
    g["sun_anom_z"] = (g["sunshine_sum"] - clim) / g.groupby("woy")["sunshine_sum"].transform("std")
    return g.reset_index()[["wk", "sun_ratio", "sun_anom_z"]]


def load_price_weekly() -> tuple[pd.DataFrame, str]:
    src = DATA_DIR / f"veg_price_{ITEM_SLUG}.csv"
    df = pd.read_csv(src, parse_dates=["date"]).dropna()
    df = df.sort_values("date")
    span_days = df["date"].diff().dt.days.median()
    df["wk"] = _week_start(df["date"])
    w = df.groupby("wk", as_index=False)["price"].mean()

    if span_days and span_days > 20:  # 月次データ → 週次へ補間
        full = pd.date_range(w["wk"].min(), w["wk"].max(), freq="W-MON")
        w = (w.set_index("wk").reindex(full).interpolate("time").rename_axis("wk").reset_index())
        note = f"価格は月次(中央間隔~{span_days:.0f}日)を週次に線形補間"
    else:
        note = f"価格は週次相当(中央間隔~{span_days:.0f}日)"

    # 季節調整: log価格 - 週番号ごとの平均log価格
    w["logp"] = np.log(w["price"])
    w["woy"] = w["wk"].dt.isocalendar().week.astype(int)
    w["logp_resid"] = w["logp"] - w.groupby("woy")["logp"].transform("mean")
    return w[["wk", "price", "logp_resid"]], note


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sun = load_sunshine_weekly()
    price, price_note = load_price_weekly()

    base = sun.merge(price, on="wk", how="inner").sort_values("wk").reset_index(drop=True)
    if len(base) < 30:
        print(f"重複期間の週数が少なすぎる（{len(base)}週）。期間を延ばすこと。", file=sys.stderr)

    rows = []
    for lag in LAG_WEEKS:
        x = base["sun_ratio"]
        y = base["logp_resid"].shift(-lag)      # lag週後の価格残差
        m = x.notna() & y.notna()
        if m.sum() < 20:
            rows.append((lag, np.nan, np.nan, int(m.sum())))
            continue
        rho, p = stats.spearmanr(x[m], y[m])
        rows.append((lag, rho, p, int(m.sum())))

    res = pd.DataFrame(rows, columns=["lag_weeks", "spearman_rho", "p_value", "n"])

    go_hits = res[(res["lag_weeks"].isin(GO_LAGS)) &
                  (res["p_value"] < GO_P) & (res["spearman_rho"] < 0)]
    verdict = "GO" if not go_hits.empty else "NO-GO"

    lines = [
        f"# CS-07 日照→卸売価格 ラグ相関  品目={PRICE_ITEM}  産地={PRODUCER_STATION}",
        f"重複週数={len(base)}  ({base['wk'].min().date()}〜{base['wk'].max().date()})",
        price_note,
        "",
        res.to_string(index=False, float_format=lambda v: f"{v:.3f}"),
        "",
        f"判定基準: ラグ {GO_LAGS} のいずれかで p<{GO_P} かつ ρ<0（日照↓→価格↑）",
        f"=> {verdict}",
    ]
    summary = "\n".join(lines)
    print(summary)
    (OUT_DIR / f"summary_{ITEM_SLUG}.txt").write_text(summary + "\n")

    # 図（ラベルは日本語フォント非依存のため ASCII）
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].bar(res["lag_weeks"], res["spearman_rho"],
              color=["#c0392b" if (l in GO_LAGS) else "#95a5a6" for l in res["lag_weeks"]])
    ax[0].axhline(0, color="k", lw=0.8)
    ax[0].set_xlabel("lag [weeks] (sunshine -> price)")
    ax[0].set_ylabel("Spearman rho")
    ax[0].set_title(f"lag correlation  verdict: {verdict}")

    ax2 = ax[1]
    ax2.plot(base["wk"], base["sun_ratio"], color="#f39c12", label="sunshine ratio-to-normal")
    ax2.set_ylabel("sunshine ratio", color="#f39c12")
    ax3 = ax2.twinx()
    ax3.plot(base["wk"], base["logp_resid"], color="#2980b9", label="price residual (log)")
    ax3.set_ylabel("price resid (log)", color="#2980b9")
    ax2.set_title(f"time series  item={PRICE_ITEM} producer={PRODUCER_STATION}  (src: JMA)")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"lag_corr_{ITEM_SLUG}.png", dpi=120)
    print(f"\n-> {OUT_DIR / f'lag_corr_{ITEM_SLUG}.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
