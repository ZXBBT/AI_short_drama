# Automation plan: from script to episode (Stages 6–7)

Status: Stage 6 approved 2026-10-23. This document is the design; each part is built and tested
in the sub-steps of §5, with a checkpoint after each.

## 1. Core idea
Everything clicked in the ComfyUI UI can be sent to ComfyUI's local HTTP API as a graph. That is
how every Stage 4–5 render was made (`scripts/run_h3_t2v.py`): same nodes, same models, same
results (Stage 5: identical output for the same seed). Automation extends this proven path; it
adds no custom nodes, no cloud services and no new ML models.

Why automate: one 5 s, 352×608 clip takes ~9 min here (measured on the owner's I2V takes), so a
60 s episode is ~12 clips × several takes ≈ hours of rendering. The pay-off is unattended,
recorded overnight batches. Creative decisions stay human.

```
script ──► episode.yaml (shots + links) ──► render queue ──► takes ──► review ──► selections ──► assembly
  you        Claude drafts, you approve       scripts       records    page        you          script
```

## 2. Episodes are data
`episodes/<name>/episode.yaml` (in Git) describes one episode:

- **recipe**: a named, versioned set of sampler/scheduler/steps/model files (`config/recipes/`).
- **assets**: reference images and approved keyframes (files in `inputs/`, checksummed).
- **characters**: description + which assets show them.
- **shots**: type (`t2v`, `i2v`, `flf2v`, `r2v`), duration, size, prompt, seed(s), and links.

`episodes/<name>/selections.yaml` records which take of each shot you picked. Takes (videos) live
in `~/AI_renders/comfyui/episodes/<name>/`; their full records in `runs/<date>/`.
Format details: `episodes/README.md`.

## 3. Shots form a dependency graph, not a line
Blindly chaining "last frame of the previous clip → first frame of the next" has four problems:

| Problem | Why |
|---|---|
| Drift accumulates | every generation adds small errors (colour, face, sharpness); shot 10 of a chain has drifted far from shot 1 |
| Cuts don't need continuity | a reverse angle or close-up must not start from another camera's last frame; only "same camera keeps going" shots should |
| The last frame is often bad | motion blur, mid-blink, transitions |
| One re-render silently invalidates everything after it | a line cannot tell which later shots used it |

**Design: approved keyframes and references are the hubs, not other shots.** Each shot names what
it depends on, with a typed link:

| Link | Meaning |
|---|---|
| `first:` / `last:` an asset | start (or end) on an approved keyframe; many shots can share one, so drift cannot accumulate |
| `first: {shot: S001, frame: best}` | continue another shot: uses that shot's *selected* take; `best` = sharpest frame of its last second, or `last`, or a time in seconds |
| `refs: [character or asset ids]` | R2V references, in order → `<Picture 1>`, `<Picture 2>`, … |
| *(later)* `continue_motion` | anchor the last frames of a clip, not one still, via the official `MiniMaxH3AddGuide` node, to carry motion across a cut-free continuation. Untested |

What the graph gives us, like a software build system:
- **Fingerprints.** Each shot's fingerprint is a hash of its exact API graph (prompt, size, length,
  recipe, model files) plus the content hash of every input image (including frames taken from
  upstream takes). Change shot 3 → its fingerprint and those of shots that continue it change;
  everything else stays done.
- **Order.** Any topological order is valid; among valid orders the runner groups shots by model
  family (fl2va for T2V/I2V/FLF2V, ref2va for R2V) and unloads models between families, so two
  21 GB diffusion models are never resident together (D14).
- **Blocking.** A shot that continues another waits until you have selected a take of it.

