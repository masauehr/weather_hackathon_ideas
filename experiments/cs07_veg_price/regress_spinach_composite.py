"""ほうれんそう × 真夏日数 — ⑤ 産地合成 ＋ 人為的要因（植え付け意思決定）の検証。

⑤-A 産地合成:
  東京入荷の産地ウェイト（ベジ探 月別の産地別数量, 暦月ごと）で
  複数官署の真夏日数を加重平均し、④の分布ラグ回帰を回し直す。
  対象産地・官署: 群馬=前橋 / 茨城=水戸 / 栃木=宇都宮 / 埼玉=熊谷 / 千葉=千葉 / 岩手=盛岡 / 岐阜=岐阜

⑤-B 人為的要因（農家の作付け判断）の検証:
  真夏は生育不適 → 農家は「夏に作付けを減らす」「涼しい産地に振る」等の適応をしているはず。
  これは "直接の高温被害" とは別の供給減チャネル。次で切り分けを試みる。
  (a) 入荷量の回帰: log(総入荷量_t) ~ ... + Σ真夏日数偏差_{t-k}  → 負なら供給減が価格上昇の経路
  (b) 涼しい産地シェアの回帰: cool_share_t ~ Σ真夏日数偏差_{t-k}  → 正なら「涼しい産地へ振り替え」の適応
  (c) growing-season heat（t-2,t-1）vs 同月 heat（t）の寄与比較

入力:
  data/cs07/jma_daily_<station>.csv          (2011〜, 各産地官署)
  data/cs07/spinach_origin_qty.csv           (year, month, origin, qty)  ← 産地ウェイト算出
  data/cs07/veg_price_spinach_monthly.csv    (date, price)
  data/cs07/vegetan_monthly_raw/spinach_YYYY.csv  ← 総入荷量の抽出
出力: results/spinach_composite.txt / .png
"""

from __future__ import annotations

import csv
import io
import pathlib

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
import statsmodels.formula.api as smf

from config import DATA_DIR, OUT_DIR, STATION_PREF

HOT_C = 30.0
HAC = {"cov_type": "HAC", "cov_kwds": {"maxlags": 6}}
HOT_LAGS = [0, 1, 2, 3]
COOL_PREFS = {"岩手", "岐阜", "長野", "北海道", "秋田", "青森"}   # 夏の冷涼産地


# ---------------------------------------------------------------- 産地ウェイト
def origin_weights() -> pd.DataFrame:
    """暦月ごとの産地ウェイト（対象7官署ぶんで再正規化）。index=month, columns=station key。"""
    q = pd.read_csv(DATA_DIR / "spinach_origin_qty.csv")
    pref2key = {v: k for k, v in STATION_PREF.items()}
    q = q[q["origin"].isin(pref2key)].copy()
    q["skey"] = q["origin"].map(pref2key)
    g = q.groupby(["month", "skey"])["qty"].sum().unstack(fill_value=0.0)
    w = g.div(g.sum(axis=1), axis=0)
    return w


# ---------------------------------------------------------------- 月次パネル
def monthly_hot(station: str) -> pd.DataFrame:
    d = pd.read_csv(DATA_DIR / f"jma_daily_{station}.csv", parse_dates=["date"])
    d["ym"] = d["date"].dt.to_period("M")
    g = d.groupby("ym").agg(hot=("tmax_c", lambda s: (s >= HOT_C).sum()),
                            nday=("tmax_c", "count")).reset_index()
    return g[g["nday"] >= 25][["ym", "hot"]].rename(columns={"hot": station})


def total_quantity() -> pd.DataFrame:
    """ベジ探 月別 生CSVから「総計」行の月次入荷量(kg)を取り出す。"""
    raw = pathlib.Path(DATA_DIR / "vegetan_monthly_raw")
    recs = []
    for f in sorted(raw.glob("spinach_*.csv")):
        rr = list(csv.reader(io.StringIO(f.read_bytes().decode("cp932", "replace"))))
        year = int(rr[0][2].split("年")[0].strip()[-4:])
        # row1 の "N月" ラベル位置で月を確定（末尾の年計列などを拾わないように）
        month_at = {i: int(mm.group(1)) for i, c in enumerate(rr[1])
                    if (mm := __import__("re").match(r"\s*(\d{1,2})月", c or ""))}
        kinds = rr[2]
        tot = next(r for r in rr if r and r[0].strip() == "総計")
        for i, k in enumerate(kinds):
            if k.strip() != "数量":
                continue
            mo = month_at.get(i)   # "N月" ラベルは 数量 列と同じ位置（row1）
            if not mo or not (1 <= mo <= 12) or i >= len(tot) or not tot[i].strip():
                continue
            recs.append((pd.Period(f"{year}-{mo:02d}", "M"), float(tot[i].replace(",", ""))))
    return pd.DataFrame(recs, columns=["ym", "qty"])


