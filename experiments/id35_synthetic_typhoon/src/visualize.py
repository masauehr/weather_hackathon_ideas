"""ID-35スパイクの結果を視覚的に説明するための図を一括生成する。

生成する図（results/figs/）:
  01_real_lifecycles.png   実データ: 台風のライフサイクル（気圧の推移）を強度別に着色
  02_cvae_diagram.png      CVAEの仕組みの概念図（エンコーダ/デコーダ/条件）
  03_insample_compare.png  観測範囲内(950hPa)条件: 生成 vs 実データの重ね書き
  04_extrapolate_fail.png  観測範囲外(820hPa)条件: 目標と実際の生成結果のズレを可視化
  05_condition_gap.png     条件(目標気圧) vs 実際の生成結果のズレ（外挿するほど拡大）
  06_pressure_wind.png     気圧-風速の物理的関係（実データ）と外挿域
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd
import torch

from build_dataset import N_POINTS
from train_cvae import CVAE, MODEL_PATH, normalize_pressure, denormalize_pressure
from generate import sample

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FIG_DIR = BASE_DIR / "results" / "figs"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.size"] = 11
plt.rcParams["font.family"] = "Hiragino Sans"  # 日本語グリフ対応（macOS標準フォント）
X_PCT = np.linspace(0, 100, N_POINTS)


def load_model() -> CVAE:
    model = CVAE()
    model.load_state_dict(torch.load(MODEL_PATH))
    model.eval()
    return model


def fig01_real_lifecycles(df: pd.DataFrame):
    pcols = [f"pressure_{i}" for i in range(N_POINTS)]
    rng = np.random.default_rng(0)
    sample_df = df.sample(n=min(80, len(df)), random_state=0)

    fig, ax = plt.subplots(figsize=(8, 5))
    norm = plt.Normalize(df["min_pressure"].min(), df["min_pressure"].max())
    cmap = plt.get_cmap("turbo_r")
    for _, row in sample_df.iterrows():
        seq = row[pcols].to_numpy(dtype=float)
        ax.plot(X_PCT, seq, color=cmap(norm(row["min_pressure"])), alpha=0.6, lw=1)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("最低気圧 (hPa) ＝ 強度（低いほど強い）")
    ax.set_xlabel("台風のライフサイクル (発生0% → 消滅100%)")
    ax.set_ylabel("中心気圧 (hPa)")
    ax.set_title("① 実データ: 台風の中心気圧の推移（ランダム80個）\n気象庁ベストトラック 1951年〜")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "01_real_lifecycles.png", dpi=140)
    plt.close(fig)


def fig02_cvae_diagram():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7.4)
    ax.axis("off")

    def box(x, y, w, h, text, color="#dbeafe", fontsize=10.5):
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                            linewidth=1.4, edgecolor="#334155", facecolor=color)
        ax.add_patch(b)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)

    def arrow(x1, y1, x2, y2):
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                             linewidth=1.6, color="#334155")
        ax.add_patch(a)

    # 学習フェーズ
    ax.text(0.2, 6.9, "【学習】実データから「圧縮のしかた」を学ぶ", ha="left", fontsize=13, weight="bold")
    box(0.3, 4.9, 1.9, 1.1, "実データの\n気圧系列\n(20点)", color="#fef3c7")
    arrow(2.2, 5.45, 3.1, 5.45)
    box(3.1, 4.9, 2.2, 1.1, "エンコーダ\n(系列→特徴量に圧縮)", color="#dbeafe")
    arrow(5.3, 5.45, 6.2, 5.45)
    box(6.2, 4.9, 2.3, 1.1, "潜在変数 z\n(小さな数値の組)\n＋ 条件 c\n(最低気圧)", color="#e9d5ff")
    arrow(8.5, 5.45, 9.4, 5.45)
    box(9.4, 4.9, 2.3, 1.1, "デコーダ\n(z, cから系列を復元)", color="#dbeafe")

    arrow(10.55, 4.9, 10.55, 3.75)
    box(7.9, 2.75, 4.9, 1.0, "復元した系列を元データと比較\n→ 近づくよう学習", color="#fee2e2", fontsize=10)

    # 生成フェーズ
    ax.text(0.2, 2.05, "【生成】学習後、zをランダムに、条件だけ変えて", ha="left", fontsize=13, weight="bold")
    ax.text(0.2, 1.65, "新しい系列を作る", ha="left", fontsize=13, weight="bold")
    box(0.3, 0.3, 2.1, 1.0, "z: N(0,1)から\nランダムに1つ選ぶ", color="#e9d5ff", fontsize=10)
    arrow(2.4, 0.8, 3.3, 0.8)
    box(3.3, 0.3, 1.9, 1.0, "条件 c\n(欲しい強さ)", color="#e9d5ff", fontsize=10)
    arrow(5.2, 0.8, 6.1, 0.8)
    box(6.1, 0.3, 2.1, 1.0, "デコーダ\n(学習済み)", color="#dbeafe", fontsize=10)
    arrow(8.2, 0.8, 9.1, 0.8)
    box(9.1, 0.3, 2.1, 1.0, "合成された\n気圧系列", color="#fef3c7", fontsize=10)

    fig.suptitle("② CVAE（条件付き変分自己符号化器）の仕組み", fontsize=14, y=0.99)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "02_cvae_diagram.png", dpi=140)
    plt.close(fig)


def _nearest_real(df, pcols, target_min_p, k=5):
    idx = (df["min_pressure"] - target_min_p).abs().nsmallest(k).index
    return df.loc[idx, pcols].to_numpy(dtype=float)


def fig03_insample_compare(df: pd.DataFrame, model: CVAE):
    pcols = [f"pressure_{i}" for i in range(N_POINTS)]
    target = 950.0
    real_seqs = _nearest_real(df, pcols, target, k=6)
    gen_seqs = sample(model, target, n_samples=6, seed=3)

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, seq in enumerate(real_seqs):
        ax.plot(X_PCT, seq, color="#2563eb", alpha=0.7, lw=1.6,
                label="実データ（最低気圧が近い台風）" if i == 0 else None)
    for i, seq in enumerate(gen_seqs):
        ax.plot(X_PCT, seq, color="#dc2626", alpha=0.7, lw=1.6, ls="--",
                label="CVAE生成（条件=950hPa）" if i == 0 else None)
    ax.axhline(target, color="gray", ls=":", lw=1)
    ax.text(101, target, "目標950hPa", va="center", fontsize=9, color="gray")
    ax.invert_yaxis()
    ax.set_xlabel("台風のライフサイクル (%)")
    ax.set_ylabel("中心気圧 (hPa)")
    ax.set_title("③ 観測範囲内(950hPa)なら生成はうまくいく\n実データ vs CVAE生成の重ね書き")
    ax.legend(loc="lower center")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "03_insample_compare.png", dpi=140)
    plt.close(fig)


def fig04_extrapolate_fail(df: pd.DataFrame, model: CVAE):
    pcols = [f"pressure_{i}" for i in range(N_POINTS)]
    target = 820.0
    obs_min = df["min_pressure"].min()
    real_extreme = _nearest_real(df, pcols, obs_min, k=1)[0]  # 観測史上最強(1979年台風20号)
    gen_seqs = sample(model, target, n_samples=6, seed=4)

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, seq in enumerate(gen_seqs):
        ax.plot(X_PCT, seq, color="#dc2626", alpha=0.7, lw=1.6, ls="--",
                label="CVAE生成（条件=820hPa指定）" if i == 0 else None)
    ax.plot(X_PCT, real_extreme, color="#111827", lw=2.2,
             label=f"観測史上最強の実データ（最低{obs_min:.0f}hPa, 1979年台風20号）")
    ax.axhline(target, color="#dc2626", ls=":", lw=1.4)
    ax.text(101, target, "目標820hPa\n(指定した強さ)", va="center", fontsize=9, color="#dc2626")
    ax.invert_yaxis()
    ax.set_xlabel("台風のライフサイクル (%)")
    ax.set_ylabel("中心気圧 (hPa)")
    ax.set_title("④ 観測範囲外(820hPa)を指定しても届かない\n生成結果は観測史上最強(870hPa)付近に留まる")
    ax.legend(loc="lower center", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "04_extrapolate_fail.png", dpi=140)
    plt.close(fig)


def fig05_condition_gap(model: CVAE, obs_min: float):
    targets = np.array([995, 990, 980, 970, 950, 930, 920, 900, 880,
                         obs_min - 5, obs_min - 20, obs_min - 40, obs_min - 60])
    actuals = []
    for t in targets:
        seqs = sample(model, float(t), n_samples=5, seed=5)
        actuals.append(seqs.min(axis=1).mean())
    actuals = np.array(actuals)

    fig, ax = plt.subplots(figsize=(7, 6))
    lims = [min(targets.min(), actuals.min()) - 5, max(targets.max(), actuals.max()) + 5]
    ax.plot(lims, lims, color="gray", ls=":", lw=1.5, label="理想（目標=実際）")
    ax.axvspan(lims[0], obs_min, color="#fee2e2", alpha=0.5,
               label=f"観測範囲外（史上最低{obs_min:.0f}hPaより強い）")
    ax.plot(targets, actuals, "o-", color="#dc2626", lw=1.8, ms=6, label="CVAEの実際の生成結果")
    ax.set_xlabel("指定した目標の最低気圧 (hPa)")
    ax.set_ylabel("実際に生成された最低気圧 (hPa)")
    ax.set_title("⑤ 条件追従性: 観測範囲から離れるほどズレが拡大")
    ax.invert_xaxis()
    ax.invert_yaxis()
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "05_condition_gap.png", dpi=140)
    plt.close(fig)


def fig06_pressure_wind(df: pd.DataFrame):
    d = df[df["has_wind"]].copy()
    dp = 1010 - d["min_pressure"]
    coef = np.polyfit(dp, d["peak_wind_kt"], 1)
    dp_max_obs = dp.max()

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.scatter(dp, d["peak_wind_kt"], s=12, alpha=0.35, color="#2563eb", label="実データ（1977年以降）")
    x_line = np.linspace(0, dp_max_obs * 1.6, 100)
    ax.plot(x_line[x_line <= dp_max_obs], (coef[0] * x_line + coef[1])[x_line <= dp_max_obs],
            color="#111827", lw=2, label="回帰式（観測範囲内）")
    ax.plot(x_line[x_line >= dp_max_obs], (coef[0] * x_line + coef[1])[x_line >= dp_max_obs],
            color="#dc2626", lw=2, ls="--", label="同じ式の外挿（観測範囲外・信頼性なし）")
    ax.axvline(dp_max_obs, color="gray", ls=":", lw=1)
    ax.set_xlabel("気圧の低下量 = 1010 − 最低気圧 (hPa)")
    ax.set_ylabel("記録されている最大風速 (kt)")
    ax.set_title(f"⑥ 気圧と風速の関係（実データ, r≈{np.corrcoef(dp, d['peak_wind_kt'])[0,1]:.2f}）\n"
                 "観測範囲を超える示唆風速は外挿であり保証されない")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "06_pressure_wind.png", dpi=140)
    plt.close(fig)


def main():
    df = pd.read_csv(PROCESSED_DIR / "typhoon_sequences.csv")
    model = load_model()
    obs_min = df["min_pressure"].min()

    fig01_real_lifecycles(df)
    fig02_cvae_diagram()
    fig03_insample_compare(df, model)
    fig04_extrapolate_fail(df, model)
    fig05_condition_gap(model, obs_min)
    fig06_pressure_wind(df)
    print(f"図を保存: {FIG_DIR}")


if __name__ == "__main__":
    main()
