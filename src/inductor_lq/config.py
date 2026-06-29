from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_SAMPLE_FREQS_GHZ = (3.0, 3.5, 4.0, 4.5)
DEFAULT_MAIN_FREQ_GHZ = 3.75
DEFAULT_MIN_L_NH = 1.0
DEFAULT_MAX_L_NH = 6.0


@dataclass(frozen=True)
class VmConfig:
    host: str = "192.168.37.128"
    user: str = "IC"
    password_env: str = "LVBOBALUN_VM_PASSWORD"
    remote_root: str = "/home/IC/EDA/single_inductor_lq_surrogate"
    cadence_lib: str = "codex_fdl_bridge"
    cadence_lib_path: str = "/home/IC/EDA/codex_fdl_bridge"
    tech_lib: str = "smic13mmrf_1233"
    layermap: str = "/home/IC/Tech/PDK_13mmrf_1P6M_30k/smic13mmrf_1233/smic13mmrf_1233.layermap"
    emx_bin: str = "/home/IC/EDA/INTEGRAND60/bin/emx"
    process_file: str = "/home/IC/EDA/INTEGRAND60/virtuoso_ui/emxinterface/processes/fdl_stack.proc"


def project_root_from_script(script_path: Path) -> Path:
    return script_path.resolve().parents[1]

