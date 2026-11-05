"""ID-37 予備解析: 降水はバス遅延を増やすか。

設計:
  - 観測単位: (bus_id, busstop, scheduled_time) の重複を除いた「到着イベント」。
  - 外れ値: 遅延を 0.5〜99.5 パーセンタイルでウィンザー化（主結果）。
            感度分析として「5分超遅れの確率」（外れ値に頑健）も推定。
  - 交絡対策: 路線・日付・時間帯・曜日×時間帯の固定効果を吸収（FWL: 交互射影）。
  - 標準誤差: 日付クラスタ頑健（同日内は天気・混雑が相関するため）。
            自由度補正なしの簡易版なので、やや楽観的な点に注意。
  - 降水: 直近10分降水量（最寄りアメダス）。0 / 0.5mm / 1.0mm以上 の3区分（観測値は0.5mm刻み）と有無の2通り。

使い方: python3 src/analyze_prelim.py  （結果は results/prelim/ に出力）
"""
import os
import sys
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(BASE, "data", "processed", "bus_delay_log.csv")
OUT = os.path.join(BASE, "results", "prelim")
os.makedirs(OUT, exist_ok=True)


def load():
    d = pd.read_csv(CSV, usecols=[
        "polled_at", "bus_id", "busroute", "busstop", "scheduled_time",
        "delay_seconds", "amedas_station", "precipitation10m_mm"])
    d = d.dropna(subset=["precipitation10m_mm", "delay_seconds"])
    # 同一イベントの重複ポーリングは最後の観測を採用
    d = d.sort_values("polled_at").drop_duplicates(
        ["bus_id", "busstop", "scheduled_time"], keep="last")
    # 時間帯・日付は予定時刻（JST）基準
    t = pd.to_datetime(d["scheduled_time"].str.slice(0, 19))
    d["date"] = t.dt.date.astype(str)
    d["hour"] = t.dt.hour
    d["dow"] = t.dt.dayofweek
    d["dowhour"] = d["dow"] * 24 + d["hour"]
    return d.reset_index(drop=True)


def demean(v, groups, iters=30, tol=1e-7):
    """複数の固定効果を交互射影で吸収する。v は (n,k)。"""
    v = v.copy()
    for _ in range(iters):
        prev = v.copy()
        for g in groups:
            m = pd.DataFrame(v).groupby(g).transform("mean").values
            v -= m
        if np.max(np.abs(v - prev)) < tol:
            break
    return v


def fe_ols(y, X, groups, cluster):
    """固定効果吸収OLS + クラスタ頑健SE。y:(n,), X:(n,k)"""
    Z = np.column_stack([y, X]).astype(np.float64)
    Zt = demean(Z, groups)
    yt, Xt = Zt[:, 0], Zt[:, 1:]
    XtX_inv = np.linalg.inv(Xt.T @ Xt)
    beta = XtX_inv @ (Xt.T @ yt)
    u = yt - Xt @ beta
    S = Xt * u[:, None]
    cl = pd.factorize(cluster)[0]
    G = cl.max() + 1
    sc = np.zeros((G, Xt.shape[1]))
    np.add.at(sc, cl, S)
    meat = sc.T @ sc
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1))
    return beta, np.sqrt(np.diag(V)), G


