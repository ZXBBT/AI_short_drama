# Third-party material

## MiniMax H3 skills (github.com/MiniMax-AI/MiniMax-H3, `skills/`, commit d21241f, reviewed 2026-10-24)

Owner asked to load these skills into the project. All 9 were read before anything was installed.

| Skill | Runs locally? | Decision |
|---|---|---|
| **h3-prompt-writing** | yes ("no external API calls, MiniMax Hub tools, or proprietary runtime required") | **installed** as a Claude Code project skill |
| 3d-animation-short-generator, brand-promo-video-generator, co-op-game-intro-generator, handdrawn-live-video-generator, minimalist-product-ad-generator, music-video-subtitle-generator, paper-collage-explainer-generator, papercraft-stop-motion-explainer | no: each says it requires the "MiniMax Hub agent" (cloud canvas, `hub_*` tools) and is "not portable"; several route work to paid services (Seedance, ElevenLabs) | **not installed** (conflicts with local-only, no-paid-services rules); readable for ideas in `~/AI_renders/_downloads/minimax_h3_skills_d21241f/` |

**Licence:** the repository has no licence file (GitHub: "no license"); its README places the *model*
under the MiniMax H3 Community License. Without a licence the text is all-rights-reserved by default,
so the skill files are **not committed**: `.gitignore` excludes `.claude/skills/h3-prompt-writing/`
and `scripts/fetch_h3_skills.sh` reinstalls the exact files (pinned commit + SHA-256 per file).
Part of the licensing review before any public or commercial use.

**Install / reinstall:** `scripts/fetch_h3_skills.sh` (Claude Code picks the skill up in new sessions).

### What the skill teaches (and how the pipeline uses it)
- H3 prompts have an official structure. T2V/I2V/FLF2V: `integrated_multimodal_description`,
  `overall_soundscape`, `non_diegetic_music`; I2V and FLF2V start with a fixed first-frame / alignment
  line. R2V (Ref2VA): `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`
  (350-500 words for generation), `overall_soundscape`, `non_diegetic_music`.
- Shots: `[Shot 1]` without a time, later shots `[Shot N] At MM:SS.mmm, the camera cuts to ...`.
- Camera vocabulary: motion type + amplitude + speed ("pushes in with small amplitude at slow speed").
- Speakers `(S1)`, dialogue `<d>[English] ...</d>`; **text in double quotes means visible on-screen
  text** — the cause of the burned-in "Over here!" caption in Sunlight P4.
- Multiple references are expressed as `<Subject N>` (people, places, props), e.g. a person and a
  location in one shot; our "two references pull the camera back" finding (S005, L1) used free-form
  prompts and should be re-tested in this format.
- `brief.py check-plan` warns when a prompt is not in this format, when dialogue is quoted instead of
  in `<d>`, when an I2V/FLF2V prompt lacks its first line, and when a cut time is after the clip ends.
