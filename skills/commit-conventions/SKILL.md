# Commit conventions skill

Conventional Commits, one logical change per commit.

## Format

`<type>(<scope>): <imperative subject, no period, ≤72 chars>`

- Types: `feat`, `fix`, `test`, `docs`, `chore`
- Scope = feature folder touched (`ingestion`, `detectors`, `contradiction`,
  `readme`, `deps` …)
- Body (optional): explains *why* when the diff doesn't.

## Examples

- `feat(ingestion): add yt-dlp link extractor with platform detection`
- `fix(contradiction): correct EXIF timestamp timezone handling`
- `test(detectors): add fixture set for image forensic ensemble`
- `docs(readme): document known Instagram/X extraction limitations`

## Rules

- Small reviewable diffs; stub with `NotImplementedError` + docstring first
  rather than one giant commit.
- Push even small changes to `main` (single branch only).
- Never commit: `.env` secrets, `node_modules`, `.venv`, weights
  (`*.pt/*.bin/*.onnx`), bulk media, volume dirs — see `.gitignore`.
- Update `changes.md` with every commit.
