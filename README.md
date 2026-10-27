# AI Short Drama — local MiniMax H3 pipeline

Reproducible, progressively automated short-drama and commercial production with MiniMax H3 in
ComfyUI, running locally on Apple Silicon through **PyTorch MPS** (not MLX, D1). No paid cloud services:
no Comfy Cloud, no "partner" or `api_*` nodes (D11) — everything renders on this Mac.

**Current state** (phase, test baseline, open items, rendering and licensing limits):
`docs/status/current.md` — the only status source. Everything else in this README is a stable overview.

## What it does

```
brief.yaml ──► shot list (episode.yaml) ──► check-plan ──► render takes (H3) ──► automatic checks
   ──► review page: pick takes, confirm ──► optional SeedVR2 upscale ──► assemble (cut.yaml)
   ──► final MP4s (native + 1080p) + subtitles + manifest
```

- **Prompts** follow MiniMax's official H3 format (`h3-prompt-writing` skill) plus our own direction
  rules (`.claude/skills/h3-short-drama-direction/`): gaze plans, emotion beats, background people,
  object continuity, geometry-first stills, sound built in the edit.
- **Every take is fingerprinted** (graph, model checksums, input pixels, prompt, recipe) and recorded in
  `runs/` with seed, timings, memory and output checksums, so finished takes are never rendered twice.
- **Automatic checks** after each render: frame count, black frames, audio, unwanted hard cuts, and
  (macOS Vision) burned-in text, looking into the lens, lips moving in silent shots, face size/quality.
- **Assembly** levels loudness (BS.1770), builds layered soundtracks (narration, music chain, room beds,
  ducking), composites phone screens, adds subtitles and writes a manifest of exactly what was used.

## Requirements

This project is verified on, and pinned to, one local environment. These are the versions in use, not
tested minimums; other versions, machines or operating systems have not been tested.

| Component | Verified, pinned version | Where |
|---|---|---|
| Machine | Apple Silicon M5 Max, 64 GB unified memory | — |
| ComfyUI | tag `v0.42.1` (own git checkout) | `~/dev/ComfyUI` (D2) |
| Python | 3.13 (Homebrew `python@3.13`) in ComfyUI's venv | `~/dev/ComfyUI/.venv` (D3) |
| PyTorch | 2.14.1 stable | same venv (D4) |

Exact versions and the package list: `env/versions.md`, `env/comfyui-venv-freeze.txt`. `env/versions.md`
records the pinned versions and one command that rebuilds the ComfyUI venv from the freeze file; this
repo has no complete from-scratch ComfyUI install script. All project scripts run with the venv's Python
(`~/dev/ComfyUI/.venv/bin/python`).

## Setup after cloning

`fetch_h3_skills.sh` and `fetch_models.sh` download from the internet; in this project a download needs
the owner's approval (`AGENTS.md` §7). `verify_models.sh` is a local, read-only check and downloads
nothing.

```bash
scripts/fetch_h3_skills.sh                                    # MiniMax's h3-prompt-writing skill (not in Git)
scripts/fetch_models.sh                                       # H3 required files (models/manifest.tsv)
scripts/fetch_models.sh models/manifest.tsv r2v               # H3 reference-to-video model (D14)
scripts/fetch_models.sh models/manifest_qwen_image_2.1.tsv    # Qwen-Image 2.1 required files (D17)
scripts/fetch_models.sh models/manifest_seedvr2.tsv           # SeedVR2 required files (D18)
scripts/verify_models.sh [manifest]                           # read-only full SHA-256 re-hash
```

- `fetch_models.sh [manifest] [role-prefix]` downloads only rows whose role starts with the prefix
  (default `required`; e.g. `required_edit`, `required_turbo`, `required_7b` are included), pinned to the
  manifest's revision, into `~/AI_models/comfyui`. Details: `models/README.md`.
- The skill has no licence in its source repo, so it is installed locally and never committed
  (`docs/third_party.md`).

## Verify

