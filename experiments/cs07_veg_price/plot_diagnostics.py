"""CS-07 の相関を「見て分かる」ための診断図。

analyze_lag_corr.py と同じ週次データを使い、6枚のパネルを1枚に出す。
  A: 相互相関関数 CCF（ラグ -4〜+8 週, Spearman, ±95%帯）
  B: 散布図 日照平年比(t) vs 価格残差(t+bestlag) ＋回帰直線
  C: 日照平年比を5分位に分け、各ビンの価格残差 平均±SE（単調性を見る）
  D: 夏季(5〜10月)だけの散布図（諏訪が主産地の期間）
  E: 26週ローリング相関（関係が時期で変わるか）
  F: 時系列（日照平年比 と 価格残差）

出力: out/diagnostics.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]  # macOS 日本語フォント
plt.rcParams["axes.unicode_minus"] = False
from scipy import stats

from config import OUT_DIR, PRODUCER_STATION, PRICE_ITEM, GO_LAGS, ITEM_SLUG
from analyze_lag_corr import load_sunshine_weekly, load_price_weekly

LAGS = list(range(-4, 9))
BEST_LAG_RANGE = [1, 2, 3, 4, 5, 6]


def spearman_at(x: pd.Series, y: pd.Series, lag: int):
    yy = y.shift(-lag)
    m = x.notna() & yy.notna()
    if m.sum() < 20:
        return np.nan, np.nan, int(m.sum())
    rho, p = stats.spearmanr(x[m], yy[m])
    return rho, p, int(m.sum())


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sun = load_sunshine_weekly()
    price, note = load_price_weekly()
    d = sun.merge(price, on="wk", how="inner").sort_values("wk").reset_index(drop=True)
    d["month"] = d["wk"].dt.month
    x = d["sun_ratio"]
    y = d["logp_resid"]

    # CCF
    ccf = [(lag, *spearman_at(x, y, lag)) for lag in LAGS]
    ccf = pd.DataFrame(ccf, columns=["lag", "rho", "p", "n"])
    band = 1.96 / np.sqrt(ccf["n"].replace(0, np.nan))

    # bestlag: 正のラグ 1〜6 で |rho| 最大
    sub = ccf[ccf["lag"].isin(BEST_LAG_RANGE)].dropna()
    best_lag = int(sub.loc[sub["rho"].abs().idxmax(), "lag"])
    yb = y.shift(-best_lag)

    fig, ax = plt.subplots(2, 3, figsize=(15, 8.5))

    # A: CCF
    a = ax[0, 0]
    a.bar(ccf["lag"], ccf["rho"],
          color=["#c0392b" if l in GO_LAGS else ("#2980b9" if l >= 0 else "#bbbbbb") for l in ccf["lag"]])
    a.plot(ccf["lag"], band, ls="--", c="k", lw=.8)
    a.plot(ccf["lag"], -band, ls="--", c="k", lw=.8)
    a.axhline(0, c="k", lw=.8); a.axvline(0, c="k", lw=.5)
    a.set_title(f"A. 相互相関 日照(t)→価格(t+ラグ)  最良={best_lag}週")
    a.set_xlabel("ラグ [週]（負=価格が先行）"); a.set_ylabel("Spearman ρ（破線=95%帯）")

    # B: scatter at best lag
    b = ax[0, 1]
    m = x.notna() & yb.notna()
    xv, yv = x[m].values, yb[m].values
    b.scatter(xv, yv, s=14, alpha=.5, c="#2980b9")
    sl, ic = np.polyfit(xv, yv, 1)
    xs = np.linspace(xv.min(), xv.max(), 50)
    b.plot(xs, sl * xs + ic, c="#c0392b", lw=2)
    rho, p = stats.spearmanr(xv, yv)
    pr, pp = stats.pearsonr(xv, yv)
    b.set_title(f"B. 散布図 ラグ{best_lag}週  ρ={rho:.2f} p={p:.3f}")
    b.set_xlabel("日照 平年比 (t)  ＜1.0=日照不足"); b.set_ylabel(f"価格 残差log (t+{best_lag}週)  ＞0=高値")

    # C: quintile bins
    c = ax[0, 2]
    dd = pd.DataFrame({"x": xv, "y": yv})
    dd["q"] = pd.qcut(dd["x"], 5, labels=["Q1\n日照少", "Q2", "Q3", "Q4", "Q5\n日照多"])
    g = dd.groupby("q", observed=True)["y"].agg(["mean", "sem"])
    c.bar(range(5), g["mean"], yerr=g["sem"], capsize=4, color="#16a085")
    c.axhline(0, c="k", lw=.8)
    c.set_xticks(range(5)); c.set_xticklabels(g.index)
    c.set_title(f"C. 日照5分位別 {best_lag}週後の価格残差(平均±SE)")
    c.set_ylabel("価格 残差log")

    # D: summer only (May-Oct)
    e = ax[1, 0]
    sm = m & d["month"].between(5, 10)
    xs2, ys2 = x[sm].values, yb[sm].values
    e.scatter(xs2, ys2, s=16, alpha=.6, c="#e67e22")
    if len(xs2) > 10:
        s2, i2 = np.polyfit(xs2, ys2, 1)
        xr = np.linspace(xs2.min(), xs2.max(), 50)
        e.plot(xr, s2 * xr + i2, c="#c0392b", lw=2)
        r2, p2 = stats.spearmanr(xs2, ys2)
        e.set_title(f"D. 夏季5〜10月のみ n={len(xs2)}  ρ={r2:.2f} p={p2:.3f}")
    e.axhline(0, c="k", lw=.6)
    e.set_xlabel("日照 平年比 (t)"); e.set_ylabel(f"価格 残差log (t+{best_lag}週)")

    # E: rolling 26w correlation
    f = ax[1, 1]
    roll = pd.DataFrame({"wk": d["wk"], "x": x, "y": yb}).dropna()
    rc = roll["x"].rolling(26).corr(roll["y"])
    f.plot(roll["wk"], rc, c="#8e44ad")
    f.axhline(0, c="k", lw=.8)
    f.set_title("E. 26週ローリング相関")
    f.set_ylabel("Pearson r（26週窓）")
    for lb in f.get_xticklabels():
        lb.set_rotation(30); lb.set_ha("right")

    # F: time series
    g2 = ax[1, 2]
    g2.plot(d["wk"], d["sun_ratio"], c="#f39c12", lw=1)
    g2.set_ylabel("日照 平年比", color="#f39c12")
    g3 = g2.twinx()
    g3.plot(d["wk"], d["logp_resid"], c="#2980b9", lw=1)
    g3.set_ylabel("価格 残差log", color="#2980b9")
    g2.set_title("F. 週次系列")
    for lb in g2.get_xticklabels():
        lb.set_rotation(30); lb.set_ha("right")

    fig.suptitle(f"CS-07 診断  品目={PRICE_ITEM}  産地={PRODUCER_STATION}  "
                 f"週数={len(d)}  ({d['wk'].min().date()}〜{d['wk'].max().date()})   出典: 気象庁 / ベジ探",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95], w_pad=2.5, h_pad=2.0)
    out = OUT_DIR / f"diagnostics_{ITEM_SLUG}.png"
    fig.savefig(out, dpi=120)
    print(f"-> {out}")
    print(ccf.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"best lag (|rho| max in {BEST_LAG_RANGE}w) = {best_lag}w")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
