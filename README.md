# Single Inductor L/Q Surrogate

This is an independent, git-managed workflow for the validated single-inductor geometry:

- 12-sided polygon spiral
- M5/M4/V4 three-metal air-bridge structure
- P1/P2 pins on M5
- EMX differential 1-port simulation from GDS
- Frequency sweep: `3.0, 3.5, 4.0, 4.5 GHz`

The main target is `L@3.75GHz` and `Q@3.75GHz`. These are computed by linearly interpolating complex `Zdiff` between `3.5 GHz` and `4.0 GHz`, then calculating L/Q.

## Quick Start

```powershell
python scripts/generate_candidates.py --config configs/v1_42_samples.yaml
$env:LVBOBALUN_VM_PASSWORD = "user1111"
python scripts/run_emx_batch.py --manifest runs/v1/manifest.csv
python scripts/extract_dataset.py --root runs/v1
python scripts/fit_model.py --dataset data/v1_dataset.csv
python scripts/predict.py --model data/v1_model.json --r0 69.7 --W 10.4 --S 15 --N 3.5
```

Use `--limit 1` with `run_emx_batch.py` for a smoke test before launching all 42 samples.
Existing valid S2P/GDS files are skipped unless `--force` is passed, so extending the v1 grid only runs missing candidates.

Run the built-in Touchstone regression without extra test dependencies:

```powershell
python scripts/validate_examples.py
```

## Outputs

- `runs/v1/fdl/*.py`: generated UltraEM-compatible FDL files
- `runs/v1/skill/*.il`: Cadence SKILL layout builders
- `runs/v1/gds/*.gds`: stream-out GDS files, ignored by git
- `runs/v1/s2p/*.s2p`: EMX Touchstone results, ignored by git
- `data/v1_dataset.csv`: extracted accepted/rejected sample table
- `data/v1_model.json`: fitted surrogate model
- `data/v1_report.json`: compact batch/model report

## Git Policy

This repository tracks source, config, docs, and small regression examples only. Large and regenerated artifacts are ignored:

- `runs/**`
- `*.gds`
- `*.s2p`
- `*.log`
- Cadence lock/cache files
