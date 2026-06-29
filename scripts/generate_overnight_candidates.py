from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.candidates import Candidate, candidate_name, write_manifest
from inductor_lq.fdl_generator import write_fdl
from inductor_lq.geometry import InductorParams
from inductor_lq.model import TARGET_NAMES, feature_row, predict_matrix


WS_PAIRS = (
    (9.6, 12.0),
    (9.6, 14.0),
    (10.4, 12.0),
    (10.4, 14.0),
    (10.4, 15.0),
    (11.2, 14.0),
    (11.2, 15.0),
    (11.2, 16.0),
    (12.0, 16.0),
    (12.0, 18.0),
)

R0_RANGES = {
    2.5: (36.0, 96.0),
    3.5: (30.0, 92.0),
    4.5: (34.0, 70.0),
}


@dataclass(frozen=True)
class PredictedCandidate:
    candidate: Candidate
    l_3p75_nh: float
    q_3p75: float
    bin_index: int

    @property
    def band_key(self) -> tuple[float, float, float]:
        return (self.candidate.n_turns, self.candidate.w_um, self.candidate.s_um)

    def as_dict(self) -> dict[str, float | str | int]:
        return {
            "candidate_id": self.candidate.candidate_id,
            "r0_um": self.candidate.r0_um,
            "N_turns": self.candidate.n_turns,
            "W_um": self.candidate.w_um,
            "S_um": self.candidate.s_um,
            "L_3p75_nH_pred": self.l_3p75_nh,
            "Q_3p75_pred": self.q_3p75,
            "bin_index": self.bin_index,
        }


def _frange(start: float, stop: float, step: float) -> list[float]:
    values = []
    value = start
    while value <= stop + 1e-9:
        values.append(round(value, 6))
        value += step
    return values


def _existing_ids(dataset_path: Path) -> set[str]:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["candidate_id"] for row in csv.DictReader(f)}


def _load_model(model_path: Path) -> dict:
    return json.loads(model_path.read_text(encoding="utf-8"))


def _predict(
    model: dict,
    r0_um: float,
    w_um: float,
    s_um: float,
    n_turns: float,
    l_model_name: str | None,
    q_model_name: str,
) -> dict[str, float]:
    l_model = model["models"][l_model_name or model["surrogate"]]
    q_model = model["models"].get(q_model_name, l_model)
    l_pred = predict_matrix(l_model, feature_row(r0_um, w_um, s_um, n_turns))[0]
    q_pred = predict_matrix(q_model, feature_row(r0_um, w_um, s_um, n_turns))[0]
    l_targets = {name: float(value) for name, value in zip(TARGET_NAMES, l_pred)}
    q_targets = {name: float(value) for name, value in zip(TARGET_NAMES, q_pred)}
    return {"L_3p75_nH": l_targets["L_3p75_nH"], "Q_3p75": q_targets["Q_3p75"]}


