# AI Short Drama — local MiniMax H3 pipeline

Reproducible, progressively automated short-drama and commercial production with MiniMax H3 in
ComfyUI, running locally on Apple Silicon (M5 Max, 64 GB) through **PyTorch MPS** (not MLX).
No paid cloud services: everything renders on this Mac.

## What it does

```
brief.yaml ──► shot list (episode.yaml) ──► check-plan ──► render takes (H3) ──► automatic checks
   ──► review page: pick takes, confirm ──► optional SeedVR2 upscale ──► assemble (cut.yaml)
   ──► final MP4s (native + 1080p) + subtitles + manifest
```

- **Prompts** follow MiniMax's official H3 format (`h3-prompt-writing` skill) plus our own direction
  rules (`.claude/skills/h3-short-drama-direction`): gaze plans, emotion beats, background people,
  object continuity, geometry-first stills, sound built in the edit.
- **Every take is fingerprinted** (graph, model checksums, input pixels, prompt, recipe) and recorded in
  `runs/` with seed, timings, memory and output checksums, so finished takes are never rendered twice.
- **Automatic checks** after each render: frame count, black frames, audio, unwanted hard cuts, and
  (macOS Vision) burned-in text, looking into the lens, lips moving in silent shots, face size/quality.
- **Assembly** levels loudness (BS.1770), builds layered soundtracks (narration, music chain, room beds,
  ducking), composites phone screens, adds subtitles and writes a manifest of exactly what was used.

## Episodes

