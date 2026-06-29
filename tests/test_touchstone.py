from __future__ import annotations

from pathlib import Path

from inductor_lq.touchstone import extract_lq


ROOT = Path(__file__).resolve().parents[1]


def test_emx_and_ultraem_validation_case_match() -> None:
    emx = extract_lq(ROOT / "data" / "examples" / "inductor_validation_12gon_emx.s2p")
    ultra = extract_lq(ROOT / "data" / "examples" / "l_test.s2p")
    d_l_pct = (emx["L_3p75_nH"] - ultra["L_3p75_nH"]) / ultra["L_3p75_nH"] * 100.0
    assert abs(d_l_pct - 0.0686) < 0.01
    assert abs(emx["L_3p75_nH"] - 3.666212) < 0.001
