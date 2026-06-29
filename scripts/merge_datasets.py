from __future__ import annotations

import csv
import math
from pathlib import Path


def _is_complete(row: dict[str, str]) -> bool:
    try:
        return math.isfinite(float(row.get("L_3p75_nH", ""))) and math.isfinite(float(row.get("Q_3p75", "")))
    except ValueError:
        return False


def merge_datasets(inputs: list[Path], out: Path, skip_incomplete: bool = True) -> tuple[int, int]:
    rows_by_id: dict[str, dict[str, str]] = {}
    fieldnames: list[str] = []
    skipped = 0
    for path in inputs:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not fieldnames:
                fieldnames = list(reader.fieldnames or [])
            for row in reader:
                if skip_incomplete and not _is_complete(row):
                    skipped += 1
                    continue
                cid = row["candidate_id"]
                old = rows_by_id.get(cid)
                if old is None or (not _is_complete(old) and _is_complete(row)):
                    rows_by_id[cid] = row

    rows = sorted(
        rows_by_id.values(),
        key=lambda row: (
            float(row.get("N") or 0.0),
            float(row.get("L_3p75_nH") or 0.0),
            row.get("candidate_id", ""),
        ),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), skipped


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Merge extracted L/Q datasets and dedupe by candidate_id.")
    parser.add_argument("--inputs", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--keep-incomplete", action="store_true", help="Keep rows without valid L/Q targets.")
    args = parser.parse_args()

    total, skipped = merge_datasets(args.inputs, args.out, skip_incomplete=not args.keep_incomplete)
    print(f"merged_rows={total} skipped_incomplete={skipped}")
    print(f"dataset: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
