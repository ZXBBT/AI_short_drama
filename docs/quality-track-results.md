# Quality track — faces at a distance, character consistency (2026-10-24)

Owner's complaint: the female lead's face is blurred and its features misaligned when she is
further from the camera; she should stay consistent. Episodes: `episodes/_quality`,
`episodes/_location`. Records: `runs/2026-10-24/`. Crop sheets: `~/AI_renders/comfyui/episodes/_quality/_review/`.

## Measuring the problem (`scripts/face_check.py`)
macOS's built-in Vision framework (Swift helper `scripts/face_boxes.swift`, nothing installed,
nothing leaves the Mac) gives per-frame face height in pixels and a face capture quality score
(0-1). Checked against the owner's own verdicts on Midnight Call before being used:

| Take | Owner's verdict | Face height | Quality (median) |
|---|---|---|---|
| S004 s402 (wide) | blurred, features misaligned | 21.5 px | 0.12 |
| S005 s501 (full body) | still blurred | 30.5 px | 0.15 |
| S004a / S002 / S005b (medium, close) | fine | 122-176 px | 0.51-0.65 |

Clean separation, so the score is used as a ranking aid (plan rule: trusted only after it agrees
with the owner). It does not measure skin texture: the owner's reference video scores 0.67, about
the same as our close-ups, although its face is 1,276 px tall.

## Batch 1: one borderline medium-wide shot, same seed, one change at a time
| Shot | Change | Face px | Quality | Time | Swap peak | Note |
|---|---|---|---|---|---|---|
| QB | baseline (352x608, 5 s, 1 ref, match) | 54 | 0.21 | 8.2 min | 6.4 GiB | soft, smeared features |
| Q1M | `ref_image_size: max` | 59 | 0.23 | 12.0 min | 12.7 GiB | +47 % time for a small gain |
| Q1S | 3-picture character sheet | 78 | 0.25 | 12.9 min | 10.2 GiB | H3 turned her to profile mid-shot |
| Q1SM | sheet + max | 78 | 0.25 | 13.5 min | 14.5 GiB | unwanted hard cut (frame 61) |
| Q2L | baseline at 3 s | 47 | 0.18 | 5.9 min | 4.6 GiB | fair twin of Q2H |
| **Q2H** | **480x864 (0.4 MP) at 3 s** | **90** | **0.52** | 12.0 min | 9.4 GiB | **sharp, features aligned; fits in memory** |

**Finding: render size is the lever.** At the same 3 s, 0.4 MP nearly doubles the face size and
triples the quality score (Q2L 0.18 → Q2H 0.52); visually the eyes, nose and mouth line up.
Reference tricks barely help and add risk. X4 showed 0.4 MP × 5 s does not fit; 0.4 MP × 3 s does.

## Batch 2 (overnight, 9 renders, no failures)
| Shot | Change | Face px | Quality | Time | Mem / swap peak | Verdict |
|---|---|---|---|---|---|---|
| QA | Q2H with ComfyUI `--use-pytorch-cross-attention` | 94 | 0.53 | 10.9 min (sampling 590 s vs 642 s) | 52.1 / **3.6 GiB** (Q2H 55.8 / 9.4) | same shot and quality (pixels differ by 10.8/255 on average: different rounding), **8 % faster, ~4 GB less memory, much less swap** |
| Q3a | 544x960 (0.5 MP) × 3 s | 82 | 0.32 | 16.0 min | 58.1 / 7.4 GiB | **fits**; H3 framed her wider at this size |
| Q3b | 480x864 × 4.5 s (107 frames) | 71 | 0.32 | 18.3 min | 57.1 / 8.7 GiB | **fits**; also framed wider |
| G1 | owner's reference genre (daylight selfie close-up, T2V) at 480x864 | 490 | 0.61 | 10.3 min | 55.0 / 5.6 GiB | **photoreal: pores, blemishes, fine hair, natural daylight** |
| G2 | same at 352x608 | 422 | 0.62 | 5.4 min | 53.1 / 7.0 GiB | **also photoreal**, slightly less fine detail |
| P0 | room plate: 5-frame T2V at 768x1376 used as a still | – | – | 3.0 min | 52.4 / 6.8 GiB | clean empty-room picture |
| L0 | woman at the desk, no room reference (control) | 94 | 0.37 | 13.0 min | 57.5 / 11.4 GiB | room invented (wooden windows) |
| L1 | same + room plate as `<Picture 2>` | 47 | 0.17 | 12.8 min | 57.6 / 6.8 GiB | **room kept** (walls, pleated lamp, window); camera pulled back, side view |
| L2 | standing by the window + room plate | – | – | 14.1 min | 56.4 / 9.6 GiB | **opens on the exact plate**, then she is seen from behind |

Note: the face score also depends on framing. At larger sizes H3 composed the same "medium-wide"
prompt wider (Q3a/Q3b), so their faces are smaller than Q2H's even with more pixels.

## Conclusions
1. **Content and framing decide realism more than anything else.** The daylight selfie close-up
   (G1/G2) is photoreal on this Mac even at 352x608: the face fills the frame (420-490 px) in soft
   daylight. Our drama shots put a 20-90 px face in low night light; no setting fixes that.
2. **For faces that are not close-ups, render size is the lever.** 0.4 MP (480x864) triples the face
   quality score at the same framing (Q2L 0.18 → Q2H 0.52). Fits at 3 s and at 4.5 s; 0.5 MP fits at 3 s.
3. **PyTorch attention is a free win** (same picture, 8 % faster, ~4 GB less memory). It changes the
   exact pixels, so it must become part of the recipe and the fingerprint before it is adopted.
4. **Reference tricks help little:** `ref_image_size: max` +0.02 quality for +47 % time; a 3-picture
   character sheet changed the acting (profile turn, one unwanted cut).
5. **Location pictures keep a room consistent but take over the camera.** A second reference (room or
   person) pulls the camera back; a room plate can become the opening frame. Use plates as the start
   frame of establishing shots (I2V), and keep close-ups/medium shots on the character reference only.

## To-do #6: H3 as the still-image generator (2026-10-24, episodes/_stills)
5-frame clips at 768x1376 (~1 MP, H3's design canvas), official prompt format, sharpest/best-face frame
kept. Recipe h3_base_v2 (PyTorch attention). Sheets: `~/AI_renders/comfyui/episodes/_stills/_review/`.

| Still | Time | Face px | Quality | Verdict |
|---|---|---|---|---|
| A1 new character from text (T2V), 2 seeds | 1.7-2.3 min | 540-555 | 0.69-0.70 | natural phone-photo portrait, as good as the owner's selfie reference (0.70); no "AI portrait" look |
| A2 Lin from her 480x864 reference (R2V), 2 seeds | 2.6-3.6 min | 650-690 | 0.58-0.62 | same identity (face, eye shape, moles), 2.6x the pixels, crisper eyelids/lips/skin; cannot invent detail the small source lacked |
| A3 park plate (T2V), 2 seeds | 2.0-2.2 min | - | - | clean, realistic; s32 sharper (1398 vs 572) |
| for comparison: SDXL keyframe / Lin G1-frame reference | - | 299 / 489 | 0.85 / 0.64 | SDXL scores high but looks smooth/artificial; G1 frame is real-looking but small |

**Conclusion:** H3 itself is a good reference and background generator: ~2-4 min per picture, no new
model or licence, memory peak <= 53 GB. R2V also works as a re-posing tool for an existing character.
Limits: ~1 MP maximum (H3's canvas), no precise editing (change one detail, remove a background) and
no reliable text rendering; those are what a dedicated image model would add (to-do #7).
