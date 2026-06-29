from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.model import TARGET_NAMES


def finite(values: list[float]) -> list[float]:
    return [value for value in values if math.isfinite(value)]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build a compact v1 dataset/model report.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "v1_report.json")
    parser.add_argument("--batch-summary", type=Path, default=ROOT / "runs" / "v1" / "emx_batch_summary.json")
    args = parser.parse_args()

    with args.dataset.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    accepted = [row for row in rows if row.get("accepted") == "1"]
    rejected = [row for row in rows if row.get("accepted") != "1"]
    model = json.loads(args.model.read_text(encoding="utf-8"))
    batch = {}
    if args.batch_summary.exists():
        batch = json.loads(args.batch_summary.read_text(encoding="utf-8"))
    ranges = {}
    for target in TARGET_NAMES:
        values = finite([float(row[target]) for row in accepted if row.get(target)])
        if values:
            ranges[target] = {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}
    report = {
        "dataset": str(args.dataset),
        "model": str(args.model),
        "total_rows": len(rows),
        "accepted_rows": len(accepted),
        "rejected_rows": len(rejected),
        "target_ranges": ranges,
        "surrogate": model.get("surrogate"),
        "training": model.get("training"),
        "metrics": model.get("metrics"),
        "emx_batch": {
            "succeeded": len(batch.get("succeeded", [])),
            "skipped": len(batch.get("skipped", [])),
            "failed": batch.get("failed", []),
        },
        "rejected": [
            {"candidate_id": row.get("candidate_id"), "reason": row.get("reject_reason")}
            for row in rejected
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report: {args.out}")
    print(f"accepted={len(accepted)} rejected={len(rejected)} surrogate={report['surrogate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
