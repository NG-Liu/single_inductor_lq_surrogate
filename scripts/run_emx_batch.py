from __future__ import annotations

import csv
import posixpath
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inductor_lq.config import VmConfig
from inductor_lq.emx import RemoteClient, prepare_skill, sh_quote, streamout_and_emx_command


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build Cadence GDS and run EMX for generated candidates.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "runs" / "v1" / "manifest.csv")
    parser.add_argument("--limit", type=int, default=None, help="Optional smoke-test limit.")
    args = parser.parse_args()

    cfg = VmConfig()
    client = RemoteClient(cfg)
    run_root = args.manifest.parent
    with args.manifest.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[: args.limit]

    for row in rows:
        cid = row["candidate_id"]
        fdl_path = (run_root / row["fdl_path"]).resolve()
        skill_path = (run_root / row["skill_path"]).resolve()
        prepare_skill(fdl_path, skill_path, cid, cfg)
        remote_fdl = posixpath.join(cfg.remote_root, "fdl", f"{cid}.py")
        remote_skill = posixpath.join(cfg.remote_root, "skill", f"{cid}.il")
        remote_run = posixpath.join(cfg.remote_root, "emx", cid)
        print(f"[{cid}] upload")
        client.run(f"mkdir -p {sh_quote(posixpath.dirname(remote_fdl))} {sh_quote(posixpath.dirname(remote_skill))} {sh_quote(remote_run)}")
        client.upload(fdl_path, remote_fdl)
        client.upload(skill_path, remote_skill)
        print(f"[{cid}] virtuoso/strmout/emx")
        client.run(f"bash -lc {sh_quote(streamout_and_emx_command(cfg, cid, remote_run))}")
        local_s2p = (run_root / row["s2p_path"]).resolve()
        local_gds = (run_root / row["gds_path"]).resolve()
        client.download(posixpath.join(remote_run, f"{cid}.s2p"), local_s2p)
        client.download(posixpath.join(remote_run, f"{cid}.gds"), local_gds)
        print(f"[{cid}] done -> {local_s2p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

