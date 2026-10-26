# Stage 8 draft — the episode brief (format proposal, 2026-10-24)

Status: **built (8.1-8.5), 2026-10-24; end-to-end test (8.6) pending owner approval.** Goal: the owner writes one short brief
(plot direction + a few character and background images); the system turns it into a shot list,
renders, picks, edits and assembles a complete episode, stopping only where the owner wants to decide.

## 1. Where it lives
```
episodes/<name>/brief.yaml      ← the only file the owner has to write
episodes/<name>/episode.yaml    ← generated from the brief (shot list), then validated
episodes/<name>/selections.yaml ← auto-picks and/or owner picks
episodes/<name>/cut.yaml        ← generated edit (order, trims, subtitles, loudness)
inputs/<name>/                  ← the owner's images (characters, backgrounds)
```

## 2. The brief, field by field
| Field | Required | Meaning | Example |
|---|---|---|---|
| `episode`, `title` | yes | folder name and display title | `midnight_call`, "Midnight Call" |
| `plot` | yes | the story direction in your own words, any length | "The phone rings at night…" |
| `beats` | no | optional ordered list of moments you insist on (else derived from `plot`) | "she answers, no one speaks" |
| `target.length_s` | yes | approximate finished length in seconds | `30` |
| `target.aspect` | no | `9:16` (default), `16:9`, `1:1` | `9:16` |
| `target.language` | no | language of dialogue and subtitles | `en` / `zh` |
| `style` | no | look, lighting, mood in plain words; added to every prompt | "realistic cinematic thriller" |
| `characters.<id>.description` | yes per character | how they look; becomes `{id}` in every prompt, word for word | "young East Asian woman…" |
| `characters.<id>.images` | recommended | 1-3 pictures: front, 3/4, profile; the first is the main one | `inputs/midnight_call/woman_front.png` |
| `characters.<id>.voice` | no | how they sound (H3 generates the voice) | "soft, nervous" |
| `locations.<id>.description` | yes per location | the place in words | "small dim apartment, rain on the window" |
| `locations.<id>.images` | no | background pictures of the place | `inputs/midnight_call/apartment.png` |
| `dialogue` | no | lines you insist on; otherwise Claude proposes lines with the shot list for your approval | `woman: "Hello?"` |
| `budget.takes_per_shot` | no | seeds per shot (default 2) | `2` |
| `budget.max_render_hours` | no | the shot list must fit (estimated from past renders) | `4` |
| `review.picks` | no | `auto` (system picks best take) or `owner` (you pick on the review page) | `auto` |
| `review.final` | no | `true` (default) = stop before assembling so you watch the takes once | `true` |

## 3. What happens with each part
| Step | Done by | Rules applied (learned in Stages 6-7) |
|---|---|---|
| brief → shot list (`episode.yaml`) | **Claude**, in this chat; you approve once (or `autopilot: true` to skip) | faces at medium shot or closer; one character reference per shot; wides as silhouettes/backs; continuations only when the camera keeps rolling; every prompt uses `{character}` placeholders; keyframes must show the prompt's opening; dialogue lines become subtitle text |
| validate | `episode.py validate` | ids, images, tags, sizes, small-face warning, render-time estimate vs `max_render_hours` |
| render + re-rolls | `pipeline.py` | unchanged (Stage 7) |
| pick | `auto`: best good take by checks + face score; `owner`: review page | auto-picks are written with a note; your pick always overrides |
| edit (`cut.yaml`) | generated | order = story order; trims at H3's own cuts when a shot asks for none; subtitles from dialogue; per-shot loudness auto |
| assemble | `assemble.py` | unchanged; new version number on every change |

## 4. How background images are used (to be tested before relying on them)
| Use | When | Risk |
|---|---|---|
| start frame of an establishing shot (I2V) | the shot opens on the empty place | the prompt must describe exactly what the picture shows, or H3 cuts away |
| extra reference in R2V (`<Picture 2>` = the room) | keep the same room behind a character | two **character** references pulled the camera back (S005); a **location** reference is untested |

## 5. What stays manual or limited
- The shot list needs Claude (this chat). Fully unattended writing would need the Claude API: an
  external, paid service and a separate approval.
- Auto-picking catches broken takes and blurry faces, not acting quality or story sense.
- Time: ~10 min per 5 s shot at 352x608 → a 60 s episode ≈ 12 shots × 2 takes ≈ 4 h (overnight).
- Picture quality is limited by the render size (quality track in progress).
- Licensing review before any public or paid use.

## 6. Owner decisions (2026-10-24)
1. **Show the takes before assembly by default:** `review.final` defaults to `true`, also with
   `picks: auto` (auto-picks are pre-selected; the owner confirms or changes them on the review page).
2. **Dialogue:** Claude proposes the lines in the shot list; the owner approves them with the shot list.
   Lines written in the brief's `dialogue` are used as given.
3. **Location reference test:** yes, 2-3 renders, after the quality track is finished.

## 7. How to use it (built 2026-10-24)
```
PY=~/dev/ComfyUI/.venv/bin/python
$PY scripts/brief.py validate   episodes/<name>   # 1. check your brief + reference faces
$PY scripts/brief.py scaffold   episodes/<name>   # 2. episode.yaml without shots (recipe h3_base_v2)
#    3. Claude drafts the shots + dialogue in episode.yaml in H3's official prompt format
#       (h3-prompt-writing skill, docs/third_party.md); you approve them
$PY scripts/brief.py check-plan episodes/<name>   # 4. rules + length + render-time estimate
$PY scripts/pipeline.py episodes/<name> --stop-comfyui    # 5. render -> auto-pick -> render -> cut list
$PY scripts/review_server.py episodes/<name>      # 6. watch, change picks, press "Confirm picks"
$PY scripts/pipeline.py episodes/<name>           # 7. assembles (native + 1080x1920)
```
| Part | Script | What it enforces / does |
|---|---|---|
| 8.1 brief checker | `brief.py validate` | required fields; images exist; main reference face >= 300 px and quality >= 0.5 (warning) |
| scaffold | `brief.py scaffold` | recipe `h3_base_v2` (PyTorch attention, D16); 480x864 / 3 s defaults; one picture per character; location plates; review settings |
| 8.2 plan checker | `brief.py check-plan` | R2V = exactly one character; plates only as I2V start frames; only sizes/lengths proven on this Mac; `{name}` placeholders; dialogue present; length vs target; render hours vs budget |
| 8.4 auto-pick | `autopick.py` via `pipeline.py` | best good take by face quality then size; marked "auto-pick"; your picks replace them; assembly waits for "Confirm picks" (`final: true`) |
| 8.5 auto edit | `assemble.py` via `pipeline.py` | cut list from picks: story order, longest uncut part when H3 cut by itself unwanted, subtitles timed on the detected voice, auto levelling, native + 1080x1920; new version when picks change |

Measured on Midnight Call: auto-pick agreed with the owner's picks on 6 of 7 shots; the voice
detector placed "Hello?" at 4.65 s (the owner's take); check-plan flags S005 (two references) and S004
(wide framing), the two shots the owner found blurred.
