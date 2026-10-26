# Stage 8 improvements (owner-approved 2026-10-26)

From the Sunlight run's review list. All checks are **warnings** shown on the review page; they never
reject a take. Calibrated on takes the owner already reviewed.

## 1. Picture checks: `scripts/take_checks.py` (+ `scripts/frame_checks.swift`)
macOS Vision framework, on the Mac only, nothing downloaded. Every 2nd frame is measured once and the
measurements are cached next to the video (`<video>.checks.json`); verdicts are recomputed from them, so
threshold or prompt changes need no new measurement. Runs automatically after each render
(`episode.py`), feeds auto-pick (takes without warnings rank first) and the review page.

| Check | How | Calibration (owner-reviewed takes) |
|---|---|---|
| Text in the picture | Vision text recognition; a word counts if seen in ≥ 3 sampled frames. Text in double quotes in the prompt is allowed; `<d>` dialogue never is | old Sunlight P4 s402: **"Over here!" caption found** from frame 44; commercial S5A/S8A: garbled can print "300 m", "DRY R", "500 гml" found; new P2/P3/P4/F2/F4: none |
| Looks into the lens | head yaw ≤ 12°, pitch ≤ 15° and both irises centred (darkness-weighted centroid inside the eye outline, ±12 % of eye width) in ≥ 15 % of face frames; allowed only when the prompt asks for it | V1 S2B (owner: eye contact) **22 % → warns**; old P4 takes 84-97 %; new P2/P3/P4: 0 %; S3C2 (fridge point of view) 67 % → warns; owner reviewed it and kept it (the cans sit where the lens is) |
| Lips move in a silent shot | inner-lip opening ÷ face height; open/close cycles with hysteresis (2.5 % of face height); ≥ 3 cycles per 4 s warns when nobody on screen should speak (no `<d>`, voice-over, "lips stay closed") | V1 S1B narration shot 4.3/4 s → warns; S2A2 3.2 → warns (to check: a smile also moves the lips); P4 "Over here!" 2.1 (speaks); new P3 0 |

## 2. Outfit completeness: `brief.py check-plan`
Warns when a shot shows the lower body (walks, stands up, lap, full body…) but the character description
names no trousers/skirt/dress, when a shot may show the feet but no shoes are named, and when no top is
named. Sentences about other people ("Nobody walks across…", background) are ignored. On Sunlight it flags
P2/P4/P5: Lin's episode description still lacks "black trousers" (the format-test prompts wrote them out).
Adding them would change the prompts (new fingerprints) — owner's decision.

## 3. Official length rule: `brief.py check-plan`
R2V `detailed_description` under 350 words warns (MiniMax ref-en.txt: "normally 350-500 English words"; a
single shot does not justify a shorter one; dialogue-dense shots may be shorter). The commercial's R2V
prompts were 241-336 words; the new `_multiref` prompts are 356-362.

## 4. Loudness: optional limiter (`loudness.limiter: true` in cut.yaml)
Levelling stays measured (BS.1770) and per-shot auto levelling stays the default. Without the limiter a cut
stops at the peak ceiling ("quieter than target"). With it, a look-ahead peak limiter (5 ms look-ahead,
150 ms release) pulls only the loudest peaks under the ceiling; the gain is raised and limited again until
the target is reached or peak reduction would exceed 6 dB (more audibly squashes a shout).
Sunlight v2: without −17.6 LUFS; with −16.8 LUFS (4.1 dB peak reduction). The cut's loudness is the shouted
"Over here!" (P4 −11.3 LUFS vs ambience shots −38 to −52), so −14 is out of reach without squashing it; the
fix there is per-shot (`gain_db` on P4), not more limiting. The delivered v2 stays without the limiter.

## 5. Also added tonight
- `mirror: true` per sequence entry in cut.yaml (flip a take left-right to match an eyeline). Not needed
  for Sunlight v2: Vision head yaw shows P3/P4/P5 all turn the same way (−45/−20/−45°).
- Tests: `test_take_checks.py` (new, 20), `test_brief.py` (+9), `test_assemble.py` (+6); all pass.
