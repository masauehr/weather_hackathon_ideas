"""CS-07 の相関判定（複数気象特徴 × ラグ）。

産地の週次気象（日照・全天日射・降水・高温日数）の平年偏差と、
数週後の卸売価格（季節調整後 log 残差）の Spearman 相関を ラグ0〜8週で見る。

入力:
  data/cs07/jma_daily_<PRODUCER_STATION>.csv  (date, precip_mm, tmax_c, sunshine_h, solar_mj)
  data/cs07/veg_price_<ITEM_SLUG>.csv         (date, price)
出力:
  results/summary_<ITEM_SLUG>.txt   特徴×ラグの ρ/p 行列と判定
  results/lag_corr_<ITEM_SLUG>.png  同じもののヒートマップ

GO 判定（当初仮説）: 日照(sunshine) の ラグ GO_LAGS のいずれかで p<GO_P かつ ρ<0。
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
from scipy import stats

from config import (DATA_DIR, OUT_DIR, PRODUCER_STATION, PRICE_ITEM, ITEM_SLUG,
                    LAG_WEEKS, GO_LAGS, GO_P, WEATHER_FEATURES, HOT_THRESHOLDS)

FEATURE_LABEL = {
    "sunshine": "日照時間", "solar": "全天日射量", "precip": "降水量",
    "hot30": "真夏日数(≥30℃)", "hot25": "夏日数(≥25℃)",
}


def _week_start(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s)
    return d - pd.to_timedelta(d.dt.weekday, unit="D")


def _woy_zanom(g: pd.DataFrame, col: str) -> pd.Series:
    """週番号（week-of-year）ごとの平均・標準偏差で標準化した偏差。"""
    woy = g["wk"].dt.isocalendar().week.astype(int)
    mean = g.groupby(woy)[col].transform("mean")
    std = g.groupby(woy)[col].transform("std")
    return (g[col] - mean) / std.replace(0, np.nan)


def load_weather_weekly(station: str) -> tuple[pd.DataFrame, dict]:
    src = DATA_DIR / f"jma_daily_{station}.csv"
    d = pd.read_csv(src, parse_dates=["date"])
    d["wk"] = _week_start(d["date"])
    for name, thr in HOT_THRESHOLDS.items():
        d[name] = (d["tmax_c"] >= thr).astype(float)
        d.loc[d["tmax_c"].isna(), name] = np.nan

    agg = {"sunshine": ("sunshine_h", "sum"), "solar": ("solar_mj", "sum"),
           "precip": ("precip_mm", "sum"), "hot30": ("hot30", "sum"), "hot25": ("hot25", "sum"),
           "n_days": ("date", "count"),
           "n_sun": ("sunshine_h", lambda x: x.notna().sum()),
           "n_solar": ("solar_mj", lambda x: x.notna().sum())}
    g = d.groupby("wk").agg(**agg).reset_index()
    g = g[g["n_days"] >= 5].copy()

    avail = {}
    for feat in WEATHER_FEATURES:
        if feat == "solar" and g["n_solar"].sum() == 0:
            avail[feat] = False
            continue
        g[f"{feat}_z"] = _woy_zanom(g, feat)
        avail[feat] = True
    # 日照の平年比（plot_diagnostics 互換用）
    woy = g["wk"].dt.isocalendar().week.astype(int)
    g["sun_ratio"] = g["sunshine"] / g.groupby(woy)["sunshine"].transform("mean")
    g["sun_anom_z"] = g["sunshine_z"]
    return g, avail


def load_sunshine_weekly() -> pd.DataFrame:   # plot_diagnostics.py 互換
    g, _ = load_weather_weekly(PRODUCER_STATION)
    return g[["wk", "sun_ratio", "sun_anom_z"]]


def load_price_weekly() -> tuple[pd.DataFrame, str]:
    src = DATA_DIR / f"veg_price_{ITEM_SLUG}.csv"
    df = pd.read_csv(src, parse_dates=["date"]).dropna().sort_values("date")
    span = df["date"].diff().dt.days.median()
    df["wk"] = _week_start(df["date"])
    w = df.groupby("wk", as_index=False)["price"].mean()
    if span and span > 20:
        full = pd.date_range(w["wk"].min(), w["wk"].max(), freq="W-MON")
        w = w.set_index("wk").reindex(full).interpolate("time").rename_axis("wk").reset_index()
        note = f"価格は月次(中央間隔~{span:.0f}日)を週次へ線形補間"
    else:
        note = f"価格は週次相当(中央間隔~{span:.0f}日)"
    w["logp"] = np.log(w["price"])
    woy = w["wk"].dt.isocalendar().week.astype(int)
    w["logp_resid"] = w["logp"] - w.groupby(woy)["logp"].transform("mean")
    return w[["wk", "price", "logp_resid"]], note


def ccf(base: pd.DataFrame, xcol: str) -> pd.DataFrame:
    rows = []
    for lag in LAG_WEEKS:
        x = base[xcol]
        y = base["logp_resid"].shift(-lag)
        m = x.notna() & y.notna()
        if m.sum() < 20:
            rows.append((lag, np.nan, np.nan, int(m.sum())))
        else:
            rho, p = stats.spearmanr(x[m], y[m])
            rows.append((lag, rho, p, int(m.sum())))
    return pd.DataFrame(rows, columns=["lag", "rho", "p", "n"])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wx, avail = load_weather_weekly(PRODUCER_STATION)
    price, note = load_price_weekly()
    base = wx.merge(price, on="wk", how="inner").sort_values("wk").reset_index(drop=True)
    if len(base) < 30:
        print(f"重複週数が少ない（{len(base)}）", file=sys.stderr)

    feats = [f for f in WEATHER_FEATURES if avail.get(f)]
    ccfs = {f: ccf(base, f"{f}_z") for f in feats}

    # サマリ
    lines = [
        f"# CS-07 複数気象特徴 × ラグ相関   品目={PRICE_ITEM}  産地={PRODUCER_STATION}",
        f"重複週数={len(base)}  ({base['wk'].min().date()}〜{base['wk'].max().date()})   {note}",
        f"各セル = Spearman ρ（* = p<{GO_P}）。特徴は week-of-year 標準化偏差。price は季節調整 log 残差。",
        "",
        "feature\\lag  " + "  ".join(f"{l:>6}" for l in LAG_WEEKS),
    ]
    for f in feats:
        c = ccfs[f]
        cells = []
        for _, r in c.iterrows():
            if np.isnan(r["rho"]):
                cells.append("   .  ")
            else:
                cells.append(f"{r['rho']:+.2f}{'*' if r['p'] < GO_P else ' '}")
        lines.append(f"{FEATURE_LABEL[f]:<11}" + "  ".join(f"{x:>6}" for x in cells))
    if not avail.get("solar", True):
        lines.append("(全天日射量: この地点は観測なし → スキップ)")

    # 各特徴の最良ラグ（1〜6週で |ρ| 最大）
    lines += ["", "## 各特徴の最良ラグ（1〜6週で |ρ| 最大）"]
    for f in feats:
        c = ccfs[f]
        sub = c[c["lag"].between(1, 6)].dropna()
        b = sub.loc[sub["rho"].abs().idxmax()]
        se = 1 / np.sqrt(b["n"] - 1)
        lines.append(f"  {FEATURE_LABEL[f]:<12} lag{int(b['lag'])}週  ρ={b['rho']:+.3f}  "
                     f"p={b['p']:.3f}  n={int(b['n'])}  z={b['rho']/se:+.2f}σ  r²={b['rho']**2:.3f}")

    # GO 判定（日照の当初仮説）
    sc = ccfs.get("sunshine")
    go = sc[(sc["lag"].isin(GO_LAGS)) & (sc["p"] < GO_P) & (sc["rho"] < 0)] if sc is not None else None
    verdict = "GO" if (go is not None and not go.empty) else "NO-GO"
    nominal = []
    for f in feats:
        c = ccfs[f]
        hit = c[(c["lag"].between(0, 4)) & (c["p"] < GO_P)]
        for _, r in hit.iterrows():
            nominal.append(f"{FEATURE_LABEL[f]} lag{int(r['lag'])} ρ={r['rho']:+.2f} p={r['p']:.3f}")
    lines += ["",
              f"判定（当初仮説＝日照 ラグ{GO_LAGS} で p<{GO_P} かつ ρ<0）: => {verdict}",
              "名目 p<0.05 のセル（多重比較 未補正・参考）: " + ("、".join(nominal) if nominal else "なし")]

    summary = "\n".join(lines)
    print(summary)
    (OUT_DIR / f"summary_{ITEM_SLUG}.txt").write_text(summary + "\n")

    # ヒートマップ
    mat = np.vstack([ccfs[f]["rho"].values for f in feats])
    pmat = np.vstack([ccfs[f]["p"].values for f in feats])
    fig, ax = plt.subplots(figsize=(1.1 * len(LAG_WEEKS) + 2.5, 0.6 * len(feats) + 2))
    im = ax.imshow(mat, cmap="RdBu_r", vmin=-0.35, vmax=0.35, aspect="auto")
    ax.set_xticks(range(len(LAG_WEEKS))); ax.set_xticklabels(LAG_WEEKS)
    ax.set_yticks(range(len(feats))); ax.set_yticklabels([FEATURE_LABEL[f] for f in feats])
    ax.set_xlabel("ラグ [週]（気象 → 価格）")
    for i in range(len(feats)):
        for j in range(len(LAG_WEEKS)):
            if np.isnan(mat[i, j]):
                continue
            star = "*" if pmat[i, j] < GO_P else ""
            ax.text(j, i, f"{mat[i, j]:+.2f}{star}", ha="center", va="center",
                    fontsize=8, color="black")
    ax.set_title(f"CS-07  {PRICE_ITEM} / {PRODUCER_STATION}  週数={len(base)}   判定(日照): {verdict}\n"
                 "セル=Spearman ρ, * = p<0.05（出典: 気象庁 / ベジ探）", fontsize=10)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman ρ")
    fig.tight_layout()
    fig.savefig(OUT_DIR / f"lag_corr_{ITEM_SLUG}.png", dpi=120)
    print(f"\n-> {OUT_DIR / f'lag_corr_{ITEM_SLUG}.png'}")
    print(f"-> {OUT_DIR / f'summary_{ITEM_SLUG}.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
