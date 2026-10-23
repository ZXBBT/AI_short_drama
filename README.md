# AI Short Drama — local MiniMax H3 pipeline

Reproducible, progressively automated short-drama production with MiniMax H3 in
ComfyUI, running locally on Apple Silicon through **PyTorch MPS** (not MLX).

## Where things live

| What | Path | In Git? |
|---|---|---|
| This repo: config, scripts, prompts, workflows, subtitles, docs, run metadata | `~/dev/AI_short_drama` | ✅ |
| ComfyUI code (its own git checkout, pinned tag) | `~/dev/ComfyUI` | ❌ (separate repo) |
| Model weights | `~/AI_models/comfyui/<type>/` | ❌ |
| Raw renders (video/audio) | `~/AI_renders/` | ❌ |

None of these paths are inside iCloud Drive. Weights and renders are too large
for Git and would be re-uploaded/evicted by iCloud.

## Repo layout

```
docs/            findings, decision log, stage reports
env/             version log + environment snapshots
models/          model manifest (filenames, sizes, sha256) — never the weights
workflows/
  official/      unmodified official ComfyUI templates (reference copies)
  project/       our edited workflows (diff against official/)
prompts/         prompt text per shot
inputs/          small reference images used as workflow inputs
subtitles/       .srt / .ass files
scripts/         helper scripts
runs/            per-render metadata (seed, params, versions, output path)
```

## Stage status

| # | Stage | Status |
|---|---|---|
| 0 | Read-only system & compatibility audit | ✅ 2026-10-23 — see `docs/stage0-findings.md` |
| 1 | Project skeleton (this repo, folders, logs) | ✅ 2026-10-23 |
| 2 | ComfyUI + PyTorch install, MPS micro-tests, small-model practice | ✅ 2026-10-23 — practice guide `docs/practice-sdxl.md` (hands-on by owner) |
| 3 | Official H3 model download + checksum verification | ⏳ needs approval |
| 4 | First low-res H3 test render | — |
| 5 | Reproducibility check | — |
| 6 | Short-drama pipeline | — |
| 7 | Automation | — |
| — | Licensing / commercial-use gate | required before monetization or client delivery |

## Rules

- One stage at a time; each ends with a checkpoint.
- Official ComfyUI core nodes, templates and model files first; no unnecessary custom nodes.
- Record versions, model filenames, parameters, seeds, checksums and output metadata.
- Every deviation from an official template is logged in `docs/decisions.md`.
