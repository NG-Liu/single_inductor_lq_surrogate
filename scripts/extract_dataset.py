from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.model import build_dataset_from_manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Extract L/Q dataset from EMX Touchstone files.")
    parser.add_argument("--root", type=Path, default=ROOT / "runs" / "v1")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--min-l-nh", type=float, default=1.0)
    parser.add_argument("--max-l-nh", type=float, default=6.0)
    args = parser.parse_args()
    manifest = args.manifest or args.root / "manifest.csv"
    rows = build_dataset_from_manifest(manifest, args.out, args.min_l_nh, args.max_l_nh)
    accepted = sum(1 for row in rows if row.get("accepted") == "1")
    print(f"rows={len(rows)} accepted={accepted} rejected={len(rows) - accepted}")
    print(f"dataset: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

