"""ほうれんそうの月別出荷と作付けカレンダー、真夏日数との関係を1枚に。

A: 月別の平均入荷量（東京）と 平均真夏日数（前橋）。作付け→生育→出荷の帯を重ねる。
B: 暑い夏 vs 涼しい夏 の月別入荷量プロファイル（6〜8月真夏日数の上位/下位5年）。
C: 年次散布図 — 夏(6〜8月)の真夏日数 × その年の 8〜10月 入荷量。

入力: data/cs07/jma_daily_maebashi.csv, data/cs07/vegetan_monthly_raw/spinach_*.csv
出力: results/spinach_calendar.png
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["Hiragino Sans", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
from matplotlib.patches import FancyArrow
from scipy import stats

from config import DATA_DIR, OUT_DIR
from regress_spinach_composite import total_quantity

HOT_C = 30.0
MONTHS = list(range(1, 13))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    q = total_quantity()
    q["mon"] = q["ym"].dt.month
    q["year"] = q["ym"].dt.year
    q["qM"] = q["qty"] / 1e6                        # 百万kg
    qty_clim = q.groupby("mon")["qM"].mean()

    d = pd.read_csv(DATA_DIR / "jma_daily_maebashi.csv", parse_dates=["date"])
    d["ym"] = d["date"].dt.to_period("M")
    h = d.groupby("ym").agg(hot=("tmax_c", lambda s: (s >= HOT_C).sum()),
                            nd=("tmax_c", "count")).reset_index()
    h = h[h["nd"] >= 25]
    h["mon"] = h["ym"].dt.month
    h["year"] = h["ym"].dt.year
    hot_clim = h.groupby("mon")["hot"].mean()

    summer = h[h["mon"].between(6, 8)].groupby("year")["hot"].sum()
    hot_yrs = sorted(summer.nlargest(5).index)
    cool_yrs = sorted(summer.nsmallest(5).index)

    fig = plt.figure(figsize=(13, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.42, wspace=0.28)

    # ---------- A: 月別 気候値 ＋ 作付けカレンダー ----------
    axA = fig.add_subplot(gs[0, :])
    axA.bar(MONTHS, [qty_clim[m] for m in MONTHS], color="#5dade2", width=0.6,
            label="入荷量（東京・月別平均, 百万kg）")
    axA.set_ylabel("入荷量 百万kg", color="#2874a6")
    axA.set_xticks(MONTHS); axA.set_xticklabels([f"{m}月" for m in MONTHS])
    axA.set_ylim(0, 2.0)

    axA2 = axA.twinx()
    axA2.plot(MONTHS, [hot_clim[m] for m in MONTHS], "o-", color="#e74c3c", lw=2,
              label="真夏日数（前橋・月別平均）")
    axA2.set_ylabel("真夏日数 / 月（前橋）", color="#c0392b")
    axA2.set_ylim(0, 30)

    # 作付け→生育→出荷 の帯（夏どり）: 播種6〜8月 → 生育30〜40日 → 収穫7〜9月
    axA.axvspan(5.6, 9.4, color="#f9e79f", alpha=0.35, zorder=0)
    # 夏の低い入荷量の上（空いている領域 y≈0.95〜1.35）に注記
    axA.annotate("", xy=(8.5, 1.15), xytext=(6.5, 1.15),
                 arrowprops=dict(arrowstyle="-|>", color="#7d6608", lw=2))
    axA.text(6.2, 1.28, "夏どり  播種 6〜8月", color="#7d6608", fontsize=9)
    axA.text(6.7, 1.02, "生育30〜40日", color="#7d6608", fontsize=8.5)
    axA.text(8.6, 1.15, "出荷 7〜9月", color="#7d6608", fontsize=9, ha="left", va="center")

    axA.set_title("A. ほうれんそう 月別の入荷量と真夏日数（2011〜2026 平均）\n"
                  "真夏日のピーク(7〜8月)の約1か月後に入荷量が底(8〜9月)＝ 播種〜生育期の高温 → 約1か月後に出荷減",
                  fontsize=11)
    l1, la1 = axA.get_legend_handles_labels()
    l2, la2 = axA2.get_legend_handles_labels()
    axA.legend(l1 + l2, la1 + la2, loc="upper left", fontsize=8)

    # ---------- B: 暑夏 vs 冷夏 の入荷量プロファイル ----------
    axB = fig.add_subplot(gs[1, 0])
    prof_hot = q[q["year"].isin(hot_yrs)].groupby("mon")["qM"].mean()
    prof_cool = q[q["year"].isin(cool_yrs)].groupby("mon")["qM"].mean()
    axB.plot(MONTHS, [prof_cool[m] for m in MONTHS], "s-", color="#3498db",
             label=f"涼しい夏 5年 {cool_yrs}")
    axB.plot(MONTHS, [prof_hot[m] for m in MONTHS], "o-", color="#e74c3c",
             label=f"暑い夏 5年 {hot_yrs}")
    axB.fill_between(MONTHS, [prof_cool[m] for m in MONTHS], [prof_hot[m] for m in MONTHS],
                     where=[prof_hot[m] < prof_cool[m] for m in MONTHS],
                     color="#e74c3c", alpha=0.15)
    axB.set_xticks(MONTHS); axB.set_xticklabels([f"{m}" for m in MONTHS])
    axB.set_xlabel("月"); axB.set_ylabel("入荷量 百万kg")
    axB.set_title("B. 暑い夏の年は 7〜10月の入荷量が 10〜25% 少ない", fontsize=10)
    axB.legend(fontsize=7.5)

    # ---------- C: 年次散布図（夏の真夏日数 × 8〜10月 入荷量）----------
    axC = fig.add_subplot(gs[1, 1])
    autumn_qty = q[q["mon"].between(8, 10)].groupby("year")["qM"].sum()
    m = pd.DataFrame({"hot": summer, "qty": autumn_qty}).dropna()
    axC.scatter(m["hot"], m["qty"], s=30, color="#e67e22")
    for y, r in m.iterrows():
        axC.annotate(str(int(y)), (r["hot"], r["qty"]), fontsize=7, alpha=.7,
                     xytext=(3, 2), textcoords="offset points")
    sl, ic = np.polyfit(m["hot"], m["qty"], 1)
    xs = np.linspace(m["hot"].min(), m["hot"].max(), 30)
    axC.plot(xs, sl * xs + ic, color="#c0392b", lw=2)
    rho, p = stats.spearmanr(m["hot"], m["qty"])
    axC.set_xlabel("夏(6〜8月)の真夏日数 合計（前橋）")
    axC.set_ylabel("その年の 8〜10月 入荷量 合計（百万kg）")
    axC.set_title(f"C. 暑い夏ほど秋の入荷量が少ない  Spearman ρ={rho:+.2f} (p={p:.3f}, n={len(m)})",
                  fontsize=10)

    fig.suptitle("ほうれんそう：作付け・出荷カレンダーと真夏日数の関係（東京市場 / 前橋）  出典: 気象庁 / ベジ探",
                 fontsize=12)
    fig.savefig(OUT_DIR / "spinach_calendar.png", dpi=120, bbox_inches="tight")
    print(f"-> {OUT_DIR / 'spinach_calendar.png'}")
    print(f"暑夏TOP5={hot_yrs}  冷夏TOP5={cool_yrs}")
    print(f"C: ρ={rho:+.3f} p={p:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
