# Stage 7 — Automation (started 2026-10-24)

Goal: one command takes an episode from `episode.yaml` to a finished cut, stopping only where a
human decision is needed (picking takes, approving the edit). Everything stays local; renders never
leave the Mac (owner's choice). Claude starts batches and pushes the phone notification when they
end (owner's choice). Builds on Stage 6 (`docs/automation-plan.md`).

## What the pilot showed to be repetitive
| Manual step in 6.3/6.4 | Automated by |
|---|---|
| re-rendering when a take had an unwanted cut / ignored its image | 7.1 automatic re-rolls with a per-shot budget |
| starting ComfyUI, waiting for it to be idle, chaining rounds | 7.1 `pipeline.py` |
| building contact sheets, sending videos, typing picks in chat | 7.2 local review page with one-click picks |
| writing `cut.yaml` by hand; per-shot volume jumps (~22 LU) | 7.3 `--init` cut list + optional per-shot auto-levelling |
| re-assembling after every change | 7.1 `pipeline.py` assembles when everything is selected |

## Sub-steps (each ends with tests and a checkpoint)
| Step | Deliverable |
|---|---|
| **7.1 Batch runner** ✅ | `allow_cuts` / `max_rerolls` per shot; quality-check re-rolls; `scripts/pipeline.py` (validate → start ComfyUI if needed → render everything renderable → review sheets → assemble when possible → summary JSON + exit code) |
| **7.2 Review page** ✅ | `scripts/review_server.py`: http://127.0.0.1:8189, every take playable with its checks and timings; "Pick" writes `selections.yaml` |
| **7.3 Cut helpers** ✅ | `assemble.py --init` writes a default cut list; `loudness.per_shot: auto` narrows shot-to-shot volume jumps (explicit `gain_db` wins) |
| **7.4 End-to-end test** | `_selftest` run through `pipeline.py` with ComfyUI started by the pipeline itself (needs owner's go-ahead for ~15 min of rendering) |

## Rules kept
Same safety as Stage 6: refuse while ComfyUI is busy, unload models first and between families,
swap guard 20 GiB, stop the batch on any render error. A re-roll is only triggered by a failed
quality check (unwanted hard cut; I2V frame 0 not following its image), never by an error, and
never beyond the shot's budget. Human picks always override automatic checks.
