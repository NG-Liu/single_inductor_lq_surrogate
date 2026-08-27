# Project Lineage

## Roles

- `single_inductor_lq_surrogate` is the canonical source repository for
  reusable single-inductor geometry, FDL, Cadence, EMX, Touchstone, and L/Q
  surrogate code.
- `emx_inductor_optimizer_release` is a derived handoff/release snapshot. It
  keeps selected reference artifacts for review and reproducibility.
- `新建文件夹 (2)` is the historical LVBOBALUN integration workspace that
  contains upstream prototype work, filter/balun studies, and solver outputs.

## Evidence Relationship

The release was packaged after the core repository and has an independent Git
history. Its shared source and data files are content-aligned with this
repository, while its release-specific scripts and checked reference artifacts
serve the handoff use case.

The integration workspace predates the standalone repository and contains
single-inductor prototypes with the same geometry features and L/Q extraction
approach. It remains the home for system-level filter, balun, cascade, and HFSS
work rather than a second source of truth for the reusable inductor workflow.

## Maintenance Rule

Make reusable inductor changes here first. Build or update release material
from this repository, and record the source commit or content snapshot used by
each release. Preserve historical raw artifacts in their original archive or
release location unless a compact reference copy is deliberately curated.