Evidence (owner's practice, 2026-10-23): `midnight_call` S001 take 2 started from frame 122 of 124
of take 1. Hand-picking a near-last frame worked; the graph makes that choice explicit and recorded.

**The continuation frame is also the cut point.** On that same take, `frame: best` picks frame
107 (sharpest in the last second), 0.7 s before the end. If the next shot starts from frame 107,
the edit must cut the earlier take at frame 107 too, or the action repeats. So assembly (6.4)
trims every continued take at its recorded frame index (stored in each take's record under
`inputs.first.index`). If a shot should keep its full length, use `frame: last` instead.

## 4. Parameters: tune recipes rarely, choose takes per shot
Facts for H3 here:
- **There is no CFG** in the official H3 workflows: all local templates use `BasicGuider` (one
  model pass per step, no negative prompt). Adding CFG would double time per step and is
  untested for H3. Not a tuning knob for now.
- Real knobs: **steps** (20; 8 with turbo), **sampler/scheduler** (`res_multistep`/`simple`; the
  R2V template note suggests `beta` or `normal` for reference-heavy prompts), **shift**
  (`ModelSamplingMiniMaxH3`: video 12, audio 3), **`ref_image_size`** (`match`/`max`).
- Biggest factors are not numbers: **prompt wording** (R2V is "very sensitive to prompt wording"
  per the template) and **reference image quality**.
- Every sample is expensive (~2–9+ min). A 3 schedulers × 3 steps × 4 seeds grid = 36 renders ≈
  5 h for one shot, so automatic optimizers needing hundreds of samples are out.

**A. Recipe parameters** (sampler, scheduler, steps, shift, ref size): tune by controlled
experiment, then lock.
1. A small benchmark: 4–6 typical shots (dialogue close-up, two characters, wide with motion, R2V
   identity).
2. Change one parameter at a time, same 3–4 seeds for every setting (paired comparison).
3. Blind review: the review page hides which setting made which take.
4. Winner becomes a new recipe version (`config/recipes/h3_<x>_v2.yaml`) with a decision-log entry.
   Re-tune only when model, ComfyUI or PyTorch changes.

**B. Per shot:** prompt first (iterate small and short), then **best-of-N seeds** at final settings.
A seed is not tunable (a good seed for one prompt says nothing about another); "seed search" just
means rendering N takes and choosing. N by importance (e.g. 2 for filler, 6 for a key beat). Caveat:
a different size or length gives different noise, so low-res previews choose prompts and
recipes, not seeds, unless a test proves otherwise.

**Scoring: automatic filters, human decision.**

| Level | Examples | Status |
|---|---|---|
| 1 hard checks (reject) | black/frozen frames, non-finite or clipped audio, wrong frame count | partly in `run_h3_t2v.py` |
| 2 ranking aids | sharpness, flicker; face similarity to character refs; Claude's written ranking of frame sheets | later; a face model needs its own licence check (several popular ones are non-commercial) |
| 3 decision | review page → `selections.yaml` | you |

A ranking aid is trusted only after it agrees with your past picks.

## 5. Stage 6 sub-steps (each ends with a checkpoint)
| Step | Deliverable | Needs |
|---|---|---|
| **6.1 Foundation** | this plan; episode format; recipe file; `scripts/episode.py` with `validate`, `plan`, `render`, `select`, `frame`; offline tests | — |
| **6.2 Smoke tests** | via the API: T2V regression (must match Stage 5 output exactly), tiny I2V, tiny continuation, **first R2V on this Mac**; reproduce owner's S001 take to prove script = UI | ComfyUI free for ~25 min |
| **6.3 Pilot experiments** | 3–5 shot pilot (owner's story): clip length ladder (5 s+), R2V identity test, scheduler A/B, seed-vs-size test; review page | owner's story + reference images; several hours of rendering |
| **6.4 Assembly** | join selected takes, `.srt` from dialogue, loudness matching, episode manifest | decide tool: PyAV (already installed) vs ffmpeg CLI (not installed; install needs approval) |

Stage 7 then automates what 6.3/6.4 showed to be repetitive: overnight batch runner, review page
with selection write-back, ranking aids, recipe experiments.

## 6. Open questions the pilot must answer
1. Do 5 s clips work at 0.4 MP, and does anything above 5 s fit in memory? (5 s at 0.2 MP: yes, ~9 min.)
2. Does `continue_motion` (multi-frame guide) carry motion better than one still?
3. Does a seed keep its composition at another size?
4. Does `beta`/`normal` beat `simple` for R2V here?
5. How well does R2V keep a face, and which kind of reference image works best?
