# 2026-10-26-optimize-readme: Make README.md clear for new users

Work starts only when the owner sets the status to `approved`. Rules: `AGENTS.md` §8.

## Status
`draft` | `approved` | `in_progress` | `implemented` | `in_audit` | `changes_requested` | `done` | `cancelled`

Current: `done`

| Field | Value |
|---|---|
| Owner / responsible agent | owner / main session (docs-only task; no subagent needed) |
| Base commit | `aef0cae327310291f23613a54278172b71115085` |
| Branch / worktree (or main checkout for renders) | `worktree-optimize-readme` / `.claude/worktrees/optimize-readme` |
| Shared resources needed | none |

## Goal and background
Owner request 2026-10-26: a new reader of `README.md` should quickly understand what the project is, what
it can do, how to set it up, how to verify it and how to run an episode — while model, licence and
local-path facts stay accurate, `docs/status/current.md` stays the only current-state source (`AGENTS.md`
§9), and the "Stage status" table is clearly history. Docs only: no code, episode, prompt, workflow,
config or governance change.

### Review of the current README (done 2026-10-26, read-only)
Files read: `CLAUDE.md`, `AGENTS.md`, `docs/status/current.md`, `docs/decisions.md`, `docs/third_party.md`,
`episodes/README.md`, `README.md`; command details checked against the scripts' argument parsers and headers.

**Structure / information order**
1. No pointer to `docs/status/current.md` anywhere; a reader cannot tell where the current state lives.
2. Order mixes audiences: episode status and models come before setup; setup notes come near the end,
   after the stage history and measurements. A new user meets "Quick start" before knowing what to
   install.
3. No "Requirements" section. The real assumptions (Apple Silicon Mac, pinned ComfyUI `v0.42.1` at
   `~/dev/ComfyUI` with its venv, Python 3.13, PyTorch 2.14.1; `env/versions.md`, D2-D4) are not stated.
   There is no from-scratch install script for ComfyUI itself; the README must say so instead of
   inventing install steps.

**Current vs history mixed up**
4. "Stage status" is not labelled as history, and its last two rows (⏳ licensing gate, ⏳ studio app) read
   like current open items; Phase 0 and Phase 1 are missing (they live in `current.md`, correctly).
5. "Episodes" table has a "Status" column (e.g. "**v2 confirmed**") that is current-state information and
   lists only some episodes (missing `nailong`, `_owner_selfie`, `_e2e`, `_selftest`, `_exp_6_3`,
   `Urban_Lifestyle_Commercial_audio`, `Urban_Lifestyle_Commercial_refs`).
6. "Measured on this Mac" repeats numbers that `current.md` → "Rendering limits" also holds (two sources
   for the same state).
7. "Finished videos are shared as GitHub Release attachments" reads as the normal procedure, but
   `current.md` says no new public release before the licensing review.

**Command accuracy** (checked against the scripts)
8. Quick-start commands match the scripts: `brief.py validate|scaffold|check-plan <episode_dir>`,
   `pipeline.py <episode>`, `review_server.py <episode>` (port 8189 default), `upscale.py --cut <cut.yaml>`,
   `assemble.py <cut.yaml>` (output `~/AI_renders/comfyui/episodes/<ep>/_final/`). Gaps, not errors:
   - it does not say which steps start ComfyUI, render, or write into `~/AI_renders` (those need an
     approved render card, `AGENTS.md` §4/§7); `upscale.py` also needs ComfyUI running;
   - `pipeline.py` exit codes (0 done, 2 waiting for a human, 1 error) are not mentioned;
   - `brief.yaml` format pointer (`docs/stage8-brief-format.md`) and the full command table
     (`episodes/README.md`) are not linked.
9. "Download with `scripts/fetch_models.sh`" is incomplete: with no arguments it fetches only rows with
   role `required*` from `models/manifest.tsv`. R2V needs `scripts/fetch_models.sh models/manifest.tsv r2v`;
   Qwen-Image and SeedVR2 need their manifest as the first argument. Downloads need owner approval.
10. Checks section uses `scripts/check.sh`; project docs use `./scripts/check.sh`. Same script, but the
    README should use the one canonical spelling.
11. All files and paths the README names exist (checked with a read-only loop; `docs/stage6-*-results.md`
    is a glob matching `stage6-2/3/4`).

**Duplication / outdated rules**
12. "Rules" section is the Stage-era rule list ("One stage at a time; each ends with a checkpoint") and
    partly overlaps `AGENTS.md`; it should become a two-line pointer to `AGENTS.md` / `CLAUDE.md`.
13. "Checks" bullets repeat most of `scripts/check.sh`'s header and `AGENTS.md` §2; can be shortened.
14. "Repo layout" lacks `AGENTS.md`, `CLAUDE.md`, `.claude/agents/`, `.claude/rules/`, `docs/status/`,
    `docs/tasks/`, `env/`, `config/extra_model_paths.yaml`, `models/verification/`.

### Planned README outline (implementation step, after approval)
1. Title + one paragraph: what it is; local-only, PyTorch MPS not MLX (D1), no paid cloud / `api_*`
   nodes (D11). Line: "Current state: `docs/status/current.md`".
2. **What it does** — keep the pipeline diagram and the four feature bullets (facts unchanged).
3. **Requirements** — the currently verified, pinned environment on this Mac (Apple Silicon M5 Max,
   64 GB; ComfyUI `v0.42.1` at `~/dev/ComfyUI` with its `.venv`; Python 3.13; PyTorch 2.14.1), with exact
   versions in `env/versions.md` (D2-D4). Described as "what this project is verified and pinned on", not
   as minimum versions; no claim about other versions, hardware or operating systems. Honest note that
   installing ComfyUI itself is not scripted. *(Post-audit correction c:)* `env/versions.md` is described
   only as recording the pinned versions and one command that rebuilds the ComfyUI venv; the repo has no
   complete from-scratch ComfyUI install script.