def build_candidates(
    dataset_path: Path,
    model_path: Path,
    target_count: int,
    r0_step_um: float,
    min_l_nh: float,
    max_l_nh: float,
    per_band_bin_limit: int,
    l_model_name: str | None,
    q_model_name: str,
) -> tuple[list[PredictedCandidate], dict[str, object]]:
    model = _load_model(model_path)
    existing = _existing_ids(dataset_path)
    bins = int(round((max_l_nh - min_l_nh) / 0.5))
    bin_target = max(1, target_count // bins)
    pool: list[PredictedCandidate] = []
    for n_turns, (r0_start, r0_stop) in R0_RANGES.items():
        for w_um, s_um in WS_PAIRS:
            for r0_um in _frange(r0_start, r0_stop, r0_step_um):
                cid = candidate_name(n_turns, r0_um, w_um, s_um)
                if cid in existing:
                    continue
                pred = _predict(model, r0_um, w_um, s_um, n_turns, l_model_name, q_model_name)
                l_value = pred["L_3p75_nH"]
                if not (min_l_nh <= l_value <= max_l_nh):
                    continue
                bin_index = min(bins - 1, int((l_value - min_l_nh) / 0.5))
                pool.append(
                    PredictedCandidate(
                        Candidate(cid, r0_um, n_turns, 12, w_um, s_um),
                        l_3p75_nh=l_value,
                        q_3p75=pred["Q_3p75"],
                        bin_index=bin_index,
                    )
                )

    selected: list[PredictedCandidate] = []
    selected_ids: set[str] = set()
    for bin_index in range(bins):
        bin_pool = [item for item in pool if item.bin_index == bin_index]
        center = min_l_nh + 0.5 * bin_index + 0.25
        bin_pool.sort(key=lambda item: (-item.q_3p75, abs(item.l_3p75_nh - center), item.candidate.outer_radius_um))
        band_counts: dict[tuple[float, float, float], int] = {}
        for item in bin_pool:
            if item.candidate.candidate_id in selected_ids:
                continue
            if band_counts.get(item.band_key, 0) >= per_band_bin_limit:
                continue
            selected.append(item)
            selected_ids.add(item.candidate.candidate_id)
            band_counts[item.band_key] = band_counts.get(item.band_key, 0) + 1
            if sum(1 for candidate in selected if candidate.bin_index == bin_index) >= bin_target:
                break

    if len(selected) < target_count:
        remaining = [item for item in pool if item.candidate.candidate_id not in selected_ids]
        remaining.sort(key=lambda item: (-item.q_3p75, item.bin_index, item.candidate.outer_radius_um))
        for item in remaining:
            selected.append(item)
            selected_ids.add(item.candidate.candidate_id)
            if len(selected) >= target_count:
                break

    selected = selected[:target_count]
    summary = {
        "target_count": target_count,
        "pool_count": len(pool),
        "selected_count": len(selected),
        "r0_step_um": r0_step_um,
        "min_l_nh": min_l_nh,
        "max_l_nh": max_l_nh,
        "per_band_bin_limit": per_band_bin_limit,
        "L_model": l_model_name or model["surrogate"],
        "Q_model": q_model_name,
        "bin_counts": {
            f"{min_l_nh + 0.5 * idx:.1f}-{min_l_nh + 0.5 * (idx + 1):.1f}": sum(1 for item in selected if item.bin_index == idx)
            for idx in range(bins)
        },
        "candidates": [item.as_dict() for item in selected],
    }
    return selected, summary


def write_candidates(candidates: list[PredictedCandidate], out_root: Path) -> Path:
    rows = []
    for item in candidates:
        candidate = item.candidate
        fdl_path = out_root / "fdl" / f"{candidate.candidate_id}.py"
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
                "fdl_path": f"fdl/{candidate.candidate_id}.py",
                "skill_path": f"skill/{candidate.candidate_id}.il",
                "gds_path": f"gds/{candidate.candidate_id}.gds",
                "s2p_path": f"s2p/{candidate.candidate_id}.s2p",
            }
        )
    manifest = out_root / "manifest.csv"
    write_manifest(manifest, rows)
    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate an overnight EMX candidate batch.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--out-root", type=Path, default=ROOT / "runs" / "overnight_v2")
    parser.add_argument("--target-count", type=int, default=600)
    parser.add_argument("--r0-step", type=float, default=1.0)
    parser.add_argument("--min-l-nh", type=float, default=1.0)
    parser.add_argument("--max-l-nh", type=float, default=6.0)
    parser.add_argument("--per-band-bin-limit", type=int, default=8)
    parser.add_argument("--l-model", default=None, help="Model used to filter L; default uses model surrogate.")
    parser.add_argument("--q-model", default="linear", help="Model used to rank Q within each L bin.")
    args = parser.parse_args()

    candidates, summary = build_candidates(
        dataset_path=args.dataset,
        model_path=args.model,
        target_count=args.target_count,
        r0_step_um=args.r0_step,
        min_l_nh=args.min_l_nh,
        max_l_nh=args.max_l_nh,
        per_band_bin_limit=args.per_band_bin_limit,
        l_model_name=args.l_model,
        q_model_name=args.q_model,
    )
    manifest = write_candidates(candidates, args.out_root)
    summary["manifest"] = str(manifest)
    summary_path = args.out_root / "proposal_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"generated {len(candidates)} overnight candidates from pool={summary['pool_count']}")
    print(f"manifest: {manifest}")
    print(f"summary: {summary_path}")
    for key, value in summary["bin_counts"].items():
        print(f"{key} nH: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
