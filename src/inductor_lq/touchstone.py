from __future__ import annotations

import math
import cmath
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Touchstone:
    freqs_hz: list[float]
    data: list[list[complex]]
    z0: float
    ports: int


def _complex_pair(a: float, b: float, fmt: str) -> complex:
    if fmt == "ri":
        return complex(a, b)
    if fmt == "ma":
        return a * cmath.exp(1j * math.radians(b))
    if fmt == "db":
        return 10 ** (a / 20.0) * cmath.exp(1j * math.radians(b))
    raise ValueError(f"Unsupported Touchstone format: {fmt}")


def read_touchstone(path: Path) -> Touchstone:
    unit = "hz"
    fmt = "ma"
    z0 = 50.0
    rows: list[list[float]] = []
    for raw in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            tokens = [t.lower() for t in line[1:].split()]
            for idx, token in enumerate(tokens):
                if token in {"hz", "khz", "mhz", "ghz"}:
                    unit = token
                elif token in {"ri", "ma", "db"}:
                    fmt = token
                elif token == "r" and idx + 1 < len(tokens):
                    z0 = float(tokens[idx + 1])
            continue
        if "!" in line:
            line = line.split("!", 1)[0].strip()
        values = [float(v) for v in line.replace(",", " ").split()]
        if values:
            rows.append(values)
    if not rows:
        raise ValueError(f"No S-parameter rows found in {path}")
    scale = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}[unit]
    value_count = len(rows[0]) - 1
    ports = 1 if value_count == 2 else 2 if value_count == 8 else 0
    if ports == 0:
        raise ValueError(f"Only 1-port and 2-port Touchstone rows are supported: {path}")
    freqs: list[float] = []
    data: list[list[complex]] = []
    for row in rows:
        freqs.append(row[0] * scale)
        data.append([_complex_pair(a, b, fmt) for a, b in zip(row[1::2], row[2::2])])
    return Touchstone(freqs, data, z0, ports)


def s2_to_z(s11: complex, s21: complex, s12: complex, s22: complex, z0: float) -> np.ndarray:
    smat = np.array([[s11, s12], [s21, s22]], dtype=complex)
    ident = np.eye(2, dtype=complex)
    return z0 * (ident + smat) @ np.linalg.inv(ident - smat)


def zdiff_series(ts: Touchstone) -> list[complex]:
    if ts.ports == 1:
        return [ts.z0 * (1.0 + row[0]) / (1.0 - row[0]) for row in ts.data]
    zdiffs: list[complex] = []
    for row in ts.data:
        s11, s21, s12, s22 = row
        z = s2_to_z(s11, s21, s12, s22, ts.z0)
        zdiffs.append(z[0, 0] + z[1, 1] - z[0, 1] - z[1, 0])
    return zdiffs


def interp_complex(freqs_hz: list[float], values: list[complex], freq_hz: float) -> complex:
    if freq_hz <= freqs_hz[0]:
        return values[0]
    if freq_hz >= freqs_hz[-1]:
        return values[-1]
    for idx in range(1, len(freqs_hz)):
        if freqs_hz[idx] >= freq_hz:
            f0, f1 = freqs_hz[idx - 1], freqs_hz[idx]
            t = (freq_hz - f0) / (f1 - f0)
            return values[idx - 1] * (1.0 - t) + values[idx] * t
    return values[-1]


def lq_from_z(freq_hz: float, z: complex) -> tuple[float, float]:
    l_nh = z.imag / (2.0 * math.pi * freq_hz) * 1e9
    q = abs(z.imag / z.real) if abs(z.real) > 1e-15 else float("inf")
    return l_nh, q


def extract_lq(path: Path, main_freq_ghz: float = 3.75, sample_freqs_ghz: tuple[float, ...] = (3.0, 3.5, 4.0, 4.5)) -> dict[str, float]:
    ts = read_touchstone(path)
    zdiffs = zdiff_series(ts)
    result: dict[str, float] = {}
    for freq_ghz in sample_freqs_ghz:
        z = interp_complex(ts.freqs_hz, zdiffs, freq_ghz * 1e9)
        l_nh, q = lq_from_z(freq_ghz * 1e9, z)
        key = str(freq_ghz).replace(".", "p")
        result[f"L_{key}_nH"] = l_nh
        result[f"Q_{key}"] = q
    z_main = interp_complex(ts.freqs_hz, zdiffs, main_freq_ghz * 1e9)
    l_main, q_main = lq_from_z(main_freq_ghz * 1e9, z_main)
    result["L_3p75_nH"] = l_main
    result["Q_3p75"] = q_main
    return result