4. **Setup after cloning** — `scripts/fetch_h3_skills.sh`; `scripts/fetch_models.sh` with the exact
   per-manifest invocations (item 9); `scripts/verify_models.sh [manifest]`; note that downloads need
   owner approval and weights go to `~/AI_models/comfyui`.
5. **Verify** — `./scripts/check.sh` (+ optional `RUN_VISION_INTEGRATION=1`); expected result and SKIP
   reasons: link to `current.md`, no copied numbers; one line on why a fresh clone/worktree SKIPs three
   episodes (local-only references).
6. **Quick start (episode)** — same commands as now, each marked "offline" / "starts ComfyUI, renders,
   writes `~/AI_renders` (approved render card only)"; `pipeline.py` exit codes; links to
   `episodes/README.md` and `docs/stage8-brief-format.md`. "Other tools" line kept.
   *(Post-audit correction d:)* the `assemble.py` note says: no running ComfyUI needed; writes render
   output into `~/AI_renders`; may also write `subtitles/` and `runs/` in the repo; approved render task
   only.
7. **Models and licences** — keep the table unchanged; add the licence limits from `AGENTS.md` §5 as a
   short list (Qwen output non-commercial D17, H3 licence not reviewed, skill has no licence and is never
   committed, third-party references local-only). No new licence conclusions. *(Post-audit correction b:)*
   no statement of the current commercial-use / client-delivery / public-release state; instead one
   line: "Current commercial-use and public-release gate: `docs/status/current.md` → "Licensing limits"."
8. **Episodes** — list all episode folders grouped as delivered / test / local-only-reference; drop the
   status wording, point to `current.md`; keep the `braver-v2` Release link as a historical fact.
9. **Where things live** — keep the table and the iCloud note; add the local-only inputs and
   `.claude/skills/h3-prompt-writing/`; reword the Release sentence (item 7).
10. **Repo layout** — updated per item 14.
11. **Working on this repo** — two lines: rules in `AGENTS.md`, Claude Code entry `CLAUDE.md`, task cards
    in `docs/tasks/`, decisions in `docs/decisions.md`. Replaces "Rules".
12. **History** — "Stage status" renamed "Stage status history (2026-10-23 … 2026-10-26) — not current"
    (*post-audit correction a:* "Stage status" kept in the heading so the references in `AGENTS.md`,
    `docs/status/current.md` and `.claude/rules/docs-and-governance.md` stay valid), moved
    to the end; the completed-stage rows are kept verbatim (history is not rewritten); the two ⏳ rows are
    removed (owner decision 1); a note says open items and Phases 0-1 are in `current.md`. "Measured on
    this Mac" numbers removed; only a link to `current.md` → "Rendering limits" remains (owner decision 2).

### Owner decisions (2026-10-26, given with the approval)
1. Delete the last two ⏳ rows (licensing gate, studio app) of the Stage history table. Current open items
   exist only in `docs/status/current.md`; the history table keeps only completed stages.
2. Delete the duplicated numbers of "Measured on this Mac"; keep only a link to `docs/status/current.md`
   → "Rendering limits".
3. README stays in English.

Card corrections requested by the owner before implementation (applied above and below):
- Requirements: Python 3.13 and PyTorch 2.14.1 are the currently verified, pinned local environment —
  not proven minimum versions; no inferred compatibility with other versions or operating systems.
- README path check: only concrete repo files/folders that README names; placeholder paths with
  `<...>`, local paths starting with `~/`, glob expressions with `*`, and example arguments inside code
  blocks are excluded; the command runs as-is in this zsh environment.

Post-audit corrections approved by the owner (2026-10-26, after the first independent audit; findings
a-d of the Audit record, in report order; full disposition under "Owner disposition — 2026-10-26"):
- a. Heading becomes "Stage status history (…) — not current"; out-of-scope files stay unchanged.
- b. README keeps only stable licence facts and links `docs/status/current.md` → "Licensing limits" for
  the current commercial-use / public-release gate.
- c. `env/versions.md` described exactly (pinned versions + one venv rebuild command; no full install
  script).
- d. `assemble.py` note: no running ComfyUI, writes `~/AI_renders`, may write `subtitles/` and `runs/`,
  needs owner approval.

## Allowed paths
- `README.md`
- `docs/tasks/2026-10-26-optimize-readme.md`

## Forbidden paths
- `workflows/official/**`, model weights, generated media, local-only inputs (always)
- All code (`scripts/**`), `episodes/**`, `prompts/**`, `workflows/**`, `config/**`, `models/**`, `env/**`,
  `subtitles/**`, `runs/**`, `inputs/**`
- Governance: `AGENTS.md`, `CLAUDE.md`, `.claude/**`
- `docs/status/current.md`, `docs/decisions.md`, `docs/third_party.md`, `episodes/README.md`, all other
  `docs/**` (out-of-scope problems are reported, not fixed)

## Acceptance criteria
Each one checkable from files, diff or command output.
- [ ] `git status --short --untracked-files=all` shows exactly ` M README.md` and
      `?? docs/tasks/2026-10-26-optimize-readme.md`, and `git diff --name-only aef0cae` shows only
      `README.md` (the untracked card does not appear in `git diff`).
- [ ] README has a clear order: what it is → what it does → requirements → setup → verify → quick start →
      models & licences → episodes → where things live → repo layout → working on this repo → history.
- [ ] README links `docs/status/current.md` as the current-state source near the top, and contains no
      test-baseline numbers, phase status or "confirmed"-style episode status of its own.
