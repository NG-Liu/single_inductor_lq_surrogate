from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _project_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _run_step(args: list[str], allow_failure: bool = False) -> int:
    print("+ " + " ".join(args), flush=True)
    result = subprocess.run(args, cwd=ROOT)
    code = result.returncode
    if code and not allow_failure:
        raise subprocess.CalledProcessError(code, args)
    return code


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the overnight v2 EMX sampling workflow end to end.")
    parser.add_argument("--root", type=Path, default=ROOT / "runs" / "overnight_v2")
    parser.add_argument("--hours", type=float, default=8.0)
    parser.add_argument("--target-count", type=int, default=600)
    parser.add_argument("--force-generate", action="store_true")
    parser.add_argument("--force-emx", action="store_true")
    parser.add_argument("--skip-emx", action="store_true", help="Only generate/postprocess; useful for smoke tests.")
    parser.add_argument("--base-dataset", type=Path, default=ROOT / "data" / "v1_dataset.csv")
    parser.add_argument("--base-model", type=Path, default=ROOT / "data" / "v1_model.json")
    parser.add_argument("--overnight-dataset", type=Path, default=ROOT / "data" / "overnight_v2_dataset.csv")
    parser.add_argument("--merged-dataset", type=Path, default=ROOT / "data" / "v2_dataset.csv")
    parser.add_argument("--model-out", type=Path, default=ROOT / "data" / "v2_model.json")
    parser.add_argument("--report-out", type=Path, default=ROOT / "data" / "v2_report.json")
    args = parser.parse_args()

    run_root = _project_path(args.root)
    manifest = run_root / "manifest.csv"
    batch_summary = run_root / "emx_batch_summary.json"
    workflow_summary = run_root / "run_overnight_summary.json"
    started = time.time()

    if args.force_generate or not manifest.exists():
        _run_step(
            [
                sys.executable,
                "scripts/generate_overnight_candidates.py",
                "--dataset",
                str(_project_path(args.base_dataset)),
                "--model",
                str(_project_path(args.base_model)),
                "--out-root",
                str(run_root),
                "--target-count",
                str(args.target_count),
            ]
        )
    else:
        print(f"reuse manifest: {manifest}", flush=True)

    emx_code: int | None = None
    if args.skip_emx:
        print("skip EMX batch by request", flush=True)
    else:
        remaining_s = max(60.0, args.hours * 3600.0 - (time.time() - started))
        cmd = [
            sys.executable,
            "scripts/run_emx_batch.py",
            "--manifest",
            str(manifest),
            "--summary-out",
            str(batch_summary),
            "--max-runtime-seconds",
            str(max(60.0, remaining_s)),
        ]
        if args.force_emx:
            cmd.append("--force")
        emx_code = _run_step(cmd, allow_failure=True)
        if emx_code:
            print(f"EMX batch exited with code {emx_code}; continuing with completed local S2P files.", file=sys.stderr)

    _run_step([sys.executable, "scripts/extract_dataset.py", "--root", str(run_root), "--out", str(_project_path(args.overnight_dataset))])
    _run_step(
        [
            sys.executable,
            "scripts/merge_datasets.py",
            "--inputs",
            str(_project_path(args.base_dataset)),
            str(_project_path(args.overnight_dataset)),
            "--out",
            str(_project_path(args.merged_dataset)),
        ]
    )
    _run_step([sys.executable, "scripts/fit_model.py", "--dataset", str(_project_path(args.merged_dataset)), "--model-out", str(_project_path(args.model_out))])
    _run_step(
        [
            sys.executable,
            "scripts/make_report.py",
            "--dataset",
            str(_project_path(args.merged_dataset)),
            "--model",
            str(_project_path(args.model_out)),
            "--out",
            str(_project_path(args.report_out)),
            "--batch-summary",
            str(batch_summary),
        ]
    )

    summary = {
        "root": str(run_root),
        "manifest": str(manifest),
        "target_count": args.target_count,
        "hours": args.hours,
        "emx_exit_code": emx_code,
        "elapsed_seconds": round(time.time() - started, 3),
        "outputs": {
            "overnight_dataset": str(_project_path(args.overnight_dataset)),
            "merged_dataset": str(_project_path(args.merged_dataset)),
            "model": str(_project_path(args.model_out)),
            "report": str(_project_path(args.report_out)),
        },
    }
    workflow_summary.parent.mkdir(parents=True, exist_ok=True)
    workflow_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"workflow summary: {workflow_summary}")
    return 0 if emx_code in (None, 0, 2, 124) else emx_code


if __name__ == "__main__":
    raise SystemExit(main())
