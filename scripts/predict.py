from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.model import predict_one


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Predict L/Q from one single-inductor geometry.")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--r0", type=float, required=True)
    parser.add_argument("--W", type=float, required=True)
    parser.add_argument("--S", type=float, required=True)
    parser.add_argument("--N", type=float, required=True)
    args = parser.parse_args()
    pred = predict_one(args.model, args.r0, args.W, args.S, args.N)
    for key, value in pred.items():
        unit = " nH" if key.startswith("L_") else ""
        print(f"{key}={value:.6f}{unit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

