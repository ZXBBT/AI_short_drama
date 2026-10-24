# Stage 6.4 — Assembly (2026-10-24)

Tool: `scripts/assemble.py` (PyAV 19.0.2, bundled FFmpeg libs; no new software).
Cut list: `episodes/midnight_call/cut.yaml`. Manifest: `runs/2026-10-24/midnight_call__cut_v1.json`.
Outputs: `~/AI_renders/comfyui/episodes/midnight_call/_final/midnight_call_v1_{352x608,720x1280}.mp4`
(+ `.srt`); subtitles in Git: `subtitles/midnight_call_v1.srt`.

## Timeline v1 (25.92 s, 622 frames)
| Time | Shot | Take | Frames used |
|---|---|---|---|
| 0.00–5.17 | S001 | s102 | all |
| 5.17–10.33 | S002 | s202 | all ("Hello?" subtitle 9.77–10.27, estimated from audio) |
| 10.33–15.50 | S003 | s301 | all |
| 15.50–18.54 | S004a | s411 | all |
| 18.54–20.83 | S004 | s402 | 69–123 (from H3's own cut) |
| 20.83–22.88 | S005 | s501 | 0–48 |
| 22.88–25.92 | S005b | s521 | all |

## Verified
- Every output frame matches its source frame (mean difference 0.5–2.2 / 255 = H.264 re-encode only);
  video and audio both exactly 25.917 s; take audio aligned to video within 1 sample.
- Cuts land on the intended frames (S004 starts on the door; S002 → S003 continuation seamless).
- Loudness measured with FFmpeg's `ebur128` (BS.1770); validated: a −20 dBFS sine measures −20.0 LUFS.
- 720×1280: Lanczos scale to 742×1280, centre crop 11 px per side (352×608 is not exactly 9:16).
- `scripts/test_assemble.py` and `scripts/test_episode.py` pass. Assembly takes ~3.5 s.

## Findings
1. **Shot loudness varies by ~22 LU** (S002 −10.0 LUFS, S005 −31.6 LUFS). H3 levels each clip on
   its own. The whole-episode gain cannot fix it: S002's peak (−0.5 dBTP) already sits at the ceiling,
   so v1 is −17.5 LUFS, below the −14 target, and the climax is very quiet. Fix in the cut list with
   per-shot `gain_db` (owner's call, by ear), not by squashing the whole mix.
2. **Continuity jump S003 → S004a**: S003 ends with the phone away from her ear in the blue flash;
   S004a starts with the phone at her ear in warm light.
3. **No subtitle track inside the mp4**: PyAV cannot open FFmpeg's `mov_text` encoder (needs a header
   PyAV can't set). Subtitles ship as `.srt` next to the video (players and platforms accept it).
4. **Upscaling adds no detail**: 720×1280 is a plain resize of 352×608. Real detail needs an AI
   upscaler (separate approval: model + licence) or larger renders.
