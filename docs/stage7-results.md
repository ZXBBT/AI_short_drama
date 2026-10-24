# Stage 7 — Automation results (2026-10-24)

Plan: `docs/stage7-plan.md`. Built: `scripts/pipeline.py`, `scripts/review_server.py`, re-roll
policy in `scripts/episode.py`, `assemble.py --init` and `loudness.per_shot: auto`.

## 7.4 End-to-end test (`episodes/_e2e`, logs in `~/AI_renders/comfyui/episodes/_e2e/_logs/`)
ComfyUI was stopped beforehand (owner's option A), so the pipeline had to start it itself.

| Step | Expected | Result |
|---|---|---|
| 1 `pipeline.py` | start ComfyUI, render E1 (T2V), E2 waits for a pick, stop ComfyUI | ✅ started in 5 s, E1 146 s, stopped, exit 2 |
| 2 pick E1 via review page | saved | ✅ |
| 3 `pipeline.py` | render E2 (continues E1's last frame) | ❌ first run: nothing rendered (bug, below); ✅ after the fix: E2 170 s, exit 2 |
| 4 pick E2 via review page | saved | ✅ |
| 5 `assemble.py --init` | default cut list | ✅ |
| 6 `pipeline.py` | assemble without starting ComfyUI | ✅ auto levelling E1 −2.1 / E2 +2.1 dB, −14.3 LUFS, exit 0 |
| 7 `pipeline.py` again | nothing to do | ✅ "already assembled", exit 0 |
| 8 edit `cut.yaml` after assembly | refuse to overwrite v1 | ✅ "stale: change version", exit 2; restored → "current" |

## Bug found and fixed
A shot continuing another shot looked **blocked** until its start frame had been extracted, and
frames were only extracted during a render. So after a pick, `pipeline.py` saw nothing to render.
Fix: continuation frames are now extracted whenever they are first needed (cheap, written only to
the renders folder); "blocked" now only means "waiting for a pick". `plan` shows such shots as todo.

## Data points
- I2V at 39 frames follows its start image (frame-0 difference 4.4; at 5 frames it was 73).
- ComfyUI cold start by the pipeline: 5 s (after the first-ever launch).

## Daily use
```
PY=~/dev/ComfyUI/.venv/bin/python
$PY scripts/pipeline.py episodes/<name> --stop-comfyui     # render what's possible, then stop
$PY scripts/review_server.py episodes/<name>               # http://127.0.0.1:8189 → Pick
$PY scripts/assemble.py episodes/<name> --init             # once, then edit cut.yaml
$PY scripts/pipeline.py episodes/<name>                    # renders the rest / assembles
```
Claude runs the pipeline in the background and pushes a phone notification when it ends.
