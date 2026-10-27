# Current project status

The only source for the project's current state (`AGENTS.md` §9). Older stage reports and README's
"Stage status" table are history. Update this file whenever the state changes; write facts with dates and
commits.

**Last updated:** 2026-10-26 · **main:** `4ca5016` · **Working branch:** `worktree-phase1-agent-governance`
(based on `4ca5016`; Phase 1 local commit approved; merge into main pending owner approval)

## Phases

| Phase | Status | What |
|---|---|---|
| Stages 0-8+ | ✅ done 2026-10-23 … 2026-10-26 (history: README, `docs/stage*`, `docs/*-results.md`) | local H3 pipeline: episodes, takes, checks, review page, assembly, Qwen-Image stills, SeedVR2 upscaling |
| Phase 0 — stable baseline | ✅ done 2026-10-26, merged to main as `4ca5016` | brief face validation no longer crashes on bad or failed Vision helper output (`scripts/brief.py`, `scripts/face_check.py` + tests); `scripts/check.sh` as the single standard gate; optional real-Vision check `scripts/test_vision_integration.py` |
| Phase 1 — multi-agent governance | ⏳ implementation complete 2026-10-26; independent audit PASS, no blocker or major findings; minor findings accepted by the owner as known limitations, no permissions widened (`docs/tasks/2026-10-26-phase1-agent-governance.md`); local commit approved 2026-10-26; merge into main pending owner approval | `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.claude/rules/`, `.claude/agents/`, this file, `docs/tasks/TEMPLATE.md`. No code, episode, prompt or workflow changes; no renders |

## Test baseline (`./scripts/check.sh`)
Measured 2026-10-26 on `4ca5016` (in the Phase 1 worktree): **17 passed, 4 skipped, 0 failed**.

- Passed: 5 offline test files (`test_episode`, `test_brief`, `test_assemble`, `test_autopick`,
  `test_take_checks`) and `episode.py validate` for 12 episodes.
- Skipped, by design:
  - `validate Urban_Lifestyle_Commercial` — `inputs/Urban_Lifestyle_Commercial/ref_can_v1.png` is local-only
    (product imitating a real beer trademark, until the licensing review).
  - `validate _owner_selfie` — `inputs/_owner_selfie/ref_girl_v1.png` is local-only (third-party reference
    picture, owner decision 2026-10-24).
  - `validate nailong` — `inputs/nailong/nailong_ref_v1.png` is local-only (third-party character /
    trademark reference, owner decision 2026-10-24).
  - `vision integration` — optional, not enabled (`RUN_VISION_INTEGRATION=1`).
- In the main checkout, where the local-only pictures exist, those three episodes may validate instead of
  skipping; that is also correct.
- Warnings that are not failures: `Urban_Lifestyle_Commercial_refs` shots R1-R4 (768x1376x5) are larger
  than anything tested — watch swap if they are ever rendered.

## Rendering limits (this Mac, M5 Max 64 GB)
- One ComfyUI (`localhost:8188`, `scripts/launch_comfyui.sh`) and one render at a time; renders only from
  the main checkout with the render lock (`AGENTS.md` §4, `.claude/agents/render-operator.md`).
- H3: 864x480 (0.4 MP) up to 107 frames, 608x352 up to 124 frames; ~14-15 min per 480x864 take with
  PyTorch attention (recipe `h3_base_v2`, D16). Swap > 20 GiB stops a render. fl2va and ref2va are never
  resident together (D14).
- Qwen-Image 2.1 edits need ComfyUI started with `--bf16-text-enc` and `resolution 0` (D17).
- SeedVR2 7B sharp x2 upscale ~10 min per 4 s shot, after picks only (D18).

## Licensing limits
- **Qwen-Image 2.1 output is non-commercial** (research/evaluation licence, D17).
- MiniMax H3 weights: community licence, not yet reviewed for commercial use.
- SeedVR2: Apache 2.0 (D18).
- `h3-prompt-writing` skill: no licence in its source repo; local install only, never in Git.
- Third-party / trademark reference pictures: local-only.
- No monetisation, client delivery or new public release before the licensing review (owner gate).

## Known open items (not approved; listed only)
- Licensing review (H3 licence, skills repo, Qwen output, SDXL, third-party references).
- Local "studio" web app (owner request; needs its own plan).
- Running the project on a Windows/RTX machine (estimate given; not started).
- Governance follow-ups noted in Phase 1: sessions in a worktree under `.claude/worktrees/` also load the
  main checkout's `CLAUDE.md` once it exists there; whether `.gitignore` should list `.claude/worktrees/`
  (today only the main checkout's `.git/info/exclude` ignores it).
