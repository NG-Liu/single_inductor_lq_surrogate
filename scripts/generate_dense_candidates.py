from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.candidates import DEFAULT_V1_CANDIDATES, Candidate, candidate_name, write_manifest
from inductor_lq.fdl_generator import write_fdl
from inductor_lq.geometry import InductorParams
from inductor_lq.model import predict_one


def _frange(start: float, stop: float, step: float) -> list[float]:
    values = []
    value = start
    while value <= stop + 1e-9:
        values.append(round(value, 6))
        value += step
    return values


def _accepted_bands(dataset: Path) -> dict[tuple[float, float, float], tuple[float, float]]:
    with dataset.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("accepted") == "1"]
    bands: dict[tuple[float, float, float], list[float]] = {}
    for row in rows:
        key = (float(row["N"]), float(row["W"]), float(row["S"]))
        bands.setdefault(key, []).append(float(row["r0"]))
    return {key: (min(values), max(values)) for key, values in bands.items()}


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen = set()
    result = []
    for candidate in candidates:
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        result.append(candidate)
    return result


def build_dense_candidates(
    dataset: Path,
    model: Path,
    r0_step_um: float,
    edge_extension_um: float,
    min_l_nh: float,
    max_l_nh: float,
) -> list[Candidate]:
    candidates = list(DEFAULT_V1_CANDIDATES)
    existing = {candidate.candidate_id for candidate in candidates}
    for (n_turns, w_um, s_um), (r0_min, r0_max) in _accepted_bands(dataset).items():
        start = max(1.0, r0_min - edge_extension_um)
        stop = r0_max + edge_extension_um
        for r0_um in _frange(start, stop, r0_step_um):
            cid = candidate_name(n_turns, r0_um, w_um, s_um)
            if cid in existing:
                continue
            pred = predict_one(model, r0_um, w_um, s_um, n_turns)
            if not (min_l_nh <= pred["L_3p75_nH"] <= max_l_nh):
                continue
            candidates.append(Candidate(cid, r0_um, n_turns, 12, w_um, s_um))
            existing.add(cid)
    return _dedupe(candidates)


def write_candidates(candidates: list[Candidate], out_root: Path) -> Path:
    fdl_dir = out_root / "fdl"
    skill_dir = out_root / "skill"
    gds_dir = out_root / "gds"
    s2p_dir = out_root / "s2p"
    rows = []
    for candidate in candidates:
        fdl_path = fdl_dir / f"{candidate.candidate_id}.py"
        write_fdl(
            fdl_path,
            InductorParams(
                "L1",
                r0=candidate.r0_um,
                n_turns=candidate.n_turns,
                width=candidate.w_um,
                spacing=candidate.s_um,
                left_bridge=candidate.left_bridge_um,
                right_bridge=candidate.right_bridge_um,
            ),
            sides=candidate.sides,
        )
        rows.append(
            {
                "candidate_id": candidate.candidate_id,
                "r0_um": candidate.r0_um,
                "N_turns": candidate.n_turns,
                "sides": candidate.sides,
                "W_um": candidate.w_um,
                "S_um": candidate.s_um,
                "left_bridge_um": candidate.left_bridge_um,
                "right_bridge_um": candidate.right_bridge_um,
                "fdl_path": str(fdl_path.relative_to(out_root)),
                "skill_path": str((skill_dir / f"{candidate.candidate_id}.il").relative_to(out_root)),
                "gds_path": str((gds_dir / f"{candidate.candidate_id}.gds").relative_to(out_root)),
                "s2p_path": str((s2p_dir / f"{candidate.candidate_id}.s2p").relative_to(out_root)),
            }
        )
    manifest = out_root / "manifest.csv"
    write_manifest(manifest, rows)
    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate a dense v1 candidate manifest by interpolating accepted data bands.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--out-root", type=Path, default=ROOT / "runs" / "v1")
    parser.add_argument("--r0-step", type=float, default=2.0)
    parser.add_argument("--edge-extension", type=float, default=2.0)
    parser.add_argument("--min-l-nh", type=float, default=1.0)
    parser.add_argument("--max-l-nh", type=float, default=6.0)
    args = parser.parse_args()

    candidates = build_dense_candidates(
        dataset=args.dataset,
        model=args.model,
        r0_step_um=args.r0_step,
        edge_extension_um=args.edge_extension,
        min_l_nh=args.min_l_nh,
        max_l_nh=args.max_l_nh,
    )
    manifest = write_candidates(candidates, args.out_root)
    existing = len(DEFAULT_V1_CANDIDATES)
    print(f"generated {len(candidates)} dense candidates ({len(candidates) - existing} beyond default v1)")
    print(f"manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
