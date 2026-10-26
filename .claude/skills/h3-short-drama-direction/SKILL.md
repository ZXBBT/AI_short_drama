---
name: h3-short-drama-direction
description: Project direction rules for MiniMax H3 shot lists in this repo (short dramas and commercials). Use together with h3-prompt-writing whenever drafting or revising episode.yaml shots, planning renders, or building an edit/soundtrack - it adds what the official format does not cover - gaze targets, believable background people, emotion beats, geometry-first stills, object continuity, narration/music added in the edit, and phone screens as composites.
---

# H3 short-drama direction (project skill)

`h3-prompt-writing` (MiniMax, vendor files, never edited) defines the prompt **format**. This skill
defines **what to direct** in that format. Sources: the owner's reviews of Midnight Call, Sunlight and
the "Be a Little Braver" V2 revision brief (`episodes/Urban_Lifestyle_Commercial/
Urban_Lifestyle_Commercial_V2_Revision_Brief_EN.md`, 2026-10-25). Apply both skills, then run
`scripts/brief.py check-plan` before any render.

## 1. Workflow order (structure before polish)
1. Story beats → shot list with a **reason for every cut** (new information, cause → effect).
2. **Geometry first**: for any place with a strict physical layout (vehicles, corridors, shops), make a
   still first (5-frame clip at ~1 MP, R2V with the character reference) and check it; then animate it
   with I2V. Never try to fix a wrong layout with camera movement.
3. Render picture shots **without narration and without music** (`non_diegetic_music: N/A`, no `<d>`
   unless a character speaks on screen). Narration, music and room beds are separate assets mixed in
   the edit (section 7).
4. Review: anatomy (eyes, hands, background people) frame by frame, then continuity, then sound.
   `scripts/take_checks.py` flags burned-in text, lens contact and lips moving in silent shots (warnings
   on the review page, calibrated on owner-reviewed takes); look at every flagged frame by eye.
   Across a cut, check the eyeline: the head must turn to the same side of the frame toward the same
   target (Vision head yaw, Sunlight v2: P3 -45, P4 -20, P5 -45 degrees). Trust the measurement over a
   glance at thumbnails. If one take faces the wrong way, `mirror: true` in cut.yaml flips it.
5. Only after structure is right: exposure/colour matching, then (never instead) sharpening/upscaling.
6. Length of an R2V `detailed_description`: 350-500 words (official guide; a single shot does not
   justify a shorter one; dialogue-dense shots may be shorter). check-plan warns below 350.

## 2. Eyes and attention (every shot with a face)
- Give each shot a **gaze plan**: target 1 → (motivated change) → target 2, with timing. Name real
  targets in the scene: "his eyes go to the two friends' faces, hold for a moment, then drop to the
  window reflection". Never write only "natural eyes".
- Include brief eye movements between targets, an occasional blink (not rhythmic), small head
  adjustments that lead or follow the eyes, convergence matching the distance of the target.
- Forbid camera contact unless asked: "he never looks into the lens".
- Faces must be large enough: medium close-up or closer for any performance beat (on 864x480 a
  chest-up face is ~120-180 px; wides show the person small, from behind or in profile).
- Ask for stability explicitly: "both eyes stay level and symmetrical, pupils aimed at the same target,
  facial proportions unchanged as the head turns".

## 3. Emotion beats
- Write emotion as a **sequence of small physical actions**, not an adjective: look → pause → gaze
  drops → mouth corners soften → small breath → returns to the window.
- Vary the endings: hesitation, polite nod, quiet recognition, physical relaxation, then (only at the
  moment of connection) a noticeable smile. Do not end every shot with a smile.
- Objects are handled for the character, not for the audience (lower the can naturally; never present
  it to the camera).

## 4. Background people
- Give 2-4 named background actions, **staggered and independent**: weight shifts with the vehicle,
  balance corrections at shoulder/elbow/wrist, thumb movements and eye shifts on phones, a pair who
  glance at each other and talk quietly in turns.