def build_panel() -> pd.DataFrame:
    w = origin_weights()
    keys = list(w.columns)
    hot = monthly_hot(keys[0])
    for k in keys[1:]:
        hot = hot.merge(monthly_hot(k), on="ym", how="inner")
    hot["month"] = hot["ym"].dt.month
    # 加重合成: Σ w_i(month) * hot_i
    wm = hot["month"].map(lambda m: w.loc[m])
    hot["hot_comp"] = sum(hot[k].values * np.array([w.loc[m, k] for m in hot["month"]]) for k in keys)
    hot["hot_maebashi"] = hot["maebashi"]
    hot["cool_w"] = hot["month"].map(lambda m: w.loc[m, [k for k in keys if STATION_PREF[k] in COOL_PREFS]].sum())

    p = pd.read_csv(DATA_DIR / "veg_price_spinach_monthly.csv", parse_dates=["date"])
    p["ym"] = p["date"].dt.to_period("M")
    p["logp"] = np.log(p["price"])
    q = total_quantity()

    q = q.groupby("ym", as_index=False)["qty"].sum()
    b = hot.merge(p[["ym", "logp"]], on="ym").merge(q, on="ym", how="left")
    b = b.sort_values("ym").reset_index(drop=True)
    b["qty"] = pd.to_numeric(b["qty"], errors="coerce")
    b["logq"] = np.log(b["qty"].where(b["qty"] > 0))
    for col in ("hot_comp", "hot_maebashi"):
        b[f"{col}_anom"] = b[col] - b.groupby("month")[col].transform("mean")
    b["trend"] = (np.arange(len(b)) - len(b) / 2) / 12.0
    for k in HOT_LAGS:
        b[f"hc_L{k}"] = b["hot_comp_anom"].shift(k)
        b[f"hm_L{k}"] = b["hot_maebashi_anom"].shift(k)
    b["logp_L1"] = b["logp"].shift(1)
    b["logq_L1"] = b["logq"].shift(1)
    return b, w


