"""⑥ 早期警戒アラートとして使えるか — 移動窓・イベント予測・リード時間。

狙い: 「出荷月 M が来る前に、産地の真夏日の溜まり具合から
       『来月のほうれんそうは平年比で高い／入荷が細る』を当てられるか」。

方法:
- 予測子 hot_win(M, lead, length):
    出荷対象月 M の開始 lead 日前で終わる length 日間の、産地合成 真夏日数。
    合成ウェイトは M の暦月の東京入荷シェア（ベジ探 産地別数量）。
    hot_win_anom = hot_win − 同一「対象月」の年平均。
- イベント（2値）:
    price_hi = 月次 価格残差（季節調整 log）が 全暖候期の上位1/3
    supply_lo = 月次 入荷量残差 が 下位1/3
- 評価:
    AUC（= 予測子がイベント日で高い確率, Mann-Whitney）
    ロジスティック回帰の係数と p
    アウトオブサンプル（2011-2020 で基準決定 → 2021-2026 で採点）
    アラート閾値（予測子が上位1/3）での 適合率・再現率・リフト・混同表
- リード時間掃引: lead = 10,20,30,40,50,60 日
- 出荷対象月は 7〜11月（真夏日が窓に入る月）

入力: data/cs07/jma_daily_<station>.csv, veg_price_spinach_monthly.csv, spinach_origin_qty.csv
     + regress_spinach_composite.total_quantity()
出力: results/spinach_alert.png / spinach_alert.txt
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
import statsmodels.formula.api as smf

from config import DATA_DIR, OUT_DIR, STATION_PREF
from regress_spinach_composite import total_quantity, origin_weights

HOT_C = 30.0
TARGET_MONTHS = [7, 8, 9, 10, 11]
LEADS = [10, 20, 30, 40, 50, 60]
WIN_LEN = 30
TERCILE = 1 / 3


def daily_composite_hot() -> pd.Series:
    """日次の『産地合成 真夏日インジケータ』。index=date, value=Σ_i w_i(その日の暦月) * 1[tmax_i>=30]。"""
    w = origin_weights()                       # index=month, col=station key
    keys = list(w.columns)
    frames = []
    for k in keys:
        d = pd.read_csv(DATA_DIR / f"jma_daily_{k}.csv", parse_dates=["date"]).set_index("date")
        frames.append((d["tmax_c"] >= HOT_C).astype(float).rename(k))
    hot = pd.concat(frames, axis=1).dropna(how="all")
    mon = hot.index.month
    wmat = np.vstack([w.loc[m].reindex(keys).values for m in mon])
    return pd.Series((hot[keys].values * wmat).sum(axis=1), index=hot.index, name="hot")


def hot_window(hot_daily: pd.Series, year: int, tmonth: int, lead: int, length: int) -> float:
    start = pd.Timestamp(year, tmonth, 1)
    w_end = start - pd.Timedelta(days=lead)
    w_beg = w_end - pd.Timedelta(days=length)
    seg = hot_daily.loc[(hot_daily.index >= w_beg) & (hot_daily.index < w_end)]
    return float(seg.sum()) if len(seg) else np.nan


def build(hot_daily: pd.Series) -> pd.DataFrame:
    price = pd.read_csv(DATA_DIR / "veg_price_spinach_monthly.csv", parse_dates=["date"])
    price["ym"] = price["date"].dt.to_period("M"); price["mon"] = price["ym"].dt.month
    price["logp"] = np.log(price["price"])
    price["p_resid"] = price["logp"] - price.groupby("mon")["logp"].transform("mean")

    q = total_quantity(); q = q.groupby("ym", as_index=False)["qty"].sum()
    q["mon"] = q["ym"].dt.month
    q["logq"] = np.log(pd.to_numeric(q["qty"], errors="coerce"))
    q["q_resid"] = q["logq"] - q.groupby("mon")["logq"].transform("mean")

    m = price.merge(q[["ym", "q_resid"]], on="ym", how="left")
    m = m[m["mon"].isin(TARGET_MONTHS)].copy().sort_values("ym").reset_index(drop=True)
    m["year"] = m["ym"].dt.year

    # 価格残差・入荷量残差から線形トレンドを除去（近年ほど高値＝構造要因を「イベント」判定から外す）
    t = np.arange(len(m))
    m["p_resid_dt"] = m["p_resid"] - np.polyval(np.polyfit(t, m["p_resid"], 1), t)
    ok = m["q_resid"].notna()
    m["q_resid_dt"] = np.nan
    m.loc[ok, "q_resid_dt"] = (m.loc[ok, "q_resid"]
                               - np.polyval(np.polyfit(t[ok], m.loc[ok, "q_resid"], 1), t[ok]))

    for lead in LEADS:
        m[f"hw{lead}"] = [hot_window(hot_daily, y, mo, lead, WIN_LEN)
                          for y, mo in zip(m["year"], m["mon"])]
        m[f"hw{lead}_anom"] = m[f"hw{lead}"] - m.groupby("mon")[f"hw{lead}"].transform("mean")

    # イベント（トレンド除去後の残差で上位/下位1/3 ＝「その時代なりに高い/細い」）
    m["price_hi"] = (m["p_resid_dt"] >= m["p_resid_dt"].quantile(1 - TERCILE)).astype(int)
    m["supply_lo"] = (m["q_resid_dt"] <= m["q_resid_dt"].quantile(TERCILE)).astype(int)
    return m.dropna(subset=[f"hw{LEADS[-1]}_anom"]).reset_index(drop=True)


def auc(score: np.ndarray, y: np.ndarray) -> float:
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    u = stats.mannwhitneyu(pos, neg, alternative="greater").statistic
    return u / (len(pos) * len(neg))


def oos_auc(m: pd.DataFrame, col: str, ev: str) -> float:
    tr, te = m[m["year"] <= 2020], m[m["year"] >= 2021]
    if len(te) < 6:
        return np.nan
    # 学習側で 対象月ごとの hw 平均を作り、テスト側の anom を再計算（情報漏れ防止）
    base = tr.groupby("mon")[col.replace("_anom", "")].mean()
    te_anom = te[col.replace("_anom", "")] - te["mon"].map(base)
    return auc(te_anom.values, te[ev].values)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hot_daily = daily_composite_hot()
    m = build(hot_daily)

    L = [f"# ⑥ 早期警戒アラート  ほうれんそう / 東京   対象月={TARGET_MONTHS}  窓長={WIN_LEN}日",
         f"n={len(m)}  ({m['year'].min()}〜{m['year'].max()})  イベント: 価格上位1/3 / 入荷量下位1/3",
         "",
         "## リード時間ごとの識別力（AUC。0.5=無意味, 1.0=完全）",
         f"{'lead[日]':>8} | {'価格hi AUC':>10} {'OOS':>6} | {'入荷lo AUC':>10} {'OOS':>6} | ロジ係数p(価格)"]
    rows = []
    for lead in LEADS:
        c = f"hw{lead}_anom"
        a_p = auc(m[c].values, m["price_hi"].values)
        a_q = auc(m[c].values, m["supply_lo"].values)
        o_p = oos_auc(m, c, "price_hi")
        o_q = oos_auc(m, c, "supply_lo")
        res = smf.logit(f"price_hi ~ {c}", data=m).fit(disp=0)
        pval = res.pvalues[c]
        rows.append((lead, a_p, o_p, a_q, o_q, pval))
        L.append(f"{lead:>8} | {a_p:>10.2f} {o_p:>6.2f} | {a_q:>10.2f} {o_q:>6.2f} | {pval:.3f}")
    R = pd.DataFrame(rows, columns=["lead", "aP", "oP", "aQ", "oQ", "p"])
    best = int(R.loc[(R["aP"] + R["oP"]).idxmax(), "lead"])   # 全期間＋OOS の合計で選ぶ
    L += ["", f"→ 価格イベントの識別力（全期間+OOS）が最大なのは lead={best}日"
          f"（窓 = 対象月開始の {best}〜{best+WIN_LEN}日前 ≒ 前月の暑さ）",
          f"  長いリードでも: lead=50日（約7週前）で 全AUC={R.loc[R['lead']==50,'aP'].iat[0]:.2f}, "
          f"OOS={R.loc[R['lead']==50,'oP'].iat[0]:.2f}"]

    # トレンド交絡の確認: 近年ほど暑く高値。年トレンドを入れても予測子が効くか
    cbest = f"hw{best}_anom"
    rt = smf.logit(f"price_hi ~ {cbest} + year", data=m).fit(disp=0)
    L.append(f"  トレンド統制: price_hi ~ {cbest} + year → {cbest} 係数 p={rt.pvalues[cbest]:.3f}, "
             f"year 係数 p={rt.pvalues['year']:.3f}")

    # アラート閾値（その年の窓が「暑い側 1/3」なら発報）
    c = f"hw{best}_anom"
    thr = m[c].quantile(1 - TERCILE)
    m["alert"] = (m[c] >= thr).astype(int)
    for ev, name in [("price_hi", "価格が平年比で高い"), ("supply_lo", "入荷量が細る")]:
        tp = ((m["alert"] == 1) & (m[ev] == 1)).sum()
        fp = ((m["alert"] == 1) & (m[ev] == 0)).sum()
        fn = ((m["alert"] == 0) & (m[ev] == 1)).sum()
        tn = ((m["alert"] == 0) & (m[ev] == 0)).sum()
        prec = tp / (tp + fp) if tp + fp else np.nan
        rec = tp / (tp + fn) if tp + fn else np.nan
        base = m[ev].mean()
        L += ["",
              f"## アラート（lead={best}日, 窓が暑い側1/3で発報） × 「{name}」",
              f"  適合率(発報が当たる率)= {prec:.0%}   再現率(該当を拾えた率)= {rec:.0%}   "
              f"リフト= {prec/base:.2f}倍（基準 {base:.0%}）",
              f"  混同表: TP={tp} FP={fp} FN={fn} TN={tn}  （発報 {m['alert'].sum()}/{len(m)} 回）"]

    # 年次バックテスト（対象月＝9月）
    L += ["", "## 年次バックテスト（対象月=9月, lead=" + str(best) + "日）"]
    s9 = m[m["mon"] == 9].sort_values("year")
    L.append(f"  {'年':>4} {'窓の真夏日偏差':>12} {'発報':>4} {'価格残差':>9} {'高値ｲﾍﾞﾝﾄ':>9}")
    for _, r in s9.iterrows():
        L.append(f"  {int(r['year']):>4} {r[c]:>12.1f} {'●' if r['alert'] else '−':>4} "
                 f"{np.expm1(r['p_resid_dt'])*100:>+8.0f}% {'●' if r['price_hi'] else '−':>7}")

    text = "\n".join(L)
    print(text)
    (OUT_DIR / "spinach_alert.txt").write_text(text + "\n")

    # ---- 図 ----
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))
    ax[0, 0].plot(R["lead"], R["aP"], "o-", label="価格hi AUC (全期間)")
    ax[0, 0].plot(R["lead"], R["oP"], "o--", label="価格hi AUC (2021-26 OOS)")
    ax[0, 0].plot(R["lead"], R["aQ"], "s-", color="#2980b9", label="入荷lo AUC (全期間)")
    ax[0, 0].axhline(0.5, color="k", lw=.8)
    ax[0, 0].set_xlabel("リード時間 [日]（対象月開始の何日前で窓を切るか）")
    ax[0, 0].set_ylabel("AUC"); ax[0, 0].set_ylim(0.4, 1.0); ax[0, 0].legend(fontsize=8)
    ax[0, 0].set_title("A. リード時間ごとの識別力")

    ax[0, 1].scatter(m[c], np.expm1(m["p_resid_dt"]) * 100, c=m["price_hi"], cmap="coolwarm", s=30)
    ax[0, 1].axvline(thr, color="#c0392b", ls="--", label="アラート閾値（暑い側1/3）")
    ax[0, 1].axhline(0, color="k", lw=.6)
    ax[0, 1].set_xlabel(f"窓の真夏日偏差（lead={best}日, {WIN_LEN}日窓）")
    ax[0, 1].set_ylabel("翌月の価格残差 [%]"); ax[0, 1].legend(fontsize=8)
    ax[0, 1].set_title(f"B. 予測子 × 価格残差（赤=高値ｲﾍﾞﾝﾄ）  AUC={R['aP'].max():.2f}")

    ax[1, 0].bar(s9["year"], s9[c], color=["#c0392b" if a else "#95a5a6" for a in s9["alert"]])
    for _, r in s9.iterrows():
        if r["price_hi"]:
            ax[1, 0].plot(r["year"], r[c] + 1.5, "k*", ms=10)
    ax[1, 0].axhline(thr, color="#c0392b", ls="--")
    ax[1, 0].set_title("C. 9月対象のバックテスト（赤=発報年, ★=実際に高値だった年）")
    ax[1, 0].set_ylabel("窓の真夏日偏差"); ax[1, 0].set_xlabel("年")

    # D: 混同表（価格）を棒で
    ev = "price_hi"
    tp = ((m["alert"] == 1) & (m[ev] == 1)).sum(); fp = ((m["alert"] == 1) & (m[ev] == 0)).sum()
    fn = ((m["alert"] == 0) & (m[ev] == 1)).sum(); tn = ((m["alert"] == 0) & (m[ev] == 0)).sum()
    ax[1, 1].bar(["的中\n(TP)", "空振り\n(FP)", "見逃し\n(FN)", "正しく非発報\n(TN)"], [tp, fp, fn, tn],
                 color=["#27ae60", "#e67e22", "#c0392b", "#bdc3c7"])
    for i, v in enumerate([tp, fp, fn, tn]):
        ax[1, 1].text(i, v + 0.3, str(v), ha="center")
    prec = tp / (tp + fp); rec = tp / (tp + fn); base = m[ev].mean()
    ax[1, 1].set_title(f"D. アラート×高値イベント  適合率{prec:.0%} 再現率{rec:.0%} リフト{prec/base:.1f}倍")

    fig.suptitle(f"⑥ ほうれんそう 早期警戒アラート（産地合成 真夏日, lead={best}日）  出典: 気象庁 / ベジ探",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "spinach_alert.png", dpi=120)
    print(f"\n-> {OUT_DIR / 'spinach_alert.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