| Episode | Format | Status |
|---|---|---|
| `midnight_call` | 9:16 drama pilot | v1, v2 (1080p) |
| `sunlight` | 9:16, brief → episode end-to-end test | **v2 confirmed** (official prompt format); v2-hd upscaled to 960x1728 |
| `Urban_Lifestyle_Commercial` ("Be a Little Braver") | 16:9 commercial, 64 s | V2 — [GitHub Release `braver-v2`](https://github.com/ZXBBT/AI_short_drama/releases/tag/braver-v2) |
| `_stills`, `_format_test`, `_multiref`, `_quality`, `_location` | test episodes | results in `docs/` |

## Models (weights are not in Git; manifests with SHA-256 are)

| Model | Use | Licence | Manifest |
|---|---|---|---|
| MiniMax H3 (fl2va, ref2va; int8) | video + sound: T2V, I2V, FLF2V, R2V, audio-only assets | H3 community licence — review before any commercial use | `models/manifest.tsv` |
| Qwen-Image 2.1 (+ turbo) | stills, edits, text in pictures, background removal | **research/evaluation only → pictures are non-commercial** (D17) | `models/manifest_qwen_image_2.1.tsv` |
| SeedVR2 3B / 7B sharp (int8) | video upscaling x2 | Apache 2.0 (D18) | `models/manifest_seedvr2.tsv` |

## Quick start (episode)

```bash
PY=~/dev/ComfyUI/.venv/bin/python
$PY scripts/brief.py validate   episodes/<name>   # check brief.yaml and reference pictures
$PY scripts/brief.py scaffold   episodes/<name>   # write episode.yaml (characters, locations), once
#   ... draft the shots in episode.yaml (official H3 format + direction skill) ...
$PY scripts/brief.py check-plan episodes/<name>   # rules: format, length, sizes that fit, outfits
$PY scripts/pipeline.py         episodes/<name>   # render takes (starts ComfyUI), re-rolls, cut, assemble
$PY scripts/review_server.py    episodes/<name>   # http://127.0.0.1:8189 — watch, pick, confirm
$PY scripts/upscale.py --cut episodes/<name>/cut.yaml   # optional: shots with `upscale: 7b_sharp`
$PY scripts/assemble.py episodes/<name>/cut.yaml        # final MP4s in ~/AI_renders/comfyui/episodes/<name>/_final
```

Other tools: `scripts/qwen_image.py` (Qwen stills/edits; start ComfyUI with `--bf16-text-enc` for edits),
`scripts/take_checks.py` (picture checks), `scripts/face_check.py`, `scripts/screen_insert.py`
(green-screen phone UI), `scripts/audio_clip.py`, `scripts/launch_comfyui.sh`.

## Checks

```bash
scripts/check.sh                            # standard checks: run before and after every change
RUN_VISION_INTEGRATION=1 scripts/check.sh   # + optional real macOS Vision face check
```

- **Standard, deterministic** (`scripts/check.sh`, for developers and agents): the offline tests
  (`test_episode`, `test_brief`, `test_assemble`, `test_autopick`, `test_take_checks`) plus
  `episode.py validate` for every episode. No macOS Vision (the face check is stubbed), no ComfyUI, no
  rendering, no network. Prints every check's full output and a PASS / FAIL / SKIP summary; exit 1 on
  any failure. Uses the ComfyUI venv (`PY=...` to override). Episodes whose only problem is a missing
  local-only reference picture listed in the script (gitignored by owner decision) are SKIPped.
- **Optional, real Vision** (`RUN_VISION_INTEGRATION=1`, `scripts/test_vision_integration.py`): measures
  two reference pictures with the Swift helper and runs `brief.py validate episodes/sunlight`. SKIP with
  the reason when this environment cannot run Vision; a broken helper or wrong measurement is a FAIL.

## Where things live

| What | Path | In Git? |
|---|---|---|
| This repo: config, scripts, prompts, workflows, subtitles, docs, run metadata | `~/dev/AI_short_drama` | ✅ |
| ComfyUI code (its own git checkout, pinned tag v0.42.1) | `~/dev/ComfyUI` | ❌ (separate repo) |
| Model weights | `~/AI_models/comfyui/<type>/` | ❌ |
| Renders (takes, finals, upscales, Qwen pictures) | `~/AI_renders/comfyui/` | ❌ |

None of these paths are inside iCloud Drive. Weights and renders are too large for Git and would be
re-uploaded/evicted by iCloud. Finished videos are shared as GitHub Release attachments.

## Repo layout

```
.claude/skills/  h3-short-drama-direction (ours); h3-prompt-writing is fetched, not committed
docs/            findings, decision log (decisions.md), stage reports, test results
env/             version log + environment snapshots
models/          model manifests (filenames, sizes, sha256) — never the weights
workflows/
  official/      unmodified official ComfyUI templates (reference copies)
  project/       our edited workflows (diff against official/)
prompts/         prompt text per shot
episodes/        one folder per episode: brief.yaml, episode.yaml, selections.yaml, cut*.yaml
config/recipes/  versioned generation settings shared by shots (h3_base_v1, h3_base_v2)
inputs/          small reference images and location plates used as inputs
subtitles/       .srt files of assembled cuts
scripts/         pipeline, tools and tests
runs/            per-render / per-cut metadata (seed, params, versions, checksums, output path)
```

## Stage status

| # | Stage | Status |
|---|---|---|
| 0 | Read-only system & compatibility audit | ✅ 2026-10-23 — `docs/stage0-findings.md` |
| 1 | Project skeleton (this repo, folders, logs) | ✅ 2026-10-23 |
| 2 | ComfyUI + PyTorch install, MPS micro-tests, small-model practice | ✅ 2026-10-23 — `docs/practice-sdxl.md` |
| 3 | Official H3 model download + checksum verification | ✅ 2026-10-23 — `models/verification/2026-10-23_stage3.txt` |
| 4 | First low-res H3 test render | ✅ 2026-10-23 |
| 5 | Reproducibility check + scaling | ✅ 2026-10-23 — `docs/stage5-results.md`, `docs/practice-h3.md` |
| 6 | Short-drama pipeline (episodes, takes, assembly) | ✅ 2026-10-23 — `docs/stage6-*-results.md`; Midnight Call v1/v2 |
| 7 | Automation (pipeline, re-rolls, review page) | ✅ 2026-10-24 — `docs/stage7-results.md` |
| 8 | Brief → episode, auto-pick, confirmation, generated cuts | ✅ 2026-10-24 — `docs/stage8-brief-format.md`; Sunlight end-to-end |
| 8+ | Quality & tools: official prompt format, direction skill, sound layers, picture checks, Qwen-Image, multi-reference, SeedVR2 | ✅ 2026-10-26 — `docs/quality-track-results.md`, `docs/commercial-v2-results.md`, `docs/stage8-improvements.md`, `docs/qwen-image-results.md`, `docs/seedvr2-results.md` |
| — | Licensing / commercial-use gate | ⏳ required before monetisation or client delivery |
| — | Local "studio" web app | ⏳ planned (owner request), plan first |

## Measured on this Mac (M5 Max, 64 GB)

- H3: 480x864 (0.4 MP) up to 107 frames, ~14-15 min per take with PyTorch attention; 352x608 up to 124 frames.
- Qwen-Image 2.1: 1024x1536 still 1-3 min (turbo ~1 min), 2K plate ~4 min, edits ~1 min.
- SeedVR2 7B sharp: x2 upscale ~10 min per 4 s shot.

## Setup notes

- After cloning: `scripts/fetch_h3_skills.sh` installs MiniMax's official `h3-prompt-writing` skill
  (not in Git: no licence in its source repo; see `docs/third_party.md`).
- Model files: download with `scripts/fetch_models.sh`, verify with `scripts/verify_models.sh` against the
  manifests.

## Rules

- One stage at a time; each ends with a checkpoint.
- Official ComfyUI core nodes, templates and model files first; no unnecessary custom nodes.
- Record versions, model filenames, parameters, seeds, checksums and output metadata.
- Every deviation from an official template is logged in `docs/decisions.md`.
- Licensing and commercial use are a separate approval gate; Qwen-Image pictures are non-commercial.