- "Nobody moves in sync; each person moves on their own timing."
- Defocused people still need stable silhouettes: "softly out of focus but with clear, stable heads,
  shoulders and arms".
- Quiet conversation = indistinct murmur in `overall_soundscape`, never `<d>` lines.
- **No small, distant figures crossing the frame, and no animals in the background** (owner, Sunlight F2,
  2026-10-25: a far-away dog walker and dog slid across the frame with legs barely moving). H3 animates
  small far figures badly: they glide. Give background life with people who stay in place (sitting,
  standing, talking, reading) and move only a little; if someone must walk, make them large enough to see
  their steps, or keep them out of the shot.

## 5. Places and geometry (write the layout as facts)
- Subway car: "the camera looks along the length of the carriage; sliding passenger doors are set into
  the left and right side walls, between rows of windows and seats; the aisle, ceiling rails, hand
  straps and vertical poles run lengthwise; the end of the car has a separate narrow gangway door;
  through the side windows the tunnel lights streak from front to back".
- Keep the same layout words in every shot of the location (wide and close-up).
- **Location pictures as references work in the official format** (`_multiref`, 2026-10-26): one character
  plus one location plate, the plate defined as its own subject ("<Subject 2> is the park environment in
  <Picture 2>: …" listing its landmarks), the camera position and a medium close-up written out, and the
  place described as "softly out of focus but recognisable" behind the face. Results: the room or park
  is kept, faces are frontal at 165-231 px (old free-text L1: 47 px side view; L2: seen from behind).
  Two character references in one shot remain untested in this format: keep to one.

## 6. Continuity of objects and order of actions
- Track object states across shots in the shot list notes (laptop open/closed, cup position, phone in
  hand/pocket, backpack on/off, can unopened/opened, overshirt on/off).
- Order actions so states never go backwards (phone → close laptop → leave).
- The character description names the **whole outfit**: top, trousers/skirt (or a dress), and shoes when
  a shot shows the feet. Whatever it leaves out, H3 invents per shot and it drifts (Sunlight P5 trousers).
  check-plan warns when a shot shows the lower body or feet and the description lacks them.
- Product: one approved reference picture per product shot; small print that must be exact (capacity,
  slogans) is added by compositing, not trusted to the model.

## 7. Sound is built in the edit
- Picture renders carry only their own sync sound (footsteps, door, can, phone taps, room tone).
- **Narration**: one narrator asset rendered separately (audio-only H3 render, all lines in as few
  clips as possible; later clips use the first clip as `<Audio 1>` voice-timbre reference), cut into
  lines and placed on the timeline. On picture: "his lips stay closed; he does not speak".
- **Music**: one continuous track (chained 15 s segments, each anchored on the end of the previous one),
  never per-shot music. Cuts between locations land on musical phrases.
- **Beds**: one room/ambience bed per location, running under all its shots; start the next location's
  bed 0.5-1 s before the cut, fade the old one out (no hard sound drop at a cut).
- Single, restrained effects on matching actions (door chime when the door opens, one notification).

## 8. Screens and text
- Phone/computer screens with content: render the screen as a **flat chroma-key green** that stays
  green for the whole shot (fingers may cover it), then composite a clean graphic
  (`scripts/screen_insert.py`). Never ask H3 for interface text or avatars.
- Screens without story content face away from the camera.
- On-screen text that H3 must draw (packaging) stays in double quotes and short; everything else: "no
  text anywhere in the frame".

## 9. Render limits on this Mac (64 GB, see docs/decisions.md)
- 864x480 (0.4 MP) up to 107 frames (4.46 s); 608x352 up to 124 frames. H3's trained length is
  124-362 frames: shots shorter than ~3 s are outside it - prefer 90-107 frames for performance shots.
- Audio-only assets: tiny picture (e.g. 320x192), up to 15 s (362 frames), only the soundtrack is used.
- Higher resolution comes after picks, not from rendering bigger: SeedVR2 7B sharp x2 (`upscale: 7b_sharp`
  in cut.yaml, `scripts/upscale.py --cut`), ~10 min per 4 s shot, D18.
