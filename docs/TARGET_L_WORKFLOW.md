# Target-L Workflow

The preferred target-L workflow is:

```text
surrogate proposal -> resilient EMX batch -> EMX best-Q selection
```

Run the complete flow with:

```powershell
python scripts/optimize_target_l_emx.py --target-L 5.367 --tol 0.02 --top 12 --out-root runs/target_L5p367_new
```

Use `--skip-emx` to generate only the FDL files, `manifest.csv`, and
`proposal.json`. The normal EMX stage delegates to `run_emx_batch.py`, which
continues after individual candidate failures, validates downloaded Touchstone
data, and writes `emx_batch_summary.json`.

The workflow expects the VM configuration supplied by `VmConfig` and the
password environment variable named by `VmConfig.password_env`. It does not
need a release-only JSON credential file.

The result directory contains:

- `fdl/`: proposed UltraEM-compatible geometry sources.
- `skill/`: generated Cadence layout builders.
- `gds/` and `s2p/`: EMX inputs and results, when EMX has run.
- `proposal.json`: surrogate-ranked proposal record.
- `emx_batch_summary.json`: per-candidate EMX run outcome.
- `best_result.json` and `best_fdl/`: EMX-verified selection.
- `summary.md`: command and final-result summary.