def dl_fit(b, ycol, xpref, extra, warm=False):
    df = b[b["month"].between(6, 11)] if warm else b
    terms = [f"{xpref}_L{k}" for k in HOT_LAGS] + extra
    df = df.dropna(subset=[ycol, "trend"] + terms)
    res = smf.ols(f"{ycol} ~ trend + C(month) + " + " + ".join(terms), data=df).fit(**HAC)
    hot_terms = [f"{xpref}_L{k}" for k in HOT_LAGS]
    idx = [res.params.index.get_loc(t) for t in hot_terms]
    cov = res.cov_params().values
    cum = float(res.params.iloc[idx].sum())
    cum_se = float(np.sqrt(np.ones(len(idx)) @ cov[np.ix_(idx, idx)] @ np.ones(len(idx))))
    wald = res.wald_test(" = ".join(hot_terms) + " = 0", use_f=True, scalar=True)
    return res, len(df), cum, cum_se, float(wald.pvalue)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    b, w = build_panel()
    L = ["# ⑤ 産地合成 ＋ 人為的要因（作付け判断）の検証  ほうれんそう / 東京",
         f"月次 {b['ym'].min()}〜{b['ym'].max()}  n={len(b)}",
         "産地ウェイト（暦月別・対象7官署で再正規化）例:",
         "  6月: " + ", ".join(f"{k}{w.loc[6,k]*100:.0f}%" for k in w.columns),
         "  8月: " + ", ".join(f"{k}{w.loc[8,k]*100:.0f}%" for k in w.columns),
         "  12月: " + ", ".join(f"{k}{w.loc[12,k]*100:.0f}%" for k in w.columns)]

    # ---- ⑤-A 合成 vs 前橋のみ（価格の分布ラグ回帰）----
    L += ["", "## ⑤-A  価格の分布ラグ回帰: 合成真夏日数 vs 前橋のみ",
          "  spec = log(price) ~ trend + C(month) + Σhot_Lk + precip無 + logp_L1"]
    for label, pref in [("前橋のみ", "hm"), ("産地合成", "hc")]:
        res, n, cum, cse, wp = dl_fit(b, "logp", pref, ["logp_L1"])
        b1 = res.params[f"{pref}_L1"]; s1 = res.bse[f"{pref}_L1"]
        L.append(f"  [{label}] n={n} adj.R²={res.rsquared_adj:.3f}  "
                 f"L1: β={b1:+.4f} t={b1/s1:+.2f} p={res.pvalues[f'{pref}_L1']:.4f}  "
                 f"Σβ={cum:+.4f}(t={cum/cse:+.2f})  Wald同時p={wp:.4f}  真夏日+10日→翌月{np.expm1(b1*10)*100:+.1f}%")

    # ---- ⑤-B (a) 入荷量の回帰 ----
    L += ["", "## ⑤-B(a)  入荷量の回帰: log(総入荷量) ~ ... + Σ合成真夏日数偏差_Lk  （負なら供給減が経路）"]
    res, n, cum, cse, wp = dl_fit(b, "logq", "hc", ["logq_L1"])
    for k in HOT_LAGS:
        t = f"hc_L{k}"; L.append(f"  {t}: β={res.params[t]:+.4f}  t={res.params[t]/res.bse[t]:+.2f}  p={res.pvalues[t]:.4f}")
    L.append(f"  Σβ(累積)= {cum:+.4f} (t={cum/cse:+.2f})  Wald同時p={wp:.4f}  → 真夏日+10日で入荷量 {np.expm1(cum*10)*100:+.1f}%")

    # ---- ⑤-B (b) 涼しい産地シェアの回帰 ----
    L += ["", "## ⑤-B(b)  冷涼産地シェアの回帰: cool_share ~ ... + Σ合成真夏日数偏差_Lk  （正なら涼しい産地へ適応）",
          "  ※ cool_share は暦月ウェイト由来のため月次で一定 → 年々変動が無く回帰不能。",
          "     代わりに『年ごとの実際の産地別数量』から夏(6-9月)の冷涼産地シェアを作り、夏の暑さと相関を見る。"]
    q = pd.read_csv(DATA_DIR / "spinach_origin_qty.csv")
    qs = q[q.month.between(6, 9)].copy()
    qs["cool"] = qs["origin"].isin(COOL_PREFS)
    yr = qs.groupby(["year", "cool"])["qty"].sum().unstack(fill_value=0.0)
    yr["cool_share"] = yr[True] / (yr[True] + yr[False])
    # 夏の合成真夏日数（6-9月平均の偏差）を年ごとに
    hb = b[b.month.between(6, 9)].groupby(b["ym"].dt.year)["hot_comp"].mean().rename("hot_summer")
    m = yr.join(hb).dropna()
    from scipy import stats
    r, p = stats.spearmanr(m["hot_summer"], m["cool_share"])
    L.append(f"  夏(6-9月)の合成真夏日数 × 同年夏の冷涼産地(岩手/岐阜/長野/北海道等)シェア: "
             f"Spearman ρ={r:+.3f}  p={p:.3f}  n={len(m)}")
    L.append(f"  冷涼産地シェアの推移: " + ", ".join(f"{int(y)}:{v:.0%}" for y, v in m["cool_share"].items()))

    # ---- ⑤-B (c) growing-season heat vs 同月 ----
    L += ["", "## ⑤-B(c)  同月(L0) vs 生育期(L1,L2) の寄与  （⑤-A 産地合成モデルの係数）"]
    res, n, *_ = dl_fit(b, "logp", "hc", ["logp_L1"])
    for k in HOT_LAGS:
        t = f"hc_L{k}"
        L.append(f"  hc_L{k}: β={res.params[t]:+.4f}  t={res.params[t]/res.bse[t]:+.2f}  p={res.pvalues[t]:.4f}")
    L.append("  → L1(=1か月前の暑さ) に集中。同月(L0)はほぼ0。作付け判断・発芽不良・生育不良が")
    L.append("     約1か月遅れで出荷減として現れる、という時間構造。直接被害と作付け判断は月次では分離不可。")

    text = "\n".join(L)
    print(text)
    (OUT_DIR / "spinach_composite.txt").write_text(text + "\n")

    # 図
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    for pref, lab, c in [("hm", "前橋のみ", "#95a5a6"), ("hc", "産地合成", "#c0392b")]:
        res, n, *_ = dl_fit(b, "logp", pref, ["logp_L1"])
        beta = [res.params[f"{pref}_L{k}"] for k in HOT_LAGS]
        err = [1.96 * res.bse[f"{pref}_L{k}"] for k in HOT_LAGS]
        xs = np.arange(len(HOT_LAGS)) + (0.18 if pref == "hc" else -0.18)
        ax[0].bar(xs, beta, 0.36, yerr=err, capsize=3, label=lab, color=c)
    ax[0].axhline(0, color="k", lw=.8); ax[0].set_xticks(range(len(HOT_LAGS)))
    ax[0].set_xticklabels([f"lag{k}月" for k in HOT_LAGS]); ax[0].legend()
    ax[0].set_title("価格への分布ラグ係数（合成 vs 前橋）"); ax[0].set_ylabel("β (log価格/真夏日1日)")

    res, n, *_ = dl_fit(b, "logq", "hc", ["logq_L1"])
    beta = [res.params[f"hc_L{k}"] for k in HOT_LAGS]
    err = [1.96 * res.bse[f"hc_L{k}"] for k in HOT_LAGS]
    ax[1].bar(range(len(HOT_LAGS)), beta, 0.5, yerr=err, capsize=3, color="#2980b9")
    ax[1].axhline(0, color="k", lw=.8); ax[1].set_xticks(range(len(HOT_LAGS)))
    ax[1].set_xticklabels([f"lag{k}月" for k in HOT_LAGS])
    ax[1].set_title("入荷量への分布ラグ係数（合成真夏日数）"); ax[1].set_ylabel("β (log入荷量/真夏日1日)")
    fig.suptitle("⑤ 産地合成 ＋ 供給（入荷量）チャネル  ほうれんそう / 東京  出典: 気象庁 / ベジ探", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT_DIR / "spinach_composite.png", dpi=120)
    print(f"\n-> {OUT_DIR / 'spinach_composite.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
