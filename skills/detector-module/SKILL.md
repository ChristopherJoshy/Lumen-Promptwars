# Detector module skill

Checklist for adding any forensic detector (`backend/app/features/analysis/detectors/<modality>_forensics.py`).

## Input contract

- Args: `media_path: str` (object-storage key or local path) + `metadata: dict`
- Never read full video into memory; stream frames/chunks.

## Output schema (required keys)

- `label`: `"synthetic" | "authentic" | "uncertain"`
- `confidence`: `float` in `[0, 1]`, calibrated, never a bare magic number
- `evidence_path`: heatmap/artifact location (stored with the case at analysis
  time, never computed on-demand at report view)
- `model_version`: string identifying weights/code version

## Rules

- Docstring format: one line what + `Args:`/`Returns:`/`Raises:`.
- Type hints on every signature; mypy-clean.
- Fixtures in `backend/tests/fixtures/<modality>/`; tests mirror the feature
  path (`test_<modality>_forensics.py`); keep repo < 10 MB — fetch large sets
  at test time, never commit weights or bulk media.
- Failure is loud: model can't load → raise with a clear error. Never return
  a fake "uncertain/insufficient evidence" to hide a broken path.
- Indic-language priority: audio work proves Malayalam/Hindi/Tamil/Telugu
  before English tuning.

## Agentic detectors (v1 note)

Agentic detectors honor the same output contract (`label`, `confidence`,
`evidence_path`, `model_version`). `evidence_path` points at the JSON
verdict artifact under `storage/`, not a pixel heatmap.
