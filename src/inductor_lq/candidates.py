from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    r0_um: float
    n_turns: float
    sides: int
    w_um: float
    s_um: float
    left_bridge_um: float = 180.0
    right_bridge_um: float = 180.0

    @property
    def pitch_um(self) -> float:
        return self.w_um + self.s_um

    @property
    def outer_radius_um(self) -> float:
        return self.r0_um + self.n_turns * self.pitch_um

    @property
    def fill_ratio(self) -> float:
        return self.w_um / self.pitch_um


def format_size_token(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text.replace(".", "p").replace("-", "m")


def candidate_name(n_turns: float, r0_um: float, w_um: float, s_um: float) -> str:
    return (
        f"LQ_N{format_size_token(n_turns)}"
        f"_R{format_size_token(r0_um)}"
        f"_W{format_size_token(w_um)}"
        f"_S{format_size_token(s_um)}"
    )


DEFAULT_V1_CANDIDATES = [
    Candidate(candidate_name(2.5, r0, w, s), r0, 2.5, 12, w, s)
    for r0 in (48, 56, 64, 72)
    for w, s in ((9.6, 12.0), (10.4, 14.0))
] + [
    Candidate(candidate_name(3.5, r0, w, s), r0, 3.5, 12, w, s)
    for r0 in (56, 64, 72, 80)
    for w, s in ((10.4, 14.0), (10.4, 15.0))
] + [
    Candidate(candidate_name(4.5, r0, w, s), r0, 4.5, 12, w, s)
    for r0 in (60, 68, 76, 84)
    for w, s in ((10.4, 15.0), (11.2, 16.0))
]


def load_candidates_from_csv(path: Path) -> list[Candidate]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            Candidate(
                candidate_id=row["candidate_id"],
                r0_um=float(row["r0_um"]),
                n_turns=float(row["N_turns"]),
                sides=int(float(row["sides"])),
                w_um=float(row["W_um"]),
                s_um=float(row["S_um"]),
                left_bridge_um=float(row.get("left_bridge_um", 180.0)),
                right_bridge_um=float(row.get("right_bridge_um", 180.0)),
            )
            for row in reader
        ]


def write_manifest(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "candidate_id",
        "r0_um",
        "N_turns",
        "sides",
        "W_um",
        "S_um",
        "left_bridge_um",
        "right_bridge_um",
        "fdl_path",
        "skill_path",
        "gds_path",
        "s2p_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
