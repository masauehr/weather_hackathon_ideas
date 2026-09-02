"""事前登録した単一仮説の検証 — ほうれんそう × 真夏日数。

H1: 前橋の「真夏日数（最高気温 ≥30℃ の日数）」の季節偏差が大きい期間ほど、
    その 2〜4週間後（月次では 1〜2か月後）の東京のほうれんそう卸売価格
    （季節調整 log 残差）が高い。  ρ > 0, p < 0.05。

背景: 45セルの探索（analyze_lag_corr.py）で最大の効果量だった組み合わせ
      （週次 lag3週 ρ=+0.32, p=0.008, r²≈0.10）を、
      (1) 期間を 2011年〜 に伸ばした月次データ、
      (2) 自己相関に頑健な循環置換検定、
      で確かめ直す。多重比較を避けるため検定は最小限（月次 lag 1,2 / 週次 lag 2,3,4 のみ）。

入力:
  data/cs07/jma_daily_maebashi.csv            (date, tmax_c ...)  ← YEAR_START=2011 で再取得したもの
  data/cs07/veg_price_spinach_monthly.csv     (date, price)  月次 2011〜
  data/cs07/veg_price_spinach.csv             (date, price)  日次 2024〜（週次確認用）
出力:
  results/spinach_hotdays.png / spinach_hotdays.txt
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
from scipy import stats

from config import DATA_DIR, OUT_DIR

HOT_C = 30.0
RNG = np.random.default_rng(42)


def circ_perm_p(x: np.ndarray, y: np.ndarray, rho_obs: float, n: int = 5000) -> float:
    """循環シフト置換検定（自己相関を保ったまま帰無分布を作る）。両側。"""
    m = len(x)
    cnt = 0
    for _ in range(n):
        s = RNG.integers(1, m)
        r, _p = stats.spearmanr(np.roll(x, s), y)
        if abs(r) >= abs(rho_obs) - 1e-12:
            cnt += 1
    return (cnt + 1) / (n + 1)


def spearman_ci(rho: float, n: int, alpha: float = 0.05):
    z = np.arctanh(rho)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return np.tanh(lo), np.tanh(hi)


def load_daily_tmax(station: str) -> pd.DataFrame:
    d = pd.read_csv(DATA_DIR / f"jma_daily_{station}.csv", parse_dates=["date"])
    return d[["date", "tmax_c"]]


# ---------------------------------------------------------------- 月次（長期）
def monthly_test() -> tuple[list[str], dict]:
    tmax = load_daily_tmax("maebashi")
    tmax["ym"] = tmax["date"].dt.to_period("M")
    g = tmax.groupby("ym").agg(hot=("tmax_c", lambda s: (s >= HOT_C).sum()),
                               nday=("tmax_c", "count")).reset_index()
    g = g[g["nday"] >= 25].copy()
    g["mon"] = g["ym"].dt.month
    g["hot_anom"] = g["hot"] - g.groupby("mon")["hot"].transform("mean")

    price = pd.read_csv(DATA_DIR / "veg_price_spinach_monthly.csv", parse_dates=["date"])
    price["ym"] = price["date"].dt.to_period("M")
    price["mon"] = price["ym"].dt.month
    price["logp"] = np.log(price["price"])
    price["resid"] = price["logp"] - price.groupby("mon")["logp"].transform("mean")

    b = g.merge(price[["ym", "resid"]], on="ym", how="inner").sort_values("ym").reset_index(drop=True)
    lines = [f"## 月次（前橋 真夏日数偏差 → t+kか月 の価格残差）  n_months={len(b)}  "
             f"{b['ym'].min()}〜{b['ym'].max()}"]
    res = {}
    for lag in (0, 1, 2, 3):
        xf = b["hot_anom"]
        yf = b["resid"].shift(-lag)
        m = xf.notna() & yf.notna()
        rho, p = stats.spearmanr(xf[m], yf[m])
        lo, hi = spearman_ci(rho, int(m.sum()))
        pp = circ_perm_p(xf[m].values, yf[m].values, rho)
        res[lag] = dict(rho=rho, p=p, perm_p=pp, n=int(m.sum()), ci=(lo, hi), r2=rho**2)
        star = "  <-- H1" if lag in (1, 2) else ""
        lines.append(f"  lag {lag}か月: ρ={rho:+.3f}  p={p:.3f}  循環置換p={pp:.3f}  "
                     f"n={int(m.sum())}  95%CI[{lo:+.2f},{hi:+.2f}]  r²={rho**2:.3f}{star}")

    # 暖候期のみ（真夏日が実際に変動しうる 6〜10月の t月 → t+1月）
    warm = b[b["mon"].between(6, 10)].copy()
    xw = warm["hot_anom"]
    yw = b.set_index("ym")["resid"].reindex(warm["ym"] + 1).values
    mw = xw.notna().values & ~np.isnan(yw)
    rw, pw = stats.spearmanr(xw.values[mw], yw[mw])
    lw, hw = spearman_ci(rw, mw.sum())
    ppw = circ_perm_p(xw.values[mw], yw[mw], rw)
    res["warm1"] = dict(rho=rw, p=pw, perm_p=ppw, n=int(mw.sum()), ci=(lw, hw), r2=rw**2)
    lines.append(f"  [6〜10月のみ] lag1か月: ρ={rw:+.3f}  p={pw:.3f}  循環置換p={ppw:.3f}  "
                 f"n={int(mw.sum())}  95%CI[{lw:+.2f},{hw:+.2f}]  r²={rw**2:.3f}")
    return lines, {"base": b, "res": res}


# ---------------------------------------------------------------- 週次（2024〜 確認）
def weekly_test() -> tuple[list[str], dict]:
    tmax = load_daily_tmax("maebashi")
    tmax["wk"] = tmax["date"] - pd.to_timedelta(tmax["date"].dt.weekday, unit="D")
    g = tmax.groupby("wk").agg(hot=("tmax_c", lambda s: (s >= HOT_C).sum()),
                               nday=("tmax_c", "count")).reset_index()
    g = g[g["nday"] >= 5].copy()
    g["woy"] = g["wk"].dt.isocalendar().week.astype(int)
    g["hot_anom"] = g["hot"] - g.groupby("woy")["hot"].transform("mean")

    price = pd.read_csv(DATA_DIR / "veg_price_spinach.csv", parse_dates=["date"])
    price["wk"] = price["date"] - pd.to_timedelta(price["date"].dt.weekday, unit="D")
    w = price.groupby("wk", as_index=False)["price"].mean()
    w["woy"] = w["wk"].dt.isocalendar().week.astype(int)
    w["logp"] = np.log(w["price"])
    w["resid"] = w["logp"] - w.groupby("woy")["logp"].transform("mean")

    b = g.merge(w[["wk", "resid"]], on="wk", how="inner").sort_values("wk").reset_index(drop=True)
    lines = [f"## 週次（2024〜, 前橋 真夏日数偏差 → t+k週 の価格残差）  n_weeks={len(b)}"]
    res = {}
    for lag in (2, 3, 4):
        x = b["hot_anom"].values
        y = b["resid"].shift(-lag).values
        mask = ~np.isnan(x) & ~np.isnan(y)
        rho, p = stats.spearmanr(x[mask], y[mask])
        lo, hi = spearman_ci(rho, mask.sum())
        pp = circ_perm_p(x[mask], y[mask], rho)
        res[lag] = dict(rho=rho, p=p, perm_p=pp, n=int(mask.sum()), ci=(lo, hi), r2=rho**2)
        lines.append(f"  lag {lag}週: ρ={rho:+.3f}  p={p:.3f}  循環置換p={pp:.3f}  "
                     f"n={int(mask.sum())}  95%CI[{lo:+.2f},{hi:+.2f}]  r²={rho**2:.3f}")
    return lines, {"base": b, "res": res}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ml, md = monthly_test()
    wl, wd = weekly_test()

    m1 = md["res"][1]
    verdict = ("H1 支持（月次 lag1か月で ρ>0 かつ 循環置換 p<0.05）"
               if (m1["rho"] > 0 and m1["perm_p"] < 0.05)
               else "H1 は有意水準に未達")
    text = "\n".join(["# ほうれんそう × 真夏日数（≥30℃）— 事前登録した単一仮説の検証",
                      "H1: 真夏日数の季節偏差 → 1〜2か月後（2〜4週後）の価格残差 に正の相関",
                      "", *ml, "", *wl, "", f"=> {verdict}"])
    print(text)
    (OUT_DIR / "spinach_hotdays.txt").write_text(text + "\n")

    # 図
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    mb = md["base"]
    x = mb["hot_anom"].values[:-1]
    y = mb["resid"].shift(-1).values[:-1]
    ok = ~np.isnan(x) & ~np.isnan(y)
    ax[0, 0].scatter(x[ok], y[ok], s=18, alpha=.6, c="#e67e22")
    sl, ic = np.polyfit(x[ok], y[ok], 1)
    xs = np.linspace(x[ok].min(), x[ok].max(), 50)
    ax[0, 0].plot(xs, sl * xs + ic, c="#c0392b", lw=2)
    ax[0, 0].axhline(0, c="k", lw=.6); ax[0, 0].axvline(0, c="k", lw=.6)
    ax[0, 0].set_title(f"月次 散布図 lag1か月  ρ={md['res'][1]['rho']:+.2f} "
                       f"p={md['res'][1]['p']:.3f} 置換p={md['res'][1]['perm_p']:.3f} (n={md['res'][1]['n']})")
    ax[0, 0].set_xlabel("真夏日数 の季節偏差 (前橋, t月)")
    ax[0, 0].set_ylabel("価格残差 log (t+1月)")

    lags_m = [0, 1, 2, 3]
    ax[0, 1].bar(lags_m, [md["res"][l]["rho"] for l in lags_m],
                 color=["#c0392b" if l in (1, 2) else "#95a5a6" for l in lags_m])
    for l in lags_m:
        ax[0, 1].plot([l - .4, l + .4], [1.96 / np.sqrt(md["res"][l]["n"] - 1)] * 2, "k--", lw=.7)
    ax[0, 1].axhline(0, c="k", lw=.8)
    ax[0, 1].set_title("月次 ラグ別 ρ（赤=H1帯 lag1-2）")
    ax[0, 1].set_xlabel("ラグ [か月]"); ax[0, 1].set_ylabel("Spearman ρ")

    ax[1, 0].plot(mb["ym"].dt.to_timestamp(), mb["hot_anom"], c="#e67e22", label="真夏日数偏差")
    ax[1, 0].set_ylabel("真夏日数 偏差", color="#e67e22")
    axb = ax[1, 0].twinx()
    axb.plot(mb["ym"].dt.to_timestamp(), mb["resid"], c="#2980b9", label="価格残差")
    axb.set_ylabel("価格残差 log", color="#2980b9")
    ax[1, 0].set_title(f"月次 時系列 {mb['ym'].min()}〜{mb['ym'].max()}")

    wb = wd["base"]
    lags_w = [2, 3, 4]
    ax[1, 1].bar(lags_w, [wd["res"][l]["rho"] for l in lags_w], color="#c0392b")
    for l in lags_w:
        ax[1, 1].plot([l - .4, l + .4], [1.96 / np.sqrt(wd["res"][l]["n"] - 1)] * 2, "k--", lw=.7)
    ax[1, 1].axhline(0, c="k", lw=.8)
    ax[1, 1].set_title(f"週次(2024〜) ラグ別 ρ  n={wd['res'][3]['n']}")
    ax[1, 1].set_xlabel("ラグ [週]"); ax[1, 1].set_ylabel("Spearman ρ")

    fig.suptitle("ほうれんそう × 真夏日数（≥30℃, 前橋）  出典: 気象庁 / ベジ探", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUT_DIR / "spinach_hotdays.png", dpi=120)
    print(f"\n-> {OUT_DIR / 'spinach_hotdays.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
