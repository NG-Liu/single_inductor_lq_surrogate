from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.candidates import format_size_token, write_manifest
from inductor_lq.optimizer import manifest_row, rank_designs, write_design_fdl


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Propose best-Q target-L candidates and generate FDL/manifest for EMX.")
    parser.add_argument("--target-L", type=float, required=True, help="Target L@3.75GHz in nH.")
    parser.add_argument("--tol", type=float, default=0.05, help="Allowed L error in nH for the high-Q candidate pool.")
    parser.add_argument("--top", type=int, default=20, help="Number of FDL candidates to generate.")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--r0-step", type=float, default=0.25)
    parser.add_argument("--per-band-limit", type=int, default=4, help="Maximum candidates per (N,W,S) band to keep proposal diverse.")
    parser.add_argument("--max-error", type=float, default=0.25, help="Maximum predicted L error in nH for generated candidates.")
    parser.add_argument("--l-model", default=None, help="Model used for L prediction; default uses model surrogate.")
    parser.add_argument("--q-model", default="linear", help="Model used for Q ranking; default is linear.")
    args = parser.parse_args()

    out_root = args.out_root or ROOT / "runs" / f"target_L{format_size_token(args.target_L)}"
    ranked = rank_designs(
        model_path=args.model,
        dataset_path=args.dataset,
        target_l_nh=args.target_L,
        tolerance_nh=args.tol,
        r0_step_um=args.r0_step,
        l_model_name=args.l_model,
        q_model_name=args.q_model,
    )
    selected = []
    band_counts: dict[tuple[float, float, float], int] = {}
    for item in ranked:
        if abs(item.l_error_nh) > args.max_error:
            continue
        key = (item.n_turns, item.w_um, item.s_um)
        if band_counts.get(key, 0) >= args.per_band_limit:
            continue
        selected.append(item)
        band_counts[key] = band_counts.get(key, 0) + 1
        if len(selected) >= args.top:
            break
    rows = []
    for item in selected:
        fdl_path = out_root / "fdl" / f"{item.candidate_id}.py"
        write_design_fdl(fdl_path, item)
        rows.append(manifest_row(item))
    manifest = out_root / "manifest.csv"
    write_manifest(manifest, rows)
    summary = {
        "target_L_3p75_nH": args.target_L,
        "tolerance_nH": args.tol,
        "top": args.top,
        "manifest": str(manifest),
        "selection_policy": "rank by predicted Q_3p75 within target-L tolerance; fallback to closest L",
        "per_band_limit": args.per_band_limit,
        "max_error_nH": args.max_error,
        "L_model": args.l_model or "surrogate",
        "Q_model": args.q_model,
        "candidates": [item.as_dict() for item in selected],
    }
    summary_path = out_root / "proposal.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"proposal={summary_path}")
    print(f"manifest={manifest}")
    print("rank,candidate_id,pred_L_3p75_nH,pred_L_error_nH,pred_Q_3p75,r0_um,N_turns,W_um,S_um,outer_radius_um,within_tol")
    if len(selected) < args.top:
        print(f"warning=only {len(selected)} candidates satisfy max-error={args.max_error:.6f} nH")
    for proposal_rank, item in enumerate(selected, start=1):
        print(
            f"{proposal_rank},{item.candidate_id},{item.l_3p75_nh:.6f},{item.l_error_nh:+.6f},"
            f"{item.q_3p75:.6f},{item.r0_um:.4f},{item.n_turns:.4f},{item.w_um:.4f},"
            f"{item.s_um:.4f},{item.outer_radius_um:.4f},{int(item.within_tolerance)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
