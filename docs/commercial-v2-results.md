# "Be a Little Braver" commercial: V1 and V2 (2026-10-24/25)

Owner's specs: `episodes/Urban_Lifestyle_Commercial/Urban_Lifestyle_Commercial_Recreation_Guide_EN.md` (V1)
and `..._V2_Revision_Brief_EN.md` (V2). Practice only: the product imitates a real beer brand's "SUPER DRY"
trademark (its reference picture is kept out of Git) and H3 drew an Apple logo on laptops - licensing
review (to-do #14) before any public or commercial use.

## V1 (cut.yaml, 59 s, 16:9)
References made with H3 itself (episodes/Urban_Lifestyle_Commercial_refs R1 man, R2 can - only the s22 can
spelled every label line correctly). 19 shots at 864x480, 2.3-3.75 s, narration and music inside every shot.
Owner's review (V2 brief): wrong subway geometry, frozen passengers, neutral face on the key line, eye drift,
soft faces, abrupt picture/sound transitions, music restarting every clip, unreadable phone screen, a
pointless store return, laptop state going backwards.

## V2 (cut_v2.yaml, 64 s)
| Problem | Fix |
|---|---|
| prompts lacked direction | project skill `.claude/skills/h3-short-drama-direction` + `brief.py` direction checks (screen text, narration/music in picture renders when `sound: edit`, very short clips) |
| subway geometry | layout stills first (refs R3/R4, 1376x768), checked, then I2V (S1A2, S1B2) |
| performance, eyes | every shot has a gaze plan and an action sequence; takes with camera contact replaced (S2B2) |
| continuity | phone -> close laptop -> leave; one white mug (S2A2 re-rendered); S2E walk to the store + match cut on the door |
| phone screen | flat green screen (S5B2) + `scripts/screen_insert.py` (drawn UI, tracked, thumb in front) |
| one narrator | audio-only H3 clips; N2b continues N1's own recording via `audio_anchor` (start correlates 0.96 with N1's end) |
| one music track | M1-M5, each anchored on the previous piece's last 4 s (joins correlate 0.83-0.94); M5 resolves on a final chord |
| sound jumps at cuts | `assemble.py` layers: ambience bed per location with lead-in/fade-out, music ducked 7 dB under the voice, V1 takes muted |

New code: `episode.py` audio inputs (`audio_refs`, `audio_anchor`, audio assets), `assemble.py` layered
soundtrack (`layers`, `duck`, `audio: off`, `video_file`, `target_lufs`, `sync_target_lufs`, +12 dB boost cap),
`scripts/audio_clip.py`, `scripts/screen_insert.py`. Audio-only renders use a 320x192 picture (thrown away).

Findings: H3's trained clip length is 124-362 frames (ComfyUI node tooltip) - most of our clips are shorter;
`<Audio 1>` voice reference alone gave a noticeably darker voice than continuation; a near-silent H3 bed boosted
+35 dB became loud hiss (hence the cap); without a limiter V2 is -18.4 LUFS (one peak hits -1 dBTP).

Open: owner's ear check of the narrator; V1 store/river shots reused without a frame-by-frame eye check;
small readable shop-sign text in S2E; optional limiter to reach -14 LUFS.