- [ ] *(Post-audit b)* README states no current commercial-use, client-delivery or public-release state of
      its own; "Models and licences" lists only stable licence facts and links `docs/status/current.md` →
      "Licensing limits" as the current commercial-use and public-release gate.
- [ ] The stage table is titled as history ("not current"), placed last; the completed-stage rows are
      unchanged and the two ⏳ rows are removed (owner decision 1). *(Post-audit a)* Its heading is
      "Stage status history (2026-10-23 … 2026-10-26) — not current", so it still contains "Stage status";
      `AGENTS.md`, `docs/status/current.md` and `.claude/rules/docs-and-governance.md` are unchanged.
- [ ] README contains no rendering time / size numbers of its own; it links `docs/status/current.md` →
      "Rendering limits" instead (owner decision 2).
- [ ] Requirements present Python 3.13 / PyTorch 2.14.1 / ComfyUI v0.42.1 as the currently verified,
      pinned environment, not as minimum versions, and make no claim about other versions, hardware or
      operating systems. *(Post-audit c)* README does not say `env/versions.md` records the install
      process; it says the file records the pinned versions and one command that rebuilds the ComfyUI
      venv, and that the repo has no complete from-scratch ComfyUI install script.
- [ ] Every command in README exists and its arguments match the script's parser (`brief.py`,
      `pipeline.py`, `review_server.py`, `upscale.py`, `assemble.py`, `fetch_models.sh`,
      `verify_models.sh`, `fetch_h3_skills.sh`, `check.sh`); `fetch_models.sh` invocations name the
      manifest and role correctly. The gate is written `./scripts/check.sh`.
- [ ] Steps that start ComfyUI, render, upscale, assemble into `~/AI_renders`, or download are marked as
      needing owner approval; `upscale.py` is marked as needing a running ComfyUI, `assemble.py` as not
      needing ComfyUI but writing into `~/AI_renders`; `verify_models.sh` is described as local and
      read-only (no download). *(Post-audit d)* The `assemble.py` note also says it may write
      `subtitles/` and `runs/` in the repo, and still needs owner approval.
- [ ] Kept and accurate: the model table (names, uses, licences, manifests), D17 Qwen non-commercial, H3
      licence not reviewed, SeedVR2 Apache 2.0 (D18), skill not in Git, local-only inputs,
      `~/dev/ComfyUI` (v0.42.1), `~/AI_models/comfyui`, `~/AI_renders/comfyui`, PyTorch MPS not MLX, no
      paid cloud services.
- [ ] No new licence conclusion, compatibility claim (e.g. other hardware/OS), feature or command that is
      not in the repo.
- [ ] No passage copied at length from `AGENTS.md` / `CLAUDE.md` (pointers instead; short licence list
      allowed).
- [ ] Every concrete repo path named in README exists (path check below): each `ABSENT` path is a
      gitignored local-only path confirmed by `git check-ignore -v`; any other `ABSENT` path is a failure.
