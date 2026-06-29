from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.optimizer import optimized_output_name, rank_designs, write_design_fdl


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate the best-Q FDL for a target L@3.75GHz.")
    parser.add_argument("--target-L", type=float, required=True, help="Target L@3.75GHz in nH.")
    parser.add_argument("--tol", type=float, default=0.05, help="Allowed L error in nH before maximizing Q.")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "runs" / "optimized")
    parser.add_argument("--top", type=int, default=8, help="Number of ranked candidates to print and write to summary.")
    parser.add_argument("--r0-step", type=float, default=0.25, help="Interpolation step in um within validated r0 bands.")
    parser.add_argument("--l-model", default=None, help="Model used for L prediction; default uses model surrogate.")
    parser.add_argument("--q-model", default="linear", help="Model used for Q ranking; default is linear.")
    args = parser.parse_args()

    ranked = rank_designs(
        model_path=args.model,
        dataset_path=args.dataset,
        target_l_nh=args.target_L,
        tolerance_nh=args.tol,
        r0_step_um=args.r0_step,
        l_model_name=args.l_model,
        q_model_name=args.q_model,
    )
    best = ranked[0]
    name = optimized_output_name(args.target_L, best)
    fdl_path = args.out_dir / f"{name}.py"
    write_design_fdl(fdl_path, best)
    summary_path = args.out_dir / f"{name}.json"
    summary = {
        "target_L_3p75_nH": args.target_L,
        "tolerance_nH": args.tol,
        "selected_fdl": str(fdl_path),
        "selection_policy": "maximize Q_3p75 within tolerance; otherwise minimize |L error|",
        "L_model": args.l_model or "surrogate",
        "Q_model": args.q_model,
        "top_candidates": [item.as_dict() for item in ranked[: args.top]],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"target_L_3p75_nH={args.target_L:.6f} tol={args.tol:.6f}")
    if not best.within_tolerance:
        print("warning=no candidate within tolerance; selected closest-L candidate")
    print(f"fdl={fdl_path}")
    print(f"summary={summary_path}")
    print("rank,candidate_id,L_3p75_nH,L_error_nH,Q_3p75,r0_um,N_turns,W_um,S_um,outer_radius_um,within_tol")
    for item in ranked[: args.top]:
        print(
            f"{item.rank},{item.candidate_id},{item.l_3p75_nh:.6f},{item.l_error_nh:+.6f},"
            f"{item.q_3p75:.6f},{item.r0_um:.4f},{item.n_turns:.4f},{item.w_um:.4f},"
            f"{item.s_um:.4f},{item.outer_radius_um:.4f},{int(item.within_tolerance)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