```bash
./scripts/check.sh                            # the quality gate: run before and after every change
RUN_VISION_INTEGRATION=1 ./scripts/check.sh   # + optional real macOS Vision face check
```

`./scripts/check.sh` runs the offline unit tests and `episode.py validate` for every episode: no ComfyUI,
no rendering, no network. It prints a PASS / FAIL / SKIP summary and exits 1 on any failure. The expected
result is recorded in `docs/status/current.md` → "Test baseline". In a fresh clone or worktree, three
episodes are SKIPped because their reference pictures are local-only (see "Where things live"); that is
expected.

## Quick start (episode)

Brief format: `docs/stage8-brief-format.md`. Full command list and `episode.yaml` format:
`episodes/README.md`.

```bash
PY=~/dev/ComfyUI/.venv/bin/python
# offline (no ComfyUI):
$PY scripts/brief.py validate   episodes/<name>   # check brief.yaml and reference pictures
$PY scripts/brief.py scaffold   episodes/<name>   # write episode.yaml (characters, locations), once
#   ... draft the shots in episode.yaml (official H3 format + direction skill) ...
$PY scripts/brief.py check-plan episodes/<name>   # rules: format, length, sizes that fit, outfits
# starts ComfyUI, renders into ~/AI_renders (approved render task only):
$PY scripts/pipeline.py         episodes/<name>   # render takes, re-rolls, review sheets, assemble when all picks are made
# no ComfyUI needed; picking and confirming takes is the owner's decision:
$PY scripts/review_server.py    episodes/<name>   # http://127.0.0.1:8189 — watch, pick, confirm
# needs a running ComfyUI, writes into ~/AI_renders (approved render task only):
$PY scripts/upscale.py --cut episodes/<name>/cut.yaml   # optional: shots with `upscale: 7b_sharp`
# no running ComfyUI needed; writes render output into ~/AI_renders and may also write subtitles/ and
# runs/ in this repo (approved render task only):
$PY scripts/assemble.py episodes/<name>/cut.yaml        # final MP4s in ~/AI_renders/comfyui/episodes/<name>/_final
```

- `pipeline.py` is safe to run again (finished takes are skipped by fingerprint). Exit code 0 = episode
  assembled or up to date, 2 = waiting for a human decision (picks, a shot that used up its re-rolls),
  1 = error.
- ComfyUI is started only through `scripts/launch_comfyui.sh` (localhost only, no custom nodes, PyTorch
  attention by default, D11/D16); `pipeline.py` does this itself. One ComfyUI and one render at a time.
- Other tools: `scripts/qwen_image.py` (Qwen stills/edits; start ComfyUI with `--bf16-text-enc` for
  edits), `scripts/take_checks.py` (picture checks), `scripts/face_check.py`, `scripts/screen_insert.py`
  (green-screen phone UI), `scripts/audio_clip.py`.

## Models and licences

Weights are not in Git; manifests with SHA-256 are.

| Model | Use | Licence | Manifest |
|---|---|---|---|
| MiniMax H3 (fl2va, ref2va; int8) | video + sound: T2V, I2V, FLF2V, R2V, audio-only assets | H3 community licence — review before any commercial use | `models/manifest.tsv` |
| Qwen-Image 2.1 (+ turbo) | stills, edits, text in pictures, background removal | **research/evaluation only → pictures are non-commercial** (D17) | `models/manifest_qwen_image_2.1.tsv` |
| SeedVR2 3B / 7B sharp (int8) | video upscaling x2 | Apache 2.0 (D18) | `models/manifest_seedvr2.tsv` |

Licence facts (sources: `docs/decisions.md`, `docs/third_party.md`):

- Qwen-Image 2.1 pictures are **non-commercial**: tag them, and replace or license them before any
  monetised use.
- MiniMax H3 weights: community licence, not yet reviewed for commercial use.
- `h3-prompt-writing` skill: no licence in its source repo; local install only, never in Git.
- Third-party / trademark reference pictures stay local-only.