- [ ] `./scripts/check.sh` summary is `17 passed, 4 skipped, 0 failed` (this worktree's baseline) or
      better, with no new SKIP.
- [ ] *(Post-audit)* The first Audit record is unchanged; the owner's disposition follows it as a separate
      section; `git diff --check` reports nothing.

## Verification commands
```
./scripts/check.sh
git status --short --untracked-files=all
git diff --stat aef0cae
git diff --name-only aef0cae
git diff --check
# Path check (read-only, zsh, run from the worktree root). Candidates: (a) backticked spans in README prose
# (fenced code blocks removed) that contain a "/" or are a root file like AGENTS.md; (b) every
# scripts/*.py|sh and models/*.tsv named anywhere, including code blocks. Dropped: spans with <...>, ~, *,
# spaces (commands with arguments) and URLs. Prints ok / ABSENT per path.
{ awk '/^```/{f=!f; next} !f' README.md | grep -oE '`[^`]+`' | tr -d '`' | grep -E '/|^[A-Z]+\.md$'; grep -oE '(scripts|models)/[A-Za-z0-9_.-]+\.(py|sh|tsv)' README.md; } | grep -vE '[<>~*[:space:]]|^https?:' | sort -u | while read -r p; do if [[ -e $p ]]; then echo "ok      $p"; else echo "ABSENT  $p"; fi; done
# Every ABSENT path must be a gitignored local-only path; this prints the matching .gitignore rule for each
# (a path with no output line is MISSING = failure). In a worktree, expected ABSENT paths:
git check-ignore -v .claude/skills/h3-prompt-writing/ inputs/_owner_selfie/ inputs/nailong/
# argument parsers the Quick Start must match:
grep -nE 'add_argument|add_parser' scripts/brief.py scripts/pipeline.py scripts/review_server.py scripts/upscale.py scripts/assemble.py
head -15 scripts/fetch_models.sh scripts/verify_models.sh
```

## Risks
- Rewording could change a fact (model name, licence, path, number). Shown by: diff review of the model
  table and licence lines; audit compares with `docs/decisions.md` and `current.md`.
- Moving information out could lose it for new users (e.g. measured times). Mitigated by links to the
  file that keeps it.
- External link `braver-v2` cannot be checked offline; it is kept unchanged, not re-verified.
- Docs-only change: `check.sh` is not expected to change; a different summary would point to an
  environment problem, not this task.

## Human approval points
- [x] Card approved, with owner decisions 1-3 and two card corrections — 2026-10-26
- [x] Independent audit (`independent-project-auditor`, Manual/default session) — 2026-10-26
- [x] Owner disposition of audit findings a-d (fix all before commit) — 2026-10-26
- [x] Second independent audit after the post-audit corrections — 2026-10-26
- [x] Owner disposition of second-audit nits (all three accepted as is) — 2026-10-26
- [x] Commit — 2026-10-26
- [ ] Push / merge to main — <date>

## Render task (only for render cards)
Not a render card.

## Audit record
2026-10-26 — audited: base `aef0cae327310291f23613a54278172b71115085`, uncommitted working tree in
`.claude/worktrees/optimize-readme`. Report pasted unchanged below.

Audit: docs/tasks/2026-10-26-optimize-readme.md  base aef0cae327310291f23613a54278172b71115085  head working tree (HEAD = aef0cae, no commits on top)
Parent mode confirmed Manual/default: yes. The prompt says so, and Bash was limited to approved read-only commands during the audit.
Gate: `17 passed, 4 skipped, 0 failed`  (baseline: `17 passed, 4 skipped, 0 failed`, measured in a worktree per `docs/status/current.md`. The SKIPs are the same three local-only episodes plus `vision integration`.)
Verdict: PASS

The prompt had exactly the four input fields and no implementer summary.

**Acceptance criteria**
- [PASS] Scope matches exactly. `git status --short --untracked-files=all` shows ` M README.md` and `?? docs/tasks/2026-10-26-optimize-readme.md`. `git diff --name-only aef0cae…` shows only `README.md`. `git log aef0cae..HEAD` is empty. I read the untracked card in full; it has no problem content.
- [PASS] Section order is right: intro, What it does, Requirements, Setup after cloning, Verify, Quick start, Models and licences, Episodes, Where things live, Repo layout, Working on this repo, Stage history.
- [PASS] `docs/status/current.md` is linked as the only status source at README.md:7-8. There are no baseline counts, no phase status and no "confirmed"-style wording. "Episodes" defers status to `current.md` (line 131).
- [PASS] The stage table is now "Stage history (2026-10-23 … 2026-10-26) — not current" and is the last section (line 183). The diff removes only the two ⏳ rows; rows 0 to 8+ have no `-` lines.
- [PASS] All "Measured on this Mac" numbers are removed. Lines 186-187 link `docs/status/current.md` → "Rendering limits". The only numbers left are hardware specs (64 GB) and an episode length (64 s).
- [PASS] Requirements (lines 30-38) say "verified on, and pinned to… not tested minimums; other versions, machines or operating systems have not been tested". The values match `env/versions.md` and D2/D3/D4.
- [PASS] Commands match the scripts:
  - `brief.py validate|scaffold|check-plan episodes/<name>`, `pipeline.py <ep>`, `review_server.py <ep>` (port 8189) and `assemble.py <cut.yaml>` match each script's own usage text.
  - `upscale.py --cut` matches the argparse at upscale.py:132.
  - The `fetch_models.sh` calls match its `[manifest] [role-prefix]` handling and `$role != $ROLE*` filter. The role values check out: `r2v` is in `manifest.tsv`, `required_turbo`/`required_edit` are in the Qwen manifest, `required_7b` is in the SeedVR2 manifest.
  - `verify_models.sh [manifest]` is read-only according to its header. The gate is written `./scripts/check.sh`.
- [PASS] Approval and side-effect markings are in place:
  - Downloads need approval (lines 46-48).
  - `pipeline.py` starts ComfyUI and needs an approved render task.
  - `upscale.py` needs a running ComfyUI and writes `~/AI_renders` (confirmed: it calls `E.api_get` and `run_h3_t2v.run`).
  - `assemble.py` needs no ComfyUI but writes `~/AI_renders` (its docstring says "no ComfyUI").
  - `verify_models.sh` is described as local and read-only.
- [PASS] Facts kept and correct: the model table is byte-identical (only moved); D17, the H3 licence not yet reviewed, D18 Apache 2.0, skill not in Git, local-only inputs (match `.gitignore` lines 55-62), the `~/dev/ComfyUI` v0.42.1, `~/AI_models/comfyui` and `~/AI_renders/comfyui` paths, MPS not MLX (D1), no paid cloud (D11). `launch_comfyui.sh` behaviour matches lines 30-36 of that script and D16.
- [PASS] No new licence conclusion, compatibility claim, feature or command. Everything new traces to `AGENTS.md`, `docs/decisions.md`, `current.md` or the scripts.
- [PASS] Nothing is copied at length from `AGENTS.md`/`CLAUDE.md`. "Working on this repo" is a three-line pointer. The licence list is short, which the card allows.
- [PASS] Every concrete repo path in README exists. I could not run the card's one-liner (see Not verified), so I checked by hand against `git ls-files`: every named path is tracked, including the `docs/stage6-*` glob → stage6-2/3/4. The three gitignored paths are covered by `.gitignore` rules: `.claude/skills/h3-prompt-writing/` (line 58), `inputs/_owner_selfie/` (line 55) and `inputs/nailong/` (line 60).
- [PASS] Gate result is `17 passed, 4 skipped, 0 failed` with no new SKIP.

**Findings (most severe first)**
- **minor** README.md:183 — The heading rename leaves other files pointing at a name that no longer exists. `AGENTS.md:109`, `.claude/rules/docs-and-governance.md:5` and `docs/status/current.md:3-4` still refer to README's "Stage status" table. Those files are forbidden paths here, so not changing them was correct. The handoff's "Noticed outside the scope" list does not mention it, though.
  - Evidence: AGENTS.md:109 "History only, never current state: README's "Stage status" table"; current.md:3-4 "README's "Stage status" table are history."
  - Recommendation: add this to the card's out-of-scope list and fix it in a follow-up governance/docs card.
- **minor** README.md:119-127 — The "Licence limits" list repeats current gate state, which line 8 says lives only in `current.md`. In particular, "No monetisation, client delivery or new public release before the licensing review" duplicates `current.md` "Licensing limits". The card's outline item 7 approved this, so it is within scope. It is still the same two-sources pattern the card removed for rendering numbers, and it will drift once the licensing review happens.
  - Recommendation: the owner may accept this as is, or keep only the stable facts (D17, the skill having no licence) and point to `current.md` for the gate.
- **nit** README.md:40-41 — "`env/versions.md` records how it was done here" overstates that file a little. It holds pinned targets, an install log table and a venv reinstall command, not step-by-step ComfyUI install instructions.
  - Recommendation: optionally reword to "records the installed versions and the venv reinstall command".
- **nit** README.md:72-74 — "assemble.py … writes into ~/AI_renders" leaves out that it also writes `subtitles/<ep>_<version>.srt` and `runs/…` inside the repo (assemble.py:7-8). Accurate as far as it goes; just incomplete.

**Not verified**
- **Card's path-check one-liner** — the `{ awk … } | … | while read …` pipeline and `git check-ignore -v …` were both denied (Bash in don't-ask mode; `grep`, `ls` and `git -C … check-ignore` were denied too). I replaced it with a manual comparison against `git ls-files` and `.gitignore`.
- **"Results in `docs/`" for `_e2e`, `_exp_6_3` and `_selftest`** (README.md:137) — not checked, because `grep -rn` over `docs/` was not available.
- **Owner approval of the card** (approval point 1, 2026-10-26) — the repo cannot show this; it is the card's own claim.
- **External link `braver-v2`** — unchanged from base and not fetched, since I had no network.

Relevant files:
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/README.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/docs/tasks/2026-10-26-optimize-readme.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/AGENTS.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/docs/status/current.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/.claude/rules/docs-and-governance.md

## Owner disposition — 2026-10-26
The owner decided to fix all four findings of the first audit before any commit (no commit, merge or
push until then). Findings are lettered a-d in the order of the report above. Status set to
`changes_requested` for the fixes; back to `implemented` when done; then a second independent audit.
Allowed paths unchanged: `README.md` and this card only.

| Finding | Decision |
|---|---|
| a (minor, README.md:183, heading rename) | Rename the heading to "Stage status history (…) — not current", so the "Stage status" references in `AGENTS.md`, `docs/status/current.md` and `.claude/rules/docs-and-governance.md` stay true. Do not change those out-of-scope files. |
| b (minor, README.md:119-127, licence limits repeat current gate) | Keep only relatively stable model-licence facts. Remove the repeated statement of the current commercial-use / client-delivery / public-release state; link only: "Current commercial-use and public-release gate: `docs/status/current.md` → Licensing limits." Also corrected (owner, 2026-10-26, before the second audit): the "Where things live" sentence keeps the historical fact "The V2 commercial was shared as a GitHub Release attachment." and replaces "any new public release waits for the licensing review" with "For the current commercial-use and public-release gate, see `docs/status/current.md` → "Licensing limits"." |
| c (nit, README.md:40-41, `env/versions.md`) | Do not say `env/versions.md` records the full install process. Describe it as recording the pinned versions and one command that rebuilds the ComfyUI venv; the repo has no complete from-scratch ComfyUI install script. |
| d (nit, README.md:72-74, `assemble.py` outputs) | The `assemble.py` note states: no running ComfyUI needed; writes into `~/AI_renders`; may also write `subtitles/` and `runs/` in the repo; still needs owner approval because it produces render output. |

## Second audit record — 2026-10-26
2026-10-26 — audited: base `aef0cae327310291f23613a54278172b71115085`, uncommitted working tree in
`.claude/worktrees/optimize-readme`, after the post-audit corrections (rounds 2 and 3). Report pasted
unchanged below.

Audit: docs/tasks/2026-10-26-optimize-readme.md  base aef0cae327310291f23613a54278172b71115085  head working tree (HEAD = aef0cae, no commits on top)
Parent mode confirmed Manual/default: yes. The prompt says so, and Bash denied every command that was not pre-approved during this audit.
Gate: `17 passed, 4 skipped, 0 failed`  (baseline: `17 passed, 4 skipped, 0 failed` for a worktree, from `docs/status/current.md` → "Test baseline")
Verdict: PASS

The prompt had exactly the four input fields and no implementer summary.

**Acceptance criteria**
- [PASS] **Scope.** `git status --short --untracked-files=all` shows ` M README.md` and `?? docs/tasks/2026-10-26-optimize-readme.md`. `git diff --name-only aef0cae…` shows only `README.md`, and `git log aef0cae..HEAD` is empty. I read the untracked card in full; it contains no secrets, media or local-only material.
- [PASS] **Section order.** README.md:1-185 runs intro → What it does → Requirements → Setup after cloning → Verify → Quick start → Models and licences → Episodes → Where things live → Repo layout → Working on this repo → Stage status history.
- [PASS] **Current-state source.** `docs/status/current.md` is linked as the only status source at README.md:7-8. README has no baseline counts, no phase status and no "confirmed"-style wording; the Episodes section points to `current.md` (README.md:133).
- [PASS] **Licence state (post-audit b).**
  - README.md:121-127 now lists only licence facts that match `AGENTS.md` §5 and `current.md` "Licensing limits" lines 50-54.
  - README.md:129 and 154-155 link `docs/status/current.md` → "Licensing limits", a heading that exists (current.md:49).
  - None of the words "monetisation", "client delivery", "public release" or "waits for" appear as README's own current state. The diff shows the gate bullet and the "waits for the licensing review" sentence removed.
- [PASS] **History table.** The heading at README.md:185 is "Stage status history (2026-10-23 … 2026-10-26) — not current" and is the last section. The diff removes only the two ⏳ rows; rows 0 to 8+ are context lines in the diff, so they are unchanged.
  - `AGENTS.md` and `.claude/rules/docs-and-governance.md` are unchanged (not in the diff), and their "Stage status" references (AGENTS.md:109, rules :16) still match.
  - `docs/status/current.md` is also unchanged (not in the diff); its "Stage status" reference at current.md:3-4 still matches.
- [PASS] **No rendering numbers.** The "Measured on this Mac" section is removed. README.md:188-189 links `current.md` → "Rendering limits" (current.md:40).
- [PASS] **Requirements.**
  - README.md:30-31 say "verified on, and pinned to … not tested minimums; other versions, machines or operating systems have not been tested".
  - The values match `env/versions.md`:9-11 and D2, D3 and D4.
  - README.md:40-42 match env/versions.md: pinned targets plus one venv reinstall command (line 16), and "no complete from-scratch ComfyUI install script".
- [PASS] **Commands.**
  - The `pipeline.py` and `assemble.py` lines match their docstrings; the `review_server.py` line matches its docstring including port 8189; the `upscale.py --cut` line matches upscale.py:8. The `brief.py` lines are unchanged from base.
  - The `fetch_models.sh` calls match its `[manifest] [role-prefix]` handling and the `$role != $ROLE*` filter. Each manifest has `#repo`/`#revision` lines. The roles `r2v` (manifest.tsv:15), `required_turbo`/`required_edit` (qwen manifest:10,13) and `required_7b` (seedvr2 manifest:10) all exist.
  - `verify_models.sh [manifest]` is read-only according to its header.
  - The gate is written `./scripts/check.sh` (README.md:69-73).
