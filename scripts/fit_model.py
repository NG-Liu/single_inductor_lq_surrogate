from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.model import fit_model


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Fit the single-inductor L/Q surrogate model.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--model-out", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    args = parser.parse_args()
    model = fit_model(args.dataset, args.model_out, val_ratio=args.val_ratio)
    print(f"model: {args.model_out}")
    print(f"surrogate={model['surrogate']}")
    for name, metrics in model["metrics"].items():
        print(f"{name}: rmse_L={metrics['rmse_L_3p75_nH']:.6f} rmse_Q={metrics['rmse_Q_3p75']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