Current commercial-use and public-release gate: `docs/status/current.md` → "Licensing limits".

## Episodes

One folder per episode in `episodes/`. Their state is in `docs/status/current.md`.

| Group | Episodes |
|---|---|
| Delivered work | `midnight_call` (9:16 drama pilot), `sunlight` (9:16, brief → episode end-to-end test), `Urban_Lifestyle_Commercial` ("Be a Little Braver", 16:9 commercial, 64 s; V2 published as [GitHub Release `braver-v2`](https://github.com/ZXBBT/AI_short_drama/releases/tag/braver-v2)) |
| Assets for the commercial | `Urban_Lifestyle_Commercial_audio` (sound assets), `Urban_Lifestyle_Commercial_refs` (reference stills) |
| Tests and experiments | `_e2e`, `_exp_6_3`, `_format_test`, `_location`, `_multiref`, `_quality`, `_selftest`, `_stills` (results in `docs/`) |
| Local-only references | `nailong`, `_owner_selfie`, and `Urban_Lifestyle_Commercial`'s product picture (SKIPped by the gate in a fresh clone) |

## Where things live

| What | Path | In Git? |
|---|---|---|
| This repo: config, scripts, prompts, workflows, subtitles, docs, run metadata | `~/dev/AI_short_drama` | ✅ |
| ComfyUI code (its own git checkout, pinned tag v0.42.1) | `~/dev/ComfyUI` | ❌ (separate repo) |
| Model weights | `~/AI_models/comfyui/<type>/` | ❌ |
| Renders (takes, finals, upscales, Qwen pictures) | `~/AI_renders/comfyui/` | ❌ |
| Local-only reference pictures (owner decision) | `inputs/_owner_selfie/`, `inputs/nailong/`, `inputs/Urban_Lifestyle_Commercial/ref_can_*.png` | ❌ (gitignored) |
| MiniMax `h3-prompt-writing` skill | `.claude/skills/h3-prompt-writing/` | ❌ (gitignored, `scripts/fetch_h3_skills.sh`) |

None of these paths are inside iCloud Drive. Weights and renders are too large for Git and would be
re-uploaded/evicted by iCloud. The V2 commercial was shared as a GitHub Release attachment. For the
current commercial-use and public-release gate, see `docs/status/current.md` → "Licensing limits".

## Repo layout

```
AGENTS.md        rules for every agent and tool; CLAUDE.md = Claude Code entry point
.claude/         settings.json, agents/, rules/, skills/ (h3-short-drama-direction is ours;
                 h3-prompt-writing is fetched, not committed)
docs/            decision log (decisions.md), status/current.md, tasks/ (task cards), stage reports,
                 test results, third_party.md
env/             version log + environment snapshots
models/          model manifests (filenames, sizes, sha256) + verification/ records — never the weights
workflows/
  official/      unmodified official ComfyUI templates (reference copies)
  project/       our edited workflows (diff against official/)
prompts/         prompt text per shot
episodes/        one folder per episode: brief.yaml, episode.yaml, selections.yaml, cut*.yaml
config/          extra_model_paths.yaml; recipes/ = versioned generation settings (h3_base_v1, h3_base_v2)
inputs/          small reference images and location plates used as inputs
subtitles/       .srt files of assembled cuts
scripts/         pipeline, tools and tests
runs/            per-render / per-cut metadata (seed, params, versions, checksums, output path)
```

## Working on this repo

Rules for people and agents: `AGENTS.md` (quality gate, non-negotiables, approval points, task workflow);
Claude Code entry point: `CLAUDE.md`. Every non-trivial change has a task card in `docs/tasks/`; decisions
and their reasons are in `docs/decisions.md`.

## Stage status history (2026-10-23 … 2026-10-26) — not current

History of how the pipeline was built; kept as a record and not updated. Later phases, open items and
the current state: `docs/status/current.md`. Rendering sizes and times measured on this Mac:
`docs/status/current.md` → "Rendering limits".

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