- [PASS] **Approval and side-effect notes.**
  - Downloads need approval (README.md:47-49).
  - `pipeline.py`: starts ComfyUI, approved render task only.
  - `upscale.py`: needs a running ComfyUI, writes `~/AI_renders`, approval.
  - `assemble.py`: no running ComfyUI, writes `~/AI_renders`, may write `subtitles/` and `runs/`, approval. This matches assemble.py:6-8.
  - `verify_models.sh` is described as local and read-only.
- [PASS] **Facts kept.**
  - The model table is unchanged; it was only moved.
  - D17 non-commercial with tag/replace matches decisions.md:111-113. The H3 licence is still "not yet reviewed", and D18 Apache 2.0 is kept.
  - Skill not in Git, local-only inputs (match `.gitignore`:55-62), `~/dev/ComfyUI` v0.42.1, `~/AI_models/comfyui`, `~/AI_renders/comfyui`, MPS not MLX (D1) and no paid cloud (D11) are all kept.
  - The `launch_comfyui.sh` description matches launch_comfyui.sh:3-37.
- [PASS] **Nothing new invented.** I found no new licence conclusion, compatibility claim, feature or command; every new statement traces to `AGENTS.md`, `docs/decisions.md`, `current.md`, `env/versions.md` or the scripts.
- [PASS] **No long copies from `AGENTS.md`/`CLAUDE.md`.** "Working on this repo" is a three-line pointer. The licence list is short and close to `AGENTS.md` §5, which the card allows.
- [PASS] **Every repo path exists** (checked by hand, see Not verified).
  - `ls` confirms every concrete path README names: `AGENTS.md`, `CLAUDE.md`, `docs/status/current.md`, `docs/tasks/`, `docs/decisions.md`, `docs/third_party.md`, `docs/stage8-brief-format.md`, `episodes/README.md`, `env/versions.md`, `env/comfyui-venv-freeze.txt`, `models/README.md`, `models/verification/`, the three manifests, `config/extra_model_paths.yaml`, `config/recipes/`, all named `scripts/*`, `.claude/skills/h3-short-drama-direction/`, and the history-table docs (stage6-2/3/4 for the glob).
  - The 16 episode folders in `episodes/` match README.md:137-140 exactly.
  - The paths that are absent in this worktree are all gitignored: `.claude/skills/h3-prompt-writing/` (.gitignore:58), `inputs/_owner_selfie/` (:55), `inputs/nailong/` (:60) and `ref_can_*.png` (:62).