def main():
    d = load()
    print(f"到着イベント数: {len(d):,} / 日数: {d['date'].nunique()}")
    lo, hi = d["delay_seconds"].quantile([0.005, 0.995])
    d["y"] = d["delay_seconds"].clip(lo, hi)
    d["late5"] = (d["delay_seconds"] > 300).astype(float)
    p = d["precipitation10m_mm"]
    d["rain"] = (p > 0).astype(float)
    # 降水量は0.5mm刻みの離散値（0 / 0.5 / 1.0 …）
    d["rain_weak"] = ((p > 0) & (p < 1.0)).astype(float)
    d["rain_mid"] = (p >= 1.0).astype(float)
    print(f"ウィンザー範囲: {lo:.0f}〜{hi:.0f} 秒 / 降水あり {int(d.rain.sum()):,} / "
          f"1.0mm以上 {int(d.rain_mid.sum()):,}")

    # 平日のみ・全日の2通り
    sets = {"全日": d, "平日のみ": d[d["dow"] < 5].reset_index(drop=True)}
    fe_sets = {
        "FEなし": [],
        "路線+時間帯": ["busroute", "hour"],
        "路線+日付+曜日×時間帯": ["busroute", "date", "dowhour"],
    }
    rows = []
    for sname, df in sets.items():
        for fname, groups in fe_sets.items():
            for yname in ["y", "late5"]:
                for xname, xs in [("降水あり", ["rain"]),
                                  ("0.5mm/1.0mm以上", ["rain_weak", "rain_mid"])]:
                    X = df[xs].values
                    y = df[yname].values
                    if groups:
                        beta, se, G = fe_ols(y, X, [df[g].values for g in groups],
                                             df["date"].values)
                    else:
                        # FEなしは切片のみ
                        beta, se, G = fe_ols(y, X, [np.zeros(len(df), int)],
                                             df["date"].values)
                    for i, nm in enumerate(xs):
                        rows.append(dict(標本=sname, 固定効果=fname,
                                         目的変数="遅延秒(winsor)" if yname == "y" else "5分超遅延確率",
                                         説明変数=nm, 係数=beta[i], SE=se[i],
                                         t=beta[i] / se[i], 日数=G, n=len(df)))
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT, "regression.csv"), index=False)
    pd.set_option("display.width", 200)
    print(res.round(3).to_string(index=False))

    # --- 記述: 日別の降水イベントごとの効果（日内で雨の時間 vs 同日の乾いた時間） ---
    wd = sets["平日のみ"]
    daily = []
    for dt, g in d.groupby("date"):
        r = g[g.rain == 1]
        if len(r) < 500 or (g.rain == 0).sum() < 500:
            continue
        # 同日・同路線・同時間帯で比較できるセルだけ使う
        cell = g.groupby(["busroute", "hour", "rain"])["y"].mean().unstack()
        cell = cell.dropna()
        if len(cell) < 20:
            continue
        daily.append(dict(date=dt, n_rain=len(r), n_cells=len(cell),
                          diff=(cell[1.0] - cell[0.0]).mean()))
    dd = pd.DataFrame(daily)
    dd.to_csv(os.path.join(OUT, "daily_within_effect.csv"), index=False)
    print("\n日別: 同日・同路線・同時間帯での 雨あり−雨なし 平均遅延差(秒)")
    print(dd.round(1).to_string(index=False))
    if len(dd):
        print(f"日別差の平均 {dd['diff'].mean():.1f} 秒 / 中央値 {dd['diff'].median():.1f} 秒 / "
              f"正の日 {(dd['diff'] > 0).sum()}/{len(dd)}")

    # --- 図 ---
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["Hiragino Sans", "AppleGothic", "sans-serif"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    cls = pd.cut(d["precipitation10m_mm"], [-1, 0, 0.9, 100],
                 labels=["0mm", "0.5mm", "1.0mm以上"])
    m = d.groupby(cls, observed=True)["delay_seconds"].agg(["median", "mean", "size"])
    ax[0].bar(m.index.astype(str), m["median"], color="#4C78A8")
    for i, (k, r) in enumerate(m.iterrows()):
        ax[0].text(i, r["median"], f"n={int(r['size']):,}", ha="center", va="bottom", fontsize=8)
    ax[0].set_title("降水区分別の遅延中央値（調整なし）")
    ax[0].set_ylabel("秒")
    if len(dd):
        ax[1].bar(dd["date"].str.slice(5), dd["diff"], color=np.where(dd["diff"] > 0, "#E45756", "#4C78A8"))
        ax[1].axhline(0, color="k", lw=0.8)
        ax[1].set_title("日別: 同路線・同時間帯の 雨あり−雨なし 差(秒)")
        ax[1].tick_params(axis="x", rotation=60)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "prelim.png"), dpi=130)
    print("図:", os.path.join(OUT, "prelim.png"))


if __name__ == "__main__":
    sys.exit(main())
