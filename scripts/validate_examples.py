from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.touchstone import extract_lq


def main() -> int:
    emx = extract_lq(ROOT / "data" / "examples" / "inductor_validation_12gon_emx.s2p")
    ultra = extract_lq(ROOT / "data" / "examples" / "l_test.s2p")
    d_l_pct = (emx["L_3p75_nH"] - ultra["L_3p75_nH"]) / ultra["L_3p75_nH"] * 100.0
    print(f"EMX L@3.75GHz: {emx['L_3p75_nH']:.6f} nH")
    print(f"UltraEM L@3.75GHz: {ultra['L_3p75_nH']:.6f} nH")
    print(f"Delta L: {d_l_pct:.4f}%")
    if abs(d_l_pct - 0.0686) > 0.01:
        raise SystemExit("Touchstone differential regression failed")
    print("example regression ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

