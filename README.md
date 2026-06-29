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

## Overnight V2 Sampling

The overnight workflow creates an independent ignored run directory, resumes from existing valid S2P/GDS files, and still trains from partial completed results if the time budget expires:

```powershell
python scripts/validate_examples.py
python -m compileall -q src scripts tests
$env:LVBOBALUN_VM_PASSWORD = "user1111"
python scripts/run_overnight.py --root runs/overnight_v2 --hours 8 --target-count 600
```

It writes the raw overnight extraction to `data/overnight_v2_dataset.csv`, merges completed rows with v1 into `data/v2_dataset.csv`, then fits `data/v2_model.json` and `data/v2_report.json`. Rows without valid EMX L/Q are skipped during merge, so an interrupted run does not poison the v2 training set with unrun candidates.

## Shunt-Grounded Library

Use this as a separate context library for filter shunt inductors. It reuses series-library geometries, but adds a local wide ground landing at the P2 end. The EMX port is still `Pdiff=P1:P2`, so the extracted impedance is signal-to-local-ground for the shunt branch.

```powershell
python scripts/generate_shunt_candidates.py --source runs/overnight_v2/manifest.csv --out-root runs/shunt_v1 --limit 200
$env:LVBOBALUN_VM_PASSWORD = "user1111"
python scripts/run_emx_batch.py --manifest runs/shunt_v1/manifest.csv
python scripts/extract_dataset.py --root runs/shunt_v1 --out data/shunt_v1_dataset.csv
python scripts/fit_model.py --dataset data/shunt_v1_dataset.csv --model-out data/shunt_v1_model.json
python scripts/make_report.py --dataset data/shunt_v1_dataset.csv --model data/shunt_v1_model.json --out data/shunt_v1_report.json --batch-summary runs/shunt_v1/emx_batch_summary.json
```

Keep `series_float` and `shunt_grounded` datasets separate. A geometry with the best floating two-terminal Q is not automatically the best grounded shunt branch after terminal landing and return parasitics are included.

## Target-L Best-Q Flow

Use the surrogate to propose a diverse target-L candidate batch, then let EMX pick the final best-Q FDL:

```powershell
python scripts/propose_target_l.py --target-L 3.6 --tol 0.05 --top 20
$env:LVBOBALUN_VM_PASSWORD = "user1111"
python scripts/run_emx_batch.py --manifest runs/target_L3p6/manifest.csv
python scripts/select_best.py --root runs/target_L3p6 --target-L 3.6 --tol 0.05
```

The proposal step searches only within accepted v1 data bands by default. It uses the selected L surrogate for L matching and the linear Q model for Q ranking because the current validation set gives lower Q error for the linear model.
By default it refuses candidates with predicted `|L-target| > 0.25 nH`; raise `--max-error` or `--tol` if a target needs a broader exploratory batch.

## Outputs

- `runs/v1/fdl/*.py`: generated UltraEM-compatible FDL files
- `runs/v1/skill/*.il`: Cadence SKILL layout builders
- `runs/v1/gds/*.gds`: stream-out GDS files, ignored by git
- `runs/v1/s2p/*.s2p`: EMX Touchstone results, ignored by git
- `data/v1_dataset.csv`: extracted accepted/rejected sample table
- `data/v1_model.json`: fitted surrogate model
- `data/v1_report.json`: compact batch/model report
- `data/v2_dataset.csv`: merged v1 + completed overnight v2 sample table
- `data/v2_model.json`: fitted v2 surrogate model
- `data/v2_report.json`: compact v2 batch/model report
- `data/shunt_v1_dataset.csv`: separate signal-to-local-ground shunt sample table

## Git Policy

This repository tracks source, config, docs, and small regression examples only. Large and regenerated artifacts are ignored:

- `runs/**`
- `*.gds`
- `*.s2p`
- `*.log`
- Cadence lock/cache files
