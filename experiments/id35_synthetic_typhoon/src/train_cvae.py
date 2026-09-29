"""条件付きVAE（Conditional VAE）で台風の中心気圧ライフサイクル（20点）を学習する。

条件（condition）= 最低気圧（強度）を正規化した値。学習後、観測範囲を超える
「もっと強い」条件（例: 観測史上最低の870hPaより低い850hPa等）を与えて
サンプリングすることで、合成シナリオを生成する（generate.py）。

モデルはCPUで数秒〜数十秒で学習が終わる小規模構成（隠れ層32、20エポック程度）。
"""
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

from build_dataset import N_POINTS

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_PATH = PROCESSED_DIR / "cvae.pt"

LATENT_DIM = 4
HIDDEN_DIM = 32
EPOCHS = 300
LR = 1e-3

# 正規化の基準（観測データのレンジに基づく固定値。学習・生成で共有する）
PRESSURE_MIN = 850.0   # 史上最低870hPaより余裕を持たせた下限（合成の余地を作る）
PRESSURE_MAX = 1015.0


def normalize_pressure(p):
    return (p - PRESSURE_MIN) / (PRESSURE_MAX - PRESSURE_MIN)


def denormalize_pressure(x):
    return x * (PRESSURE_MAX - PRESSURE_MIN) + PRESSURE_MIN


class CVAE(nn.Module):
    def __init__(self, seq_len=N_POINTS, latent_dim=LATENT_DIM, hidden=HIDDEN_DIM):
        super().__init__()
        self.seq_len = seq_len
        # エンコーダ: (系列 + 条件) -> 潜在分布
        self.enc = nn.Sequential(
            nn.Linear(seq_len + 1, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
        )
        self.enc_mu = nn.Linear(hidden, latent_dim)
        self.enc_logvar = nn.Linear(hidden, latent_dim)
        # デコーダ: (潜在変数 + 条件) -> 系列
        self.dec = nn.Sequential(
            nn.Linear(latent_dim + 1, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, seq_len),
        )

    def encode(self, x, c):
        h = self.enc(torch.cat([x, c], dim=1))
        return self.enc_mu(h), self.enc_logvar(h)

    def decode(self, z, c):
        return self.dec(torch.cat([z, c], dim=1))

    def forward(self, x, c):
        mu, logvar = self.encode(x, c)
        std = torch.exp(0.5 * logvar)
        z = mu + std * torch.randn_like(std)
        recon = self.decode(z, c)
        return recon, mu, logvar


def loss_fn(recon, x, mu, logvar, beta=0.1):
    recon_loss = nn.functional.mse_loss(recon, x, reduction="mean")
    kl = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + beta * kl, recon_loss, kl


def load_training_arrays():
    df = pd.read_csv(PROCESSED_DIR / "typhoon_sequences.csv")
    pcols = [f"pressure_{i}" for i in range(N_POINTS)]
    seqs = normalize_pressure(df[pcols].to_numpy(dtype=np.float32))
    # 条件 = 系列内の最低気圧（=強度）を正規化したもの
    cond = normalize_pressure(df[pcols].min(axis=1).to_numpy(dtype=np.float32))
    return seqs, cond


def train():
    seqs, cond = load_training_arrays()
    x = torch.tensor(seqs, dtype=torch.float32)
    c = torch.tensor(cond, dtype=torch.float32).unsqueeze(1)

    torch.manual_seed(0)
    model = CVAE()
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    n = x.shape[0]
    for epoch in range(1, EPOCHS + 1):
        perm = torch.randperm(n)
        total, total_recon, total_kl = 0.0, 0.0, 0.0
        for i in range(0, n, 64):
            idx = perm[i:i + 64]
            xb, cb = x[idx], c[idx]
            recon, mu, logvar = model(xb, cb)
            loss, recon_loss, kl = loss_fn(recon, xb, mu, logvar)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total += loss.item() * len(idx)
            total_recon += recon_loss.item() * len(idx)
            total_kl += kl.item() * len(idx)
        if epoch % 50 == 0 or epoch == 1:
            print(f"epoch {epoch:4d}  loss={total/n:.5f}  "
                  f"recon={total_recon/n:.5f}  kl={total_kl/n:.5f}")

    torch.save(model.state_dict(), MODEL_PATH)
    print(f"モデル保存: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train()