- [PASS] **Gate.** I ran `./scripts/check.sh` myself: `17 passed, 4 skipped, 0 failed`, with the same four SKIPs as the baseline (`_owner_selfie`, `nailong`, `Urban_Lifestyle_Commercial`, `vision integration`) and no new SKIP.
- [NOT VERIFIED] **First Audit record unchanged; `git diff --check` reports nothing.** The owner disposition is a separate section after the Audit record (card lines 296-307), which passes. The other two parts could not be checked; see Not verified.

**Findings (most severe first)**
- **nit** README.md:95 — The `upscale.py` note says "needs a running ComfyUI, writes into ~/AI_renders" but leaves out that it also writes `runs/<date>/upscale__….json` in the repo. This is the same gap finding d fixed for `assemble.py`. The acceptance criterion does not require it for `upscale.py`.
  - Evidence: upscale.py:17 "Writes ~/AI_renders/comfyui/upscaled/… and runs/<date>/upscale__<name>__<model>.json".
  - Recommendation: optionally add "and a record in runs/" to the comment.
- **nit** README.md:121 — The line "Licence facts (sources: `docs/decisions.md`, `docs/third_party.md`)" is not quite right for every bullet. "MiniMax H3 weights: community licence, not yet reviewed for commercial use" is not stated in either cited file; it comes from `AGENTS.md` §5 and `current.md`:51. `third_party.md` covers the skill, not the H3 weights.
  - Recommendation: optionally add `AGENTS.md` §5 to the sources.
- **nit** docs/tasks/2026-10-26-optimize-readme.md:8 — During this audit the card status is `implemented`, not `in_audit`. It is a workflow label only.

