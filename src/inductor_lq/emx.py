from __future__ import annotations

import os
import posixpath
from dataclasses import dataclass
from pathlib import Path

import paramiko

from .cadence import fdl_to_skill
from .config import VmConfig


@dataclass
class RemoteClient:
    config: VmConfig

    def _connect(self):
        password = os.environ.get(self.config.password_env)
        if not password:
            raise RuntimeError(f"Set {self.config.password_env} before running EMX batch")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.config.host,
            username=self.config.user,
            password=password,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )
        return client

    def upload(self, local: Path, remote: str) -> None:
        with self._connect() as client:
            sftp = client.open_sftp()
            try:
                self.run(f"mkdir -p {sh_quote(posixpath.dirname(remote))}")
                sftp.put(str(local), remote)
            finally:
                sftp.close()

    def download(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as client:
            sftp = client.open_sftp()
            try:
                sftp.get(remote, str(local))
            finally:
                sftp.close()

    def run(self, command: str) -> str:
        with self._connect() as client:
            _, stdout, stderr = client.exec_command(command)
            out = stdout.read().decode("utf-8", "ignore")
            err = stderr.read().decode("utf-8", "ignore")
            status = stdout.channel.recv_exit_status()
        if status:
            raise RuntimeError(f"Remote command failed ({status}):\n{command}\n{out}\n{err}")
        return out + err


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def streamout_and_emx_command(cfg: VmConfig, cell_name: str, remote_run: str) -> str:
    gds = f"{remote_run}/{cell_name}.gds"
    s2p = f"{remote_run}/{cell_name}.s2p"
    return f"""
set -e
mkdir -p {sh_quote(remote_run)}
cd /home/IC/EDA
virtuoso -nograph -restore {sh_quote(f'{cfg.remote_root}/skill/{cell_name}.il')} -log {sh_quote(f'{remote_run}/virtuoso.log')}
strmout \\
  -library {cfg.cadence_lib} \\
  -strmFile {sh_quote(gds)} \\
  -topCell {cell_name} \\
  -view layout \\
  -runDir {sh_quote(remote_run)} \\
  -logFile {sh_quote(f'{remote_run}/strmout.log')} \\
  -summaryFile {sh_quote(f'{remote_run}/strmout.summary')} \\
  -techLib {cfg.tech_lib} \\
  -hierDepth 32 \\
  -maxVertices 4000 \\
  -layerMap {cfg.layermap} \\
  -labelDepth 32 \\
  -case Preserve \\
  -convertDot node \\
  -convertPin geometryAndText \\
  -pinAttNum 1 \\
  -pathToPolygon \\
  -verbose
cd {sh_quote(remote_run)}
{cfg.emx_bin} {sh_quote(gds)} {cell_name} {sh_quote(cfg.process_file)} \\
  --3d=m4,m5 \\
  --via-sidewalls=v4 \\
  --via-inductance=v4 \\
  --sweep 3e9 4.5e9 \\
  --sweep-stepsize=5e8 \\
  --format=touchstone \\
  --s-impedance=50 \\
  --s-file={sh_quote(s2p)} \\
  --internal=P1,m5,8 \\
  --internal=P2,m5,8 \\
  -p Pdiff=P1:P2 \\
  --include-command-line 2>&1 | tee {sh_quote(f'{remote_run}/emx.log')}
"""


def prepare_skill(fdl_path: Path, skill_path: Path, cell_name: str, cfg: VmConfig) -> None:
    fdl_to_skill(
        fdl_path,
        skill_path,
        lib_name=cfg.cadence_lib,
        lib_path=cfg.cadence_lib_path,
        tech_lib=cfg.tech_lib,
        cell_name=cell_name,
    )
