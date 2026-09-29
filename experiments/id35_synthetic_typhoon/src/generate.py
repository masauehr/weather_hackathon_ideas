"""学習済みCVAEから、指定した強度条件（最低気圧）の台風ライフサイクルを合成する。

観測範囲内の条件（例: 950hPa）で生成すれば「よくある強い台風」の再現、
観測史上最低(870hPa)を下回る条件（例: 850hPa）で生成すれば「もっと強い台風」の
合成シナリオになる。
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from build_dataset import N_POINTS
from train_cvae import CVAE, MODEL_PATH, normalize_pressure, denormalize_pressure

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "results"


def load_model() -> CVAE:
    model = CVAE()
    model.load_state_dict(torch.load(MODEL_PATH))
    model.eval()
    return model


def sample(model: CVAE, target_min_pressure: float, n_samples: int = 5, seed: int = 0):
    """target_min_pressure(hPa)を条件として n_samples 本のライフサイクル系列を生成する。"""
    torch.manual_seed(seed)
    c_val = normalize_pressure(np.float32(target_min_pressure))
    c = torch.full((n_samples, 1), float(c_val), dtype=torch.float32)
    z = torch.randn(n_samples, model.enc_mu.out_features)
    with torch.no_grad():
        recon = model.decode(z, c)
    seqs = denormalize_pressure(recon.numpy())
    return seqs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pressure", type=float, default=850.0,
                         help="合成したい最低気圧(hPa)。観測史上最低は870hPa（1979年台風20号）")
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    model = load_model()
    seqs = sample(model, args.pressure, args.n)

    out = {
        "target_min_pressure_hpa": args.pressure,
        "n_points": N_POINTS,
        "samples": [
            {
                "pressure_sequence_hpa": [round(float(v), 1) for v in seq],
                "actual_min_pressure_hpa": round(float(seq.min()), 1),
            }
            for seq in seqs
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"synthetic_{int(args.pressure)}hpa.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"生成: {args.n}本, 条件={args.pressure}hPa -> {out_path}")
    for s in out["samples"]:
        print(f"  実際の最低気圧={s['actual_min_pressure_hpa']}hPa")


if __name__ == "__main__":
    main()