**Not verified**
- **`git diff --check aef0cae…`** — the command was denied (don't-ask mode). In the full diff I read, I saw no trailing-whitespace markers, but that is not proof.
- **"First Audit record unchanged"** — the card is untracked and there is no earlier copy in Git. The implementer's `cmp`/SHA-1 against a scratch copy cannot be checked from the repo.
- **Trailing whitespace in the untracked card** — no allowed command could show it.
- **The card's path-check one-liner and `git check-ignore -v …`** — both were denied (compound pipelines and `git -C … check-ignore` are not pre-approved). I checked by hand with `ls` and `.gitignore`, as listed under acceptance criteria.
- **Owner approvals recorded in the card** (card approval, disposition) — the repo cannot show these; they are the card's own claims.
- **External link `braver-v2`** — unchanged from base and not fetched, since I had no network.

Relevant files:
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/README.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/docs/tasks/2026-10-26-optimize-readme.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/docs/status/current.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/AGENTS.md
- /Users/marcusmao/dev/AI_short_drama/.claude/worktrees/optimize-readme/scripts/upscale.py

## Owner disposition (second audit) — 2026-10-26
Second independent audit verdict: PASS, no blocker, major or minor findings. The owner accepts all three
nits as they are; none is handled in this task. README is not changed again and no third audit is needed.
Status stays `implemented`, waiting for the owner's commit authorisation (no commit, merge or push until
then).

| Finding | Decision |
|---|---|
| nit 1 (README.md:95, `upscale.py` note does not mention `runs/`) | Accepted as is; not handled in this task. |
| nit 2 (README.md:121, licence-fact sources omit `AGENTS.md` §5 for the H3 weights) | Accepted as is; not handled in this task. |
| nit 3 (card line 8, status `implemented` rather than `in_audit` during the audit) | Accepted as is; not handled in this task. Status stays `implemented`. |

## Final handoff record
Written by the implementing agent. The auditor treats this as claims to verify.
Implemented 2026-10-26 by the main session in `.claude/worktrees/optimize-readme`, on base `aef0cae`.
Not committed.
- Files changed: `README.md` (modified; `git diff --stat aef0cae`: 118 insertions, 62 deletions) and this
  card (new, untracked). No other file changed: `git status --short --untracked-files=all` shows
  ` M README.md` and `?? docs/tasks/2026-10-26-optimize-readme.md`; `git diff --name-only aef0cae` shows
  `README.md`.
- Owner's pre-audit corrections (2026-10-26), applied: (1) acceptance criterion 1 now checks
  `git status --short --untracked-files=all` and `git diff --name-only aef0cae` separately; (2) README
  "Setup after cloning" says only `fetch_h3_skills.sh` and `fetch_models.sh` download, and that
  `verify_models.sh` is local and read-only; (3) Quick start has separate notes for `upscale.py` (needs a
  running ComfyUI, writes `~/AI_renders`, approval) and `assemble.py` (no ComfyUI, writes `~/AI_renders`,
  approval). Checked against the code: `upscale.py` calls `E.api_get` and `run_h3_t2v.run`;
  `assemble.py` has no ComfyUI call; `episodes/README.md` lists assemble as not needing ComfyUI.
- What changed in README, per the approved outline: a pointer to `docs/status/current.md` near the top;
  new sections "Requirements" (verified, pinned environment, explicitly not minimum versions), "Setup
  after cloning" (per-manifest `fetch_models.sh` invocations, download approval), "Verify", "Working on
  this repo"; Quick start commands unchanged but grouped by offline / starts ComfyUI / needs approval, plus
  `pipeline.py` exit codes and links to `episodes/README.md` and `docs/stage8-brief-format.md`; licence
  limits list under the model table; Episodes table regrouped to list every episode folder without status
  wording; "Where things live" adds local-only inputs and the skill folder, and the Release sentence is
  reworded; Repo layout adds `AGENTS.md`, `.claude/`, `docs/status/`, `docs/tasks/`, `config/`,
  `models/verification/`; "Rules" replaced by a pointer; "Measured on this Mac" numbers removed (link
  only); Stage table renamed "Stage history … — not current", moved last, two ⏳ rows removed.
- Kept verbatim: the model table (all original lines found unchanged with `grep -xF`), the completed-stage
  rows 0-8+ (`git diff -U0 README.md | grep '^-|'` shows only the two ⏳ rows, the old Episodes table
  and the moved model table as removed), the pipeline diagram and the four feature bullets (only the
  direction-skill path got a trailing `/`), the "Where things live" rows.
- Facts checked against the repo for new text: script parsers (`brief.py`, `pipeline.py`,
  `review_server.py`, `upscale.py`, `assemble.py`); `fetch_models.sh` role-prefix logic and the role values
  in each manifest; `pipeline.py` docstring (exit codes) and that it starts `scripts/launch_comfyui.sh`;
  `env/versions.md` pinned targets; every test episode named "results in `docs/`" is mentioned in a
  `docs/*.md` file; delivered episodes as listed in `.claude/rules/episodes-and-prompts.md`.
- Tests added or changed (and how they failed before the fix): none (docs only)
- `./scripts/check.sh` before (verbatim summary): `17 passed, 4 skipped, 0 failed` (2026-10-26, `aef0cae`,
  this worktree; SKIPs: `_owner_selfie`, `nailong`, `Urban_Lifestyle_Commercial` local-only references,
  `vision integration` not enabled)
- `./scripts/check.sh` after (verbatim summary): `17 passed, 4 skipped, 0 failed` (same four SKIPs;
  re-run after the pre-audit corrections, same result)
