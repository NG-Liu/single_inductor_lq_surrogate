from __future__ import annotations

import csv
import json
import posixpath
import sys
from pathlib import Path
from traceback import format_exception_only

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.config import VmConfig
from inductor_lq.emx import RemoteClient, prepare_skill, sh_quote, streamout_and_emx_command
from inductor_lq.touchstone import read_touchstone


def is_valid_s2p(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = read_touchstone(path)
    except Exception:
        return False
    return len(data.freqs_hz) == 4 and all(
        abs(actual - expected) < 1.0
        for actual, expected in zip(data.freqs_hz, (3.0e9, 3.5e9, 4.0e9, 4.5e9))
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build Cadence GDS and run EMX for generated candidates.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "runs" / "v1" / "manifest.csv")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke-test limit.")
    parser.add_argument("--force", action="store_true", help="Rerun candidates even if local S2P/GDS already exist.")
    parser.add_argument("--summary-out", type=Path, default=None, help="Optional JSON batch summary path.")
    args = parser.parse_args()

    cfg = VmConfig()
    client = RemoteClient(cfg)
    run_root = args.manifest.parent
    summary_out = args.summary_out or run_root / "emx_batch_summary.json"
    with args.manifest.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for row in rows:
        cid = row["candidate_id"]
        fdl_path = (run_root / row["fdl_path"]).resolve()
        skill_path = (run_root / row["skill_path"]).resolve()
        local_s2p = (run_root / row["s2p_path"]).resolve()
        local_gds = (run_root / row["gds_path"]).resolve()
        if not args.force and local_gds.exists() and is_valid_s2p(local_s2p):
            print(f"[{cid}] skip existing valid result -> {local_s2p}")
            skipped.append(cid)
            continue

        prepare_skill(fdl_path, skill_path, cid, cfg)
        remote_fdl = posixpath.join(cfg.remote_root, "fdl", f"{cid}.py")
        remote_skill = posixpath.join(cfg.remote_root, "skill", f"{cid}.il")
        remote_run = posixpath.join(cfg.remote_root, "emx", cid)
        remote_logs = {
            "virtuoso_log": posixpath.join(remote_run, "virtuoso.log"),
            "strmout_log": posixpath.join(remote_run, "strmout.log"),
            "emx_log": posixpath.join(remote_run, "emx.log"),
        }
        try:
            print(f"[{cid}] upload")
            client.run(f"mkdir -p {sh_quote(posixpath.dirname(remote_fdl))} {sh_quote(posixpath.dirname(remote_skill))} {sh_quote(remote_run)}")
            client.upload(fdl_path, remote_fdl)
            client.upload(skill_path, remote_skill)
            print(f"[{cid}] virtuoso/strmout/emx")
            client.run(f"bash -lc {sh_quote(streamout_and_emx_command(cfg, cid, remote_run))}")
            client.download(posixpath.join(remote_run, f"{cid}.s2p"), local_s2p)
            client.download(posixpath.join(remote_run, f"{cid}.gds"), local_gds)
            if not is_valid_s2p(local_s2p):
                raise RuntimeError(f"Downloaded S2P is missing required 4 frequency points: {local_s2p}")
            succeeded.append(cid)
            print(f"[{cid}] done -> {local_s2p}")
        except Exception as exc:  # noqa: BLE001
            message = "".join(format_exception_only(type(exc), exc)).strip()
            log_text = ", ".join(f"{name}={path}" for name, path in remote_logs.items())
            failed.append((cid, f"{message}; remote logs: {log_text}"))
            print(f"[{cid}] FAILED: {message}; remote logs: {log_text}", file=sys.stderr)

    print(f"summary: succeeded={len(succeeded)} skipped={len(skipped)} failed={len(failed)}")
    summary = {
        "manifest": str(args.manifest),
        "succeeded": succeeded,
        "skipped": skipped,
        "failed": [{"candidate_id": cid, "reason": message} for cid, message in failed],
    }
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"batch summary: {summary_out}")
    if failed:
        print("failed candidates:", file=sys.stderr)
        for cid, message in failed:
            print(f"- {cid}: {message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
