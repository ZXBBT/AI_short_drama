# Stage 6.3 — Pilot: Midnight Call + experiments (2026-10-23)

Recipe `h3_base_v1`, 352×608 (9:16, 0.2 MP), 20 steps. Records: `runs/2026-10-23/`;
review sheets: `~/AI_renders/comfyui/episodes/<episode>/_review/` (`scripts/review_sheet.py`).

## Experiments (`episodes/_exp_6_3`)
| Exp | Question | Result | Time | Swap peak |
|---|---|---|---|---|
| X1 | R2V close-up, front | ✅ identity + outfit kept | 9.0 min | 7.9 GiB |
| X2 | R2V profile (angle not in the reference) | ✅ identity kept; she barely walks | 10.3 min | 6.5 GiB |
| X3 | R2V wide, full body | ✅ outfit kept; face too small to judge | 11.8 min | 7.5 GiB |
| X4 | R2V 0.4 MP (480×864) × 5 s | ❌ swap guard stopped it after 70 s (swap 32 GiB, memory 61 GiB) | — | 32.2 GiB |
| X5 | R2V 8 s | not run (batch stops at first failure) | — | — |

## Pilot episode (`episodes/midnight_call`, story by owner, shot list owner-approved)
| Shot | Type | Selected take | Notes |
|---|---|---|---|
| S001 | I2V from keyframe | s102 | starts exactly on the keyframe (diff 3.7), no cut |
| S002 | R2V close-up | s202 | answers the phone |
| S003 | I2V continuing S002's last frame | s301 | seamless continuation; the flash |
| S004a | R2V medium close-up, 3 s | s411 | added after owner review (replaces S004's blurred wide part) |
| S004 | R2V wide | s402 | H3 cut by itself at ~3 s in both takes → use frames 69-123 (door + man) |
| S005 | R2V woman + man refs | s501 | H3 framed her full-body despite "waist-up" → use ~2 s as establishing shot |
| S005b | R2V close-up, her ref only, 3 s | s521 | added after owner review; face sharp; man's hood shows down at the edge |

16 takes (incl. reruns), all successful; 5-12 min each. No swap-guard trips on story shots.

## Findings
1. **Faces need size.** At 352×608 a face below ~2 latent cells (~30 px) blurs and its features
   drift (owner, S004 and S005). Close-ups (150-250 px faces) are sharp. Rule: faces that matter
   at medium shot or closer. 0.4 MP is not available for R2V at 5 s (X4).
2. **Two full references pull the camera back.** With woman + man references H3 framed both
   full-body (S005, both seeds) although the prompt asked for waist-up. Single-subject shots with
   one reference keep the requested framing (S004a, S005b).
3. **H3 cuts on dramatic events by itself** (S004: wide → door, both seeds). Usable: the edit
   takes frame ranges. The cut detector finds them reliably (no false positives in 16 takes).
4. **Reference hubs work.** The man was created in S004 and fixed by extracting its last frame as
   a reference asset; continuation by last frame only works when the next shot shows the same
   subjects from the same camera (S002 → S003 ✅).
5. **Prompts that describe what is visible avoid unwanted cuts** (new S001: no cut; old UI take:
   cut at 1.5 s).
6. **Things the prompt did not mention drift** (the man's hood in S005b). Name every visible
   detail that must stay consistent.

## Not done in 6.3 (still open)
Scheduler A/B, seed-vs-size, 8 s clips, `continue_motion`, attention test. None blocks assembly.
