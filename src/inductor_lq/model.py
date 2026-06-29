from __future__ import annotations

import ast
import csv
import json
import random
import re
from itertools import combinations_with_replacement
from pathlib import Path

import numpy as np

from .touchstone import extract_lq


MODEL_FEATURES = ("r0", "W", "S", "N", "pitch", "outer_radius", "fill_ratio")
TARGET_NAMES = ("L_3p75_nH", "Q_3p75", "Q_3p0", "Q_4p5")


def parse_variables_block(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Variables\(var=(\[.*?\])\)", text, re.S)
    if not match:
        raise ValueError(f"Could not find Variables(var=[...]) in {path}")
    values = ast.literal_eval(match.group(1))
    result: dict[str, float] = {}
    for item in values:
        result.update({key: float(value) for key, value in item.items()})
    return result


def features_from_fdl(path: Path) -> dict[str, float]:
    params = parse_variables_block(path)
    pitch = params["L1_W"] + params["L1_S"]
    return {
        "r0": params["L1_r0"],
        "W": params["L1_W"],
        "S": params["L1_S"],
        "N": params["N1"],
        "pitch": pitch,
        "outer_radius": params["L1_r0"] + params["N1"] * pitch,
        "fill_ratio": params["L1_W"] / pitch,
    }


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["candidate_id", "fdl_path", "s2p_path", "accepted", "reject_reason", *MODEL_FEATURES, *TARGET_NAMES]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_dataset_from_manifest(manifest_path: Path, out_path: Path, min_l_nh: float = 1.0, max_l_nh: float = 6.0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    base = manifest_path.parent
    for item in load_manifest(manifest_path):
        fdl_path = Path(item["fdl_path"].replace("\\", "/"))
        s2p_path = Path(item["s2p_path"].replace("\\", "/"))
        if not fdl_path.is_absolute():
            fdl_path = (base / fdl_path).resolve()
        if not s2p_path.is_absolute():
            s2p_path = (base / s2p_path).resolve()
        row: dict[str, object] = {"candidate_id": item["candidate_id"], "fdl_path": str(fdl_path), "s2p_path": str(s2p_path)}
        try:
            feats = features_from_fdl(fdl_path)
            targets = extract_lq(s2p_path)
            accepted = min_l_nh <= targets["L_3p75_nH"] <= max_l_nh
            row.update(feats)
            row.update({name: targets[name] for name in TARGET_NAMES})
            row["accepted"] = "1" if accepted else "0"
            row["reject_reason"] = "" if accepted else f"L_3p75_nH outside [{min_l_nh}, {max_l_nh}]"
        except Exception as exc:  # noqa: BLE001
            row["accepted"] = "0"
            row["reject_reason"] = str(exc)
            for name in (*MODEL_FEATURES, *TARGET_NAMES):
                row[name] = ""
        rows.append(row)
    write_dataset(out_path, rows)
    return rows


def _accepted_numeric(rows: list[dict[str, object]]) -> list[dict[str, float]]:
    accepted = []
    for row in rows:
        if str(row.get("accepted")) != "1":
            continue
        accepted.append({key: float(row[key]) for key in (*MODEL_FEATURES, *TARGET_NAMES)})
    return accepted


def _matrix(rows: list[dict[str, float]], fields: tuple[str, ...]) -> np.ndarray:
    return np.array([[row[field] for field in fields] for row in rows], dtype=float)


def _terms(feature_count: int, degree: int) -> list[tuple[int, ...]]:
    terms = [()]
    for deg in range(1, degree + 1):
        terms.extend(combinations_with_replacement(range(feature_count), deg))
    return terms


def _design_matrix(x: np.ndarray, terms: list[tuple[int, ...]]) -> np.ndarray:
    phi = np.ones((x.shape[0], len(terms)), dtype=float)
    for col, term in enumerate(terms[1:], start=1):
        values = np.ones(x.shape[0], dtype=float)
        for idx in term:
            values *= x[:, idx]
        phi[:, col] = values
    return phi


def _fit(x: np.ndarray, y: np.ndarray, degree: int, ridge: float) -> dict:
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0.0] = 1.0
    xs = (x - mean) / scale
    terms = _terms(x.shape[1], degree)
    phi = _design_matrix(xs, terms)
    gram = phi.T @ phi + ridge * np.eye(phi.shape[1])
    gram[0, 0] -= ridge
    coef = np.linalg.solve(gram, phi.T @ y)
    return {"degree": degree, "feature_mean": mean.tolist(), "feature_scale": scale.tolist(), "terms": [list(t) for t in terms], "coef": coef.tolist()}


def predict_matrix(model: dict, x: np.ndarray) -> np.ndarray:
    mean = np.array(model["feature_mean"], dtype=float)
    scale = np.array(model["feature_scale"], dtype=float)
    terms = [tuple(term) for term in model["terms"]]
    coef = np.array(model["coef"], dtype=float)
    return _design_matrix((x - mean) / scale, terms) @ coef


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    residual = y_true - y_pred
    rmse = np.sqrt(np.mean(residual**2, axis=0))
    ss_tot = np.sum((y_true - y_true.mean(axis=0)) ** 2, axis=0)
    r2 = np.where(ss_tot > 0, 1.0 - np.sum(residual**2, axis=0) / ss_tot, 1.0)
    return {f"rmse_{name}": float(value) for name, value in zip(TARGET_NAMES, rmse)} | {f"r2_{name}": float(value) for name, value in zip(TARGET_NAMES, r2)}


def fit_model(dataset_path: Path, model_out: Path, val_ratio: float = 0.2, seed: int = 20260629, ridge: float = 1e-8) -> dict:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = _accepted_numeric(list(csv.DictReader(f)))
    if len(rows) < 2:
        raise ValueError("Need at least 2 accepted samples to fit a model")
    rng = random.Random(seed)
    rng.shuffle(rows)
    val_count = max(1, round(len(rows) * val_ratio)) if len(rows) >= 5 else len(rows)
    val_rows = rows[:val_count]
    train_rows = rows[val_count:] or rows
    x_train = _matrix(train_rows, MODEL_FEATURES)
    y_train = _matrix(train_rows, TARGET_NAMES)
    x_val = _matrix(val_rows, MODEL_FEATURES)
    y_val = _matrix(val_rows, TARGET_NAMES)
    models = {name: _fit(x_train, y_train, degree, ridge) for name, degree in (("linear", 1), ("quadratic", 2))}
    metrics = {name: _metrics(y_val, predict_matrix(model, x_val)) for name, model in models.items()}
    choose = "quadratic" if metrics["quadratic"]["rmse_L_3p75_nH"] <= metrics["linear"]["rmse_L_3p75_nH"] else "linear"
    model = {
        "version": "single-inductor-lq-surrogate-v1",
        "input_features": list(MODEL_FEATURES),
        "output_targets": list(TARGET_NAMES),
        "surrogate": choose,
        "training": {"n_samples": len(rows), "n_train": len(train_rows), "n_val": len(val_rows), "val_ratio": val_ratio},
        "models": models,
        "metrics": metrics,
    }
    model_out.parent.mkdir(parents=True, exist_ok=True)
    model_out.write_text(json.dumps(model, indent=2), encoding="utf-8")
    return model


def feature_row(r0: float, w: float, s: float, n: float) -> np.ndarray:
    pitch = w + s
    return np.array([[r0, w, s, n, pitch, r0 + n * pitch, w / pitch]], dtype=float)


def predict_one(model_path: Path, r0: float, w: float, s: float, n: float, model_name: str | None = None) -> dict[str, float]:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    chosen = model_name or model["surrogate"]
    pred = predict_matrix(model["models"][chosen], feature_row(r0, w, s, n))[0]
    return {name: float(value) for name, value in zip(TARGET_NAMES, pred)}
