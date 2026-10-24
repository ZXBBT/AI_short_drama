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
episodes/        one folder per episode: episode.yaml (shots + links), selections.yaml
config/recipes/  versioned generation settings shared by shots
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
| 3 | Official H3 model download + checksum verification | ✅ 2026-10-23 — `models/verification/2026-10-23_stage3.txt` |
| 4 | First low-res H3 test render | ✅ 2026-10-23 — `runs/2026-10-23/stage4_a_608x352_5f.json` |
| 5 | Reproducibility check + scaling | ✅ 2026-10-23 — `docs/stage5-results.md` (attention comparison skipped: swap stop rule); hands-on guide `docs/practice-h3.md` |
| 6 | Short-drama pipeline | 🔄 started 2026-10-23 — plan `docs/automation-plan.md`; 6.1 foundation done (`scripts/episode.py`, `episodes/`); 6.2 smoke tests done (`docs/stage6-2-results.md`); 6.3 pilot done (`docs/stage6-3-results.md`); 6.4 assembly done (`docs/stage6-4-results.md`) — first episode `midnight_call` v1; awaiting owner review |
| 7 | Automation | 🔄 started 2026-10-24 — plan `docs/stage7-plan.md`; 7.1–7.4 done (`docs/stage7-results.md`): `pipeline.py`, `review_server.py`, re-rolls, cut helpers; end-to-end test passed |
| — | Licensing / commercial-use gate | required before monetization or client delivery |

## Rules

- One stage at a time; each ends with a checkpoint.
- Official ComfyUI core nodes, templates and model files first; no unnecessary custom nodes.
- Record versions, model filenames, parameters, seeds, checksums and output metadata.
- Every deviation from an official template is logged in `docs/decisions.md`.
