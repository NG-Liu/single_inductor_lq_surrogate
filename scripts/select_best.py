from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.touchstone import extract_lq


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Select the best EMX-verified target-L FDL from a proposal run.")
    parser.add_argument("--root", type=Path, required=True, help="Proposal run root containing manifest.csv and s2p/.")
    parser.add_argument("--target-L", type=float, required=True, help="Target L@3.75GHz in nH.")
    parser.add_argument("--tol", type=float, default=0.05, help="Allowed EMX L error in nH.")
    parser.add_argument("--out", type=Path, default=None, help="Best-result JSON path.")
    args = parser.parse_args()

    manifest = args.root / "manifest.csv"
    with manifest.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    evaluated = []
    for row in rows:
        s2p_path = args.root / row["s2p_path"]
        fdl_path = args.root / row["fdl_path"]
        item = {
            "candidate_id": row["candidate_id"],
            "fdl_path": str(fdl_path),
            "s2p_path": str(s2p_path),
            "r0_um": float(row["r0_um"]),
            "N_turns": float(row["N_turns"]),
            "W_um": float(row["W_um"]),
            "S_um": float(row["S_um"]),
        }
        try:
            lq = extract_lq(s2p_path)
            l_value = lq["L_3p75_nH"]
            item.update(lq)
            item["L_error_nH"] = l_value - args.target_L
            item["within_tolerance"] = abs(item["L_error_nH"]) <= args.tol
            item["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            item["error"] = str(exc)
            item["within_tolerance"] = False
        evaluated.append(item)

    ok = [item for item in evaluated if item["status"] == "ok"]
    feasible = [item for item in ok if item["within_tolerance"]]
    pool = feasible or ok
    if not pool:
        raise RuntimeError(f"No usable S2P results found under {args.root}")
    if feasible:
        best = sorted(pool, key=lambda item: (-item["Q_3p75"], abs(item["L_error_nH"])))[0]
    else:
        best = sorted(pool, key=lambda item: (abs(item["L_error_nH"]), -item["Q_3p75"]))[0]

    out = args.out or args.root / "best_result.json"
    best_fdl_copy = args.root / "best_fdl" / Path(best["fdl_path"]).name
    best_fdl_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best["fdl_path"], best_fdl_copy)
    result = {
        "target_L_3p75_nH": args.target_L,
        "tolerance_nH": args.tol,
        "selected_by": "max EMX Q_3p75 within tolerance; fallback closest EMX L",
        "best_fdl": str(best_fdl_copy),
        "best": best,
        "feasible_count": len(feasible),
        "evaluated_count": len(ok),
        "failed_count": len(evaluated) - len(ok),
        "ranked_results": sorted(
            ok,
            key=lambda item: (
                0 if item["within_tolerance"] else 1,
                -item["Q_3p75"] if item["within_tolerance"] else abs(item["L_error_nH"]),
            ),
        ),
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not best["within_tolerance"]:
        print("warning=no EMX result within tolerance; selected closest-L result")
    print(f"best_fdl={best_fdl_copy}")
    print(
        f"best={best['candidate_id']} L_3p75_nH={best['L_3p75_nH']:.6f} "
        f"L_error_nH={best['L_error_nH']:+.6f} Q_3p75={best['Q_3p75']:.6f}"
    )
    print(f"result={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
