# Stage 6.2 — Pipeline smoke tests through the API (2026-10-23)

Tool: `scripts/episode.py render` (commit after badd384). ComfyUI v0.42.1, torch 2.14.1 MPS,
recipe `h3_base_v1` (20 steps, res_multistep/simple, fp16 video VAE). Records in `runs/2026-10-23/`.

| Shot | What | Size × frames | Result | Time | Mem peak / swap peak GiB |
|---|---|---|---|---|---|
| `_selftest` T1 | T2V regression vs Stage 5 | 608×352×5 | ✅ **pixel- and sample-identical** to `stage5_repro_a` | 109 s (record of the re-run shows 0.1 s: ComfyUI cache hit) | — |
| `_selftest` I1 | I2V from keyframe | 352×608×5 | ⚠️ ran, but frame 0 ignores the image (see finding 2) | 93 s | 47.5 / 4.8 |
| `_selftest` C1 | continuation of I1 (dependency link, frame extraction, selection) | 352×608×5 | ✅ mechanics work | 96 s | 47.9 / 4.7 |
| `_selftest` R1 | **first R2V on this Mac** (ref2va, D14) | 352×608×5 | ✅ identity kept: same face, hair, coat in a new close-up | 131 s | 53.2 / 14.2 (includes model switch) |
| `midnight_call` S001 | reproduce owner's UI take01 | 352×608×124 | ✅ **pixel- and sample-identical** to the UI video | 581 s (sampling 512 s) | 57.7 / 11.4 |

## Findings
1. **Script = UI = Stage 5.** The episode tool reproduces both the Stage 5 T2V run and the owner's
   UI I2V take exactly. Takes made either way are interchangeable and re-makeable.
2. **I2V needs real length.** At 5 frames, frame 0 differed from the input image by 73/255 on
   average (it was ignored); at 124 frames by 3.8 (followed). Never judge I2V on 5-frame tests.
   Every I2V take now records `continuity.first_frame_diff` and warns above 20.
3. **A keyframe that doesn't show the prompt's scene makes H3 cut.** Owner's take01: keyframe =
   woman standing by a window; prompt = at a desk with a phone, "no cut". H3 kept the keyframe for
   1.5 s, then hard-cut (frame 36, 29× the median frame change) to a desk scene, in a different
   sweater. Take02 started from a frame already showing the desk scene: no cut. Every take now
   records detected cuts and warns.
4. **R2V works on MPS** with the same memory profile as T2V/I2V at this size. Unloading models
   before every render command (added after R1 left ref2va loaded) keeps fl2va and ref2va from
   being resident together.
5. **"best" frame on short clips** searched the whole clip and picked frame 0; the window is now
   the last second or the last quarter of the clip, whichever is shorter.

## Bugs found and fixed during 6.2
- Recipe `created: 2026-10-23` parsed as a YAML date → the first T1 record could not be written
  (render itself succeeded). Fixed (quoted date, `default=str`) + test that shot parameters are JSON.

## Not yet known (→ 6.3)
- I2V/R2V at 0.4 MP and > 5 s; R2V identity across several shots and angles; scheduler A/B;
  seed-vs-size; `continue_motion`.
