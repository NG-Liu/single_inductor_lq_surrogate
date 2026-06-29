from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.candidates import DEFAULT_V1_CANDIDATES, write_manifest
from inductor_lq.fdl_generator import write_fdl
from inductor_lq.geometry import InductorParams


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate v1 single-inductor FDL candidates.")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "v1_42_samples.yaml", help="Reserved config path; v1 uses the checked-in default grid.")
    parser.add_argument("--out-root", type=Path, default=ROOT / "runs" / "v1")
    args = parser.parse_args()

    fdl_dir = args.out_root / "fdl"
    skill_dir = args.out_root / "skill"
    gds_dir = args.out_root / "gds"
    s2p_dir = args.out_root / "s2p"
    rows = []
    for candidate in DEFAULT_V1_CANDIDATES:
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
                "fdl_path": str(fdl_path.relative_to(args.out_root)),
                "skill_path": str((skill_dir / f"{candidate.candidate_id}.il").relative_to(args.out_root)),
                "gds_path": str((gds_dir / f"{candidate.candidate_id}.gds").relative_to(args.out_root)),
                "s2p_path": str((s2p_dir / f"{candidate.candidate_id}.s2p").relative_to(args.out_root)),
            }
        )
    manifest = args.out_root / "manifest.csv"
    write_manifest(manifest, rows)
    print(f"generated {len(rows)} candidates")
    print(f"manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
