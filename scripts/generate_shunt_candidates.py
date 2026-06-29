from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.candidates import Candidate, candidate_name, write_manifest
from inductor_lq.fdl_generator import write_fdl
from inductor_lq.geometry import InductorParams


def shunt_name(candidate: Candidate) -> str:
    return candidate_name(candidate.n_turns, candidate.r0_um, candidate.w_um, candidate.s_um).replace("LQ_", "SH_", 1)


def load_source_candidates(path: Path, source_root: Path | None, completed_only: bool) -> list[Candidate]:
    base = source_root or path.parent
    candidates: list[Candidate] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if completed_only:
                s2p_path = Path(row["s2p_path"].replace("\\", "/"))
                if not s2p_path.is_absolute():
                    s2p_path = base / s2p_path
                if not s2p_path.exists():
                    continue
            candidates.append(
                Candidate(
                    shunt_name(
                        Candidate(
                            row["candidate_id"],
                            float(row["r0_um"]),
                            float(row["N_turns"]),
                            int(float(row["sides"])),
                            float(row["W_um"]),
                            float(row["S_um"]),
                            float(row.get("left_bridge_um") or 180.0),
                            float(row.get("right_bridge_um") or 180.0),
                        )
                    ),
                    float(row["r0_um"]),
                    float(row["N_turns"]),
                    int(float(row["sides"])),
                    float(row["W_um"]),
                    float(row["S_um"]),
                    float(row.get("left_bridge_um") or 180.0),
                    float(row.get("right_bridge_um") or 180.0),
                )
            )
    return candidates


def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
    seen: set[str] = set()
    result: list[Candidate] = []
    for candidate in candidates:
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        result.append(candidate)
    return result


def write_candidates(candidates: list[Candidate], out_root: Path) -> Path:
    rows = []
    for candidate in candidates:
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
            mode="shunt_grounded",
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

    parser = argparse.ArgumentParser(description="Generate shunt-grounded variants from an existing series manifest.")
    parser.add_argument("--source", type=Path, default=ROOT / "runs" / "overnight_v2" / "manifest.csv")
    parser.add_argument("--source-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=ROOT / "runs" / "shunt_v1")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--completed-only", action="store_true", help="Only use source rows whose S2P already exists.")
    args = parser.parse_args()

    candidates = _dedupe(load_source_candidates(args.source, args.source_root, args.completed_only))
    if args.limit is not None:
        candidates = candidates[: args.limit]
    manifest = write_candidates(candidates, args.out_root)
    print(f"generated {len(candidates)} shunt-grounded candidates")
    print(f"manifest: {manifest}")
    print("mode: shunt_grounded, EMX port remains Pdiff=P1:P2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
