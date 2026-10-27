# AGENTS.md — rules for every agent working in this repo

These rules apply to every coding agent and tool (Claude Code main session, its subagents, any other
assistant). Claude Code loads this file through `CLAUDE.md`. Current project state lives only in
`docs/status/current.md`; this file holds rules, not status.

## 1. The project in one paragraph
A reproducible, local-only short-drama and commercial pipeline: MiniMax H3 (video + sound), Qwen-Image 2.1
(stills) and SeedVR2 (upscaling) in a pinned ComfyUI, on Apple Silicon through **PyTorch MPS, not MLX**
(D1). Everything renders on this Mac. **No paid cloud generation services**: no Comfy Cloud, no "partner"
or `api_*` nodes/templates (D11), no remote APIs that generate pictures, video or sound. Story and creative
decisions stay with the owner; agents prepare, check and execute.

## 2. Quality gate
- `./scripts/check.sh` is the **only** formal quality gate: offline unit tests plus `episode.py validate`
  for every episode. No ComfyUI, no rendering, no network.
- Run it **before** you change anything (to know the baseline) and **after** every change. Report its
  summary line verbatim. The expected baseline is recorded in `docs/status/current.md`.
- A SKIP is acceptable only for the reasons the script itself lists (local-only reference pictures that are
  gitignored by owner decision; the optional Vision check). Any FAIL blocks the task.
- `RUN_VISION_INTEGRATION=1 ./scripts/check.sh` adds the real macOS Vision check; optional, not the gate.

## 3. Non-negotiables
1. Never modify `workflows/official/` (unmodified reference copies of official templates).
2. Never commit model weights, generated media (video, audio, renders, Qwen pictures), secrets/tokens, or
   local-only private material (see §6). `.gitignore` encodes most of this; do not weaken it.
3. Every bug fix includes a regression test that fails without the fix.
4. Never delete, skip, loosen or stub out a test (or a check in `scripts/check.sh`) to make it pass.
5. Stay inside the task's allowed paths. No refactoring, renaming or "while I'm here" fixes outside the task;
   report out-of-scope problems instead of fixing them.
6. Never start ComfyUI or a render concurrently with another one (§4).
7. A decision that changes architecture or generation parameters (models, recipes, sizes, attention mode,
   sampler settings, launch flags, pipeline structure) gets a new numbered entry in `docs/decisions.md`
   (what, why, what would make us revisit it), approved by the owner.
8. Follow the official H3 prompt format and the project direction skill for anything that becomes a prompt.

## 4. Shared exclusive resources
These are shared by all sessions, worktrees and the owner's own ComfyUI UI. Only one user at a time.

| Resource | What it is |
|---|---|
| `~/dev/ComfyUI` | pinned ComfyUI checkout and its venv (also the Python used by `check.sh`) |
| `~/AI_models/comfyui` | model weights (read-only for agents) |
| `~/AI_renders/comfyui` | takes, finals, upscales, Qwen pictures |
| `localhost:8188` | the one ComfyUI server (`scripts/launch_comfyui.sh`) |
| Apple MPS/GPU + 64 GB unified memory | one render at a time; fl2va and ref2va models never resident together (D14); swap > 20 GiB stops a render |

- Read-only use (running `check.sh`, reading manifests) is always fine. Starting ComfyUI, rendering,
  upscaling, assembling into `~/AI_renders`, or writing into `~/AI_models` needs an approved render task
  and the render procedure in `.claude/agents/render-operator.md`: main checkout only, a fresh
  Manual/default session, and the render lock `~/AI_renders/comfyui/.render-lock`.
- Existing safeguards stay on: `episode.py render` refuses while ComfyUI is busy; renders stop above the swap
  limit; models are unloaded when switching model families.

## 5. Licensing
- **Qwen-Image 2.1 output is non-commercial** (research/evaluation licence, D17): tag such pictures, and
  replace or license them before any monetised use.
- MiniMax H3 weights: H3 community licence, not yet reviewed for commercial use.
- `h3-prompt-writing` skill: no licence in its source repo → never committed; installed locally by
  `scripts/fetch_h3_skills.sh` (`docs/third_party.md`).
- Third-party / trademark reference pictures stay local-only (§6).
- Licence confirmation for any asset or model is a human decision. Agents report licence facts with
  sources; they never declare something cleared.

## 6. Local-only material and worktree bootstrap
- Gitignored, local-only by owner decision: `inputs/_owner_selfie/`, `inputs/nailong/`,
  `inputs/Urban_Lifestyle_Commercial/ref_can_*.png`, `.claude/skills/h3-prompt-writing/`.
- A fresh git worktree does **not** contain them. Expected consequences:
  - `check.sh` SKIPs the three episodes whose references are missing — this is correct; do not copy the
    files in, do not change the tests or the skip list.
  - The `h3-prompt-writing` skill is absent. Agents that need it must say so and degrade safely (see
    `.claude/agents/episode-director.md`). Installing it needs network access and owner approval.
- Never copy local-only files into a worktree for convenience, and never commit them anywhere.
- Python: use the ComfyUI venv (`~/dev/ComfyUI/.venv/bin/python`); do not create other environments or
  install packages without approval.

## 7. Human approval points
The owner must approve (or do) each of these; an agent stops and asks:
- a task card before work starts (status `approved`);
- any ComfyUI start, render, upscale or assembly into `~/AI_renders`;
- any download, network install or model fetch;
- choosing or confirming final takes (`episode.py select`, the review page's confirm, `selections.yaml`);
- licence confirmation for any asset or model, and any publication (push, GitHub Release, PR, sharing);
- commits and pushes;
- any change to `scripts/check.sh`, to what a test asserts, or to the governance files
  (`AGENTS.md`, `CLAUDE.md`, `.claude/**`);
- new or changed entries in `docs/decisions.md`;
- deleting any tracked file or any file outside the repo.

## 8. Task workflow
1. **Card.** Every non-trivial task has a card `docs/tasks/<YYYY-MM-DD>-<slug>.md` made from
   `docs/tasks/TEMPLATE.md`: goal, allowed and forbidden paths, acceptance criteria, verification commands,
   risks, approval points. The owner approves it.
2. **Analyse (optional).** Large or structural work: a read-only architecture pass first; findings go into
   the card; the owner confirms the order.
3. **Implement.** One writing agent per worktree at a time. Parallel work only in separate worktrees with
   non-overlapping paths. Run the gate before and after; fill in the card's handoff record. Do not commit.
4. **Audit.** An independent, read-only audit judges the change from the repo, the diff, the gate result
   and the card's acceptance criteria — not from the implementer's explanation. Its report is pasted into
   the card unchanged.
5. **Decide.** Blocker/major findings send the card back to step 3 (the implementer fixes; the auditor never
   does). Otherwise the owner decides whether to commit.
6. **Render** (if any) is its own approved card, executed by the render procedure (§4). The owner picks and
   confirms takes.

## 9. Sources of truth
- `docs/status/current.md` — the **only** source for the current state (phase, test baseline, open limits).
- `docs/decisions.md` — why things are the way they are (D-numbered, append-only; supersede, don't rewrite).
- History only, never current state: README's "Stage status" table, `docs/stage*`, `docs/*-results.md`,
  `docs/automation-plan.md`, `docs/practice-*.md`.
- Episode format: `episodes/README.md`, `docs/stage8-brief-format.md`. Third-party material:
  `docs/third_party.md`.

## 10. Git
Agents do not commit, push, rebase, reset, stash or merge on their own. The main session does these only
when the owner asks, and never discards uncommitted work.