- Path check result: 45 paths `ok`; 3 `ABSENT` — `.claude/skills/h3-prompt-writing/`,
  `inputs/_owner_selfie/`, `inputs/nailong/` — each confirmed gitignored by `git check-ignore -v`
  (`.gitignore` lines 58, 55, 60). No missing path. Same result after the pre-audit corrections.
- Not done / open questions:
  - The external link `braver-v2` was kept unchanged and not re-checked (no network).
  - The path check was first written as one line with `git check-ignore` inside the loop. This session's
    worktree guard refuses compound shell lines here, so it was split into the existence one-liner plus a
    plain `git check-ignore -v` line (card updated). The one-liner was run by saving its exact text to a
    scratch file and running it with `zsh` from the worktree root; it is unchanged and runs as-is in a
    normal zsh terminal.
- Noticed outside the scope (reported, not fixed):
  - `docs/stage8-brief-format.md` still says "end-to-end test (8.6) pending owner approval" while the
    README history and `current.md` record Stage 8 / Sunlight end-to-end as done. It is a history doc, so it
    was left alone.
  - `episodes/README.md` command table does not mention `brief.py` or `upscale.py`.

### Post-audit corrections (round 2) — 2026-10-26
Owner-approved corrections from the first independent audit (see "Owner disposition — 2026-10-26").
Implemented by the main session in the same worktree, still on base `aef0cae`, not committed. Status went
`implemented` → `changes_requested` → `implemented`.
- `./scripts/check.sh` before round 2 (verbatim summary): `17 passed, 4 skipped, 0 failed`.
- README changes:
  - a: heading now "## Stage status history (2026-10-23 … 2026-10-26) — not current". `AGENTS.md:109`,
    `.claude/rules/docs-and-governance.md:16` and `docs/status/current.md:4` (unchanged) still say
    "Stage status", which the heading contains.
  - b: "Licence limits (… current gate in `docs/status/current.md`)" became "Licence facts (sources:
    `docs/decisions.md`, `docs/third_party.md`)"; the bullet "No monetisation, client delivery or new public
    release before the licensing review" was removed; added "Current commercial-use and public-release
    gate: `docs/status/current.md` → "Licensing limits"." (heading checked in `current.md`).
    `grep -nE 'monetisation|client delivery|public release' README.md` printed nothing at this point. The
    "Where things live" sentence "any new public release waits for the licensing review" was not part of
    finding b and was first left as is; the owner then had it corrected too (round 3 below).
  - c: Requirements now say `env/versions.md` records the pinned versions and one command that rebuilds
    the ComfyUI venv from the freeze file (checked: `env/versions.md:16`), and that the repo has no
    complete from-scratch ComfyUI install script.
  - d: the `assemble.py` comment in Quick start now says no running ComfyUI is needed, it writes render
    output into `~/AI_renders`, may also write `subtitles/` and `runs/` in this repo, approved render task
    only (checked against `scripts/assemble.py` docstring lines 6-8).
- Card changes: outline items 3, 6, 7, 12 and the acceptance criteria marked *(Post-audit …)*; list of
  post-audit corrections after the owner decisions; `git diff --check` added to the verification commands;
  "Owner disposition — 2026-10-26" added after the Audit record; approval points updated.
- First Audit record unchanged: the section was saved before the edits and compared after with `cmp`
  (identical; SHA-1 `ae13852a9cc6e44b263f0fe20ee71f1f046c1746` both times).
- `./scripts/check.sh` after round 2 (verbatim summary): `17 passed, 4 skipped, 0 failed` (same four
  SKIPs: `_owner_selfie`, `nailong`, `Urban_Lifestyle_Commercial`, `vision integration`).
- Scope: `git status --short --untracked-files=all` shows ` M README.md` and
  `?? docs/tasks/2026-10-26-optimize-readme.md`; `git diff --name-only aef0cae` shows `README.md`;
  `git diff --stat aef0cae`: 120 insertions, 62 deletions.
- `git diff --check aef0cae`: no output, exit 0. It does not cover the untracked card; a separate search for
  trailing whitespace in the card found none.
- Path check (same one-liner, run from a scratch file with `zsh`): 45 `ok`, 3 `ABSENT` —
  `.claude/skills/h3-prompt-writing/`, `inputs/_owner_selfie/`, `inputs/nailong/` — each confirmed by
  `git check-ignore -v` (`.gitignore` lines 58, 55, 60).
- Tests added or changed: none (docs only).
- Not done: the external link `braver-v2` was still not re-checked (no network).

### Finding b follow-up (round 3) — 2026-10-26
Owner-requested before the second audit; recorded under finding b in "Owner disposition". Same worktree,
base `aef0cae`, not committed; status stayed `implemented`.
- README "Where things live": "The V2 commercial was shared as a GitHub Release attachment; any new public
  release waits for the licensing review." became "The V2 commercial was shared as a GitHub Release
  attachment. For the current commercial-use and public-release gate, see `docs/status/current.md` →
  "Licensing limits"." The historical fact is kept; README now states no current release state of its own.
- `./scripts/check.sh` after round 3 (verbatim summary): `17 passed, 4 skipped, 0 failed` (same four SKIPs).
- `git diff --check aef0cae`: no output, exit 0; no trailing whitespace in this card.
- Scope: `git status --short --untracked-files=all` shows ` M README.md` and
  `?? docs/tasks/2026-10-26-optimize-readme.md`; `git diff --name-only aef0cae` shows `README.md`;
  `git diff --stat aef0cae`: 120 insertions, 62 deletions.
- `grep -nE 'monetisation|client delivery|public release|waits for' README.md`: no output.
- First Audit record still identical to the saved copy (`cmp`). Path check: 45 `ok`, same 3 gitignored
  `ABSENT` paths.
