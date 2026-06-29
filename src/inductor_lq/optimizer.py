from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .candidates import candidate_name, format_size_token
from .fdl_generator import write_fdl
from .geometry import InductorParams
from .model import TARGET_NAMES, feature_row, predict_matrix


@dataclass(frozen=True)
class SearchBand:
    n_turns: float
    w_um: float
    s_um: float
    r0_min_um: float
    r0_max_um: float


@dataclass(frozen=True)
class RankedDesign:
    rank: int
    candidate_id: str
    r0_um: float
    n_turns: float
    w_um: float
    s_um: float
    l_3p75_nh: float
    q_3p75: float
    q_3p0: float
    q_4p5: float
    l_error_nh: float
    within_tolerance: bool

    @property
    def outer_radius_um(self) -> float:
        return self.r0_um + self.n_turns * (self.w_um + self.s_um)

    def as_dict(self) -> dict[str, float | str | bool | int]:
        return {
            "rank": self.rank,
            "candidate_id": self.candidate_id,
            "r0_um": self.r0_um,
            "N_turns": self.n_turns,
            "W_um": self.w_um,
            "S_um": self.s_um,
            "outer_radius_um": self.outer_radius_um,
            "L_3p75_nH": self.l_3p75_nh,
            "Q_3p75": self.q_3p75,
            "Q_3p0": self.q_3p0,
            "Q_4p5": self.q_4p5,
            "L_error_nH": self.l_error_nh,
            "within_tolerance": self.within_tolerance,
        }


def load_search_bands(dataset_path: Path) -> list[SearchBand]:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("accepted") == "1"]
    grouped: dict[tuple[float, float, float], list[float]] = {}
    for row in rows:
        key = (float(row["N"]), float(row["W"]), float(row["S"]))
        grouped.setdefault(key, []).append(float(row["r0"]))
    return [
        SearchBand(n_turns=n, w_um=w, s_um=s, r0_min_um=min(r0s), r0_max_um=max(r0s))
        for (n, w, s), r0s in sorted(grouped.items())
    ]


def _frange(start: float, stop: float, step: float) -> list[float]:
    count = max(1, int(round((stop - start) / step)) + 1)
    values = [start + i * step for i in range(count)]
    if values[-1] < stop:
        values.append(stop)
    return [round(min(value, stop), 6) for value in values]


def rank_designs(
    model_path: Path,
    dataset_path: Path,
    target_l_nh: float,
    tolerance_nh: float,
    r0_step_um: float = 0.25,
    l_model_name: str | None = None,
    q_model_name: str = "linear",
) -> list[RankedDesign]:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    l_model = model["models"][l_model_name or model["surrogate"]]
    q_model = model["models"][q_model_name]
    candidates: list[RankedDesign] = []
    for band in load_search_bands(dataset_path):
        for r0 in _frange(band.r0_min_um, band.r0_max_um, r0_step_um):
            x = feature_row(r0, band.w_um, band.s_um, band.n_turns)
            l_pred = predict_matrix(l_model, x)[0]
            q_pred = predict_matrix(q_model, x)[0]
            targets = {name: float(value) for name, value in zip(TARGET_NAMES, l_pred)}
            q_targets = {name: float(value) for name, value in zip(TARGET_NAMES, q_pred)}
            l_value = targets["L_3p75_nH"]
            l_error = l_value - target_l_nh
            cid = candidate_name(band.n_turns, r0, band.w_um, band.s_um)
            candidates.append(
                RankedDesign(
                    rank=0,
                    candidate_id=cid,
                    r0_um=r0,
                    n_turns=band.n_turns,
                    w_um=band.w_um,
                    s_um=band.s_um,
                    l_3p75_nh=l_value,
                    q_3p75=q_targets["Q_3p75"],
                    q_3p0=q_targets["Q_3p0"],
                    q_4p5=q_targets["Q_4p5"],
                    l_error_nh=l_error,
                    within_tolerance=abs(l_error) <= tolerance_nh,
                )
            )
    feasible = [item for item in candidates if item.within_tolerance]
    infeasible = [item for item in candidates if not item.within_tolerance]
    ordered = sorted(feasible, key=lambda item: (-item.q_3p75, abs(item.l_error_nh), item.outer_radius_um)) + sorted(
        infeasible,
        key=lambda item: (abs(item.l_error_nh), -item.q_3p75, item.outer_radius_um),
    )
    return [
        RankedDesign(
            rank=index,
            candidate_id=item.candidate_id,
            r0_um=item.r0_um,
            n_turns=item.n_turns,
            w_um=item.w_um,
            s_um=item.s_um,
            l_3p75_nh=item.l_3p75_nh,
            q_3p75=item.q_3p75,
            q_3p0=item.q_3p0,
            q_4p5=item.q_4p5,
            l_error_nh=item.l_error_nh,
            within_tolerance=item.within_tolerance,
        )
        for index, item in enumerate(ordered, start=1)
    ]


def optimized_output_name(target_l_nh: float, design: RankedDesign) -> str:
    return f"OPT_L{format_size_token(target_l_nh)}_{design.candidate_id}"


def write_design_fdl(path: Path, design: RankedDesign, sides: int = 12) -> None:
    write_fdl(
        path,
        InductorParams(
            name="L1",
            r0=design.r0_um,
            n_turns=design.n_turns,
            width=design.w_um,
            spacing=design.s_um,
            left_bridge=180.0,
            right_bridge=180.0,
        ),
        sides=sides,
    )


def manifest_row(design: RankedDesign, fdl_dir: str = "fdl", skill_dir: str = "skill", gds_dir: str = "gds", s2p_dir: str = "s2p") -> dict[str, object]:
    return {
        "candidate_id": design.candidate_id,
        "r0_um": design.r0_um,
        "N_turns": design.n_turns,
        "sides": 12,
        "W_um": design.w_um,
        "S_um": design.s_um,
        "left_bridge_um": 180.0,
        "right_bridge_um": 180.0,
        "fdl_path": f"{fdl_dir}/{design.candidate_id}.py",
        "skill_path": f"{skill_dir}/{design.candidate_id}.il",
        "gds_path": f"{gds_dir}/{design.candidate_id}.gds",
        "s2p_path": f"{s2p_dir}/{design.candidate_id}.s2p",
    }
