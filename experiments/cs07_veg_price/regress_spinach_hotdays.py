"""ほうれんそう × 真夏日数 — 分布ラグ回帰（交絡統制つき）。

③ の相関（前橋の真夏日数 → 翌月の卸売価格）が、
  ・季節（暦月ダミー）
  ・トレンド
  ・価格自身のモメンタム（前月価格 = AR項）
  ・もう一つの気象チャネル（降水）
を同時に入れても残るか、真夏日数の「限界寄与」と符号安定性を確認する。

モデル: log(price_t) ~ trend + C(month) + Σ_k β_k·hot_anom_{t-k}  (+ precip_anom, + logp_{t-1})
標準誤差: Newey-West (HAC, maxlags=6)  ← 月次の系列相関に頑健
真夏日数ブロック（β_0..β_3 = 0）の同時検定は HAC 共分散での Wald 検定。

入力: data/cs07/jma_daily_maebashi.csv, data/cs07/veg_price_spinach_monthly.csv
出力: results/spinach_hotdays_regression.txt / .png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import statsmodels.formula.api as smf

from config import DATA_DIR, OUT_DIR

HOT_C = 30.0
HAC = {"cov_type": "HAC", "cov_kwds": {"maxlags": 6}}
HOT_LAGS = [0, 1, 2, 3]
PRECIP_LAGS = [0, 1, 2]


def build_panel() -> pd.DataFrame:
    d = pd.read_csv(DATA_DIR / "jma_daily_maebashi.csv", parse_dates=["date"])
    d["ym"] = d["date"].dt.to_period("M")
    g = d.groupby("ym").agg(hot=("tmax_c", lambda s: (s >= HOT_C).sum()),
                            precip=("precip_mm", "sum"),
                            nday=("tmax_c", "count")).reset_index()
    g = g[g["nday"] >= 25].copy()
    g["month"] = g["ym"].dt.month
    g["hot_anom"] = g["hot"] - g.groupby("month")["hot"].transform("mean")
    g["precip_anom"] = (np.log1p(g["precip"])
                        - g.groupby("month")["precip"].transform(lambda s: np.log1p(s).mean()))

    p = pd.read_csv(DATA_DIR / "veg_price_spinach_monthly.csv", parse_dates=["date"])
    p["ym"] = p["date"].dt.to_period("M")
    p["logp"] = np.log(p["price"])

    b = g.merge(p[["ym", "logp"]], on="ym", how="inner").sort_values("ym").reset_index(drop=True)
    # 月次が連続していることを確認（ラグの意味が崩れないよう）
    step = (b["ym"].astype("int64").diff().dropna() != 1)
    if step.any():
        print(f"警告: 月次に {int(step.sum())} 箇所の欠落。ラグ生成前に確認を。")
    b["trend"] = (np.arange(len(b)) - len(b) / 2) / 12.0   # 年単位・中心化
    for k in HOT_LAGS:
        b[f"hot_anom_L{k}"] = b["hot_anom"].shift(k)
    for k in PRECIP_LAGS:
        b[f"precip_anom_L{k}"] = b["precip_anom"].shift(k)
    b["logp_L1"] = b["logp"].shift(1)
    return b


def fit(b: pd.DataFrame, terms: list[str], warm: bool):
    df = b.copy()
    if warm:
        df = df[df["month"].between(6, 11)]
    cols = ["logp", "trend", "month"] + terms
    df = df.dropna(subset=[c for c in cols if c != "month"])
    f = "logp ~ trend + C(month) + " + " + ".join(terms)
    return smf.ols(f, data=df).fit(**HAC), len(df)


def summarize(name, res, n, hot_terms, lines):
    lines.append(f"\n### {name}   n={n}   adj.R²={res.rsquared_adj:.3f}")
    for t in hot_terms:
        co, se, pv = res.params[t], res.bse[t], res.pvalues[t]
        lines.append(f"  {t:14} β={co:+.4f}  HAC-SE={se:.4f}  t={co/se:+.2f}  p={pv:.4f}")
    # 累積効果（Σβ_k）と HAC-SE（デルタ法）
    idx = [res.params.index.get_loc(t) for t in hot_terms]
    cov = res.cov_params().values
    cum = float(res.params.iloc[idx].sum())
    cum_se = float(np.sqrt(np.ones(len(idx)) @ cov[np.ix_(idx, idx)] @ np.ones(len(idx))))
    lines.append(f"  Σβ(累積, {len(hot_terms)}ラグ)= {cum:+.4f}  HAC-SE={cum_se:.4f}  "
                 f"t={cum/cum_se:+.2f}  → 真夏日+10日で累積 {np.expm1(cum*10)*100:+.1f}%")
    # 真夏日数ブロックの同時 Wald 検定（HAC）
    wt = res.wald_test(" = ".join(hot_terms) + " = 0", use_f=True, scalar=True)
    lines.append(f"  同時検定 H0: 全ラグ係数=0  → F={float(wt.statistic):.2f}  p={float(wt.pvalue):.4f}")
    return cum, cum_se


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    b = build_panel()
    hot_terms = [f"hot_anom_L{k}" for k in HOT_LAGS]
    prc_terms = [f"precip_anom_L{k}" for k in PRECIP_LAGS]

    lines = ["# ほうれんそう × 真夏日数 — 分布ラグ回帰（前橋, 月次 2011〜2026）",
             "log(price) ~ trend + 暦月ダミー + Σ hot_anom_Lk (+ precip_anom, + logp_L1)",
             "標準誤差 = Newey-West HAC(maxlags=6)。真夏日数ブロックは HAC 共分散で Wald 同時検定。"]

    specs = [
        ("M1: 分布ラグのみ", hot_terms, False),
        ("M2: + 降水", hot_terms + prc_terms, False),
        ("M3: + 降水 + 前月価格(AR1)", hot_terms + prc_terms + ["logp_L1"], False),
        ("M4: M3 を暖候期(6〜11月)に限定", hot_terms + prc_terms + ["logp_L1"], True),
    ]
    fitted = {}
    for name, terms, warm in specs:
        res, n = fit(b, terms, warm)
        fitted[name] = (res, n)
        summarize(name, res, n, hot_terms, lines)

    # ΔR²: M3 から真夏日数ブロックを抜くと adj.R² がどれだけ落ちるか
    res_full, n3 = fitted["M3: + 降水 + 前月価格(AR1)"]
    res_drop, _ = fit(b, prc_terms + ["logp_L1"], warm=False)
    lines.append(f"\n真夏日数ブロックの寄与: adj.R² {res_drop.rsquared_adj:.3f} → {res_full.rsquared_adj:.3f} "
                 f"(Δ={res_full.rsquared_adj - res_drop.rsquared_adj:+.3f})")

    text = "\n".join(lines)
    print(text)
    (OUT_DIR / "spinach_hotdays_regression.txt").write_text(text + "\n")

    # 係数プロット（各モデルの hot_anom_Lk ± 95%CI）
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.2
    for i, (name, (res, n)) in enumerate(fitted.items()):
        beta = [res.params[t] for t in hot_terms]
        err = [1.96 * res.bse[t] for t in hot_terms]
        xs = np.arange(len(hot_terms)) + (i - 1.5) * width
        ax.bar(xs, beta, width, yerr=err, capsize=3, label=name)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(np.arange(len(hot_terms)))
    ax.set_xticklabels([f"lag {k}か月" for k in HOT_LAGS])
    ax.set_ylabel("β（log価格 / 真夏日数1日）  HAC 95%CI")
    ax.set_title("真夏日数の分布ラグ係数（前橋 → 東京ほうれんそう卸売価格, 月次2011〜2026）")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spinach_hotdays_regression.png", dpi=120)
    print(f"\n-> {OUT_DIR / 'spinach_hotdays_regression.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
