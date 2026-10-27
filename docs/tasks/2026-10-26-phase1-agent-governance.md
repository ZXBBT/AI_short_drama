# PHASE1-GOV: Multi-agent governance layer (bootstrap)

**Bootstrap exception.** The owner approved the Phase 1 governance plan in the Claude Code session of
2026-10-26, before `docs/tasks/TEMPLATE.md` existed. This card was written afterwards, in the template's
format, so that Phase 1 can be audited like any other task. It records the approved scope; it does not
widen it.

## Status
`draft` | `approved` | `in_progress` | `implemented` | `in_audit` | `changes_requested` | `done` | `cancelled`

Current: `done`

| Field | Value |
|---|---|
| Owner / responsible agent | owner / main Claude Code session (no subagent; the agents did not exist yet) |
| Base commit | `4ca5016` (Phase 0, merged to main) |
| Branch / worktree | `worktree-phase1-agent-governance` (`.claude/worktrees/phase1-agent-governance`) |
| Shared resources needed | none |

## Goal and background
Let several specialised Claude Code agents work on this project safely, with:
1. one place for the project's global rules and the single quality gate;
2. each agent's responsibilities, permissions and prohibitions;
3. how tasks are assigned, verified and handed over;
4. an independent audit agent that does not inherit the implementing agent's context;
5. which operations must run one at a time or need human approval.

Governance, agent configuration and status documents only: no Python refactoring, no renders.
Agent frontmatter, settings and rules use only fields confirmed in the official Claude Code docs
(code.claude.com/docs/en/sub-agents, memory, permissions, permission-modes, settings) for the installed
version 2.1.311 (`omitClaudeMd` needs ≥ 2.1.271).

## Allowed paths
The 15 original governance files:
- `AGENTS.md`
- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/rules/scripts-and-tests.md`, `episodes-and-prompts.md`, `render-and-generation.md`,
  `workflows-models-assets.md`, `docs-and-governance.md`
- `.claude/agents/project-architect.md`, `episode-director.md`, `pipeline-engineer.md`, `render-operator.md`,
  `independent-project-auditor.md`
- `docs/status/current.md`
- `docs/tasks/TEMPLATE.md`

and this card: `docs/tasks/2026-10-26-phase1-agent-governance.md`.

The bootstrap follow-up (approved 2026-10-26) touched only `CLAUDE.md`,
`.claude/agents/independent-project-auditor.md` and this card.

## Forbidden paths
- Every existing Python file (`scripts/*.py`), every episode (`episodes/**`), prompt (`prompts/**`),
  workflow (`workflows/**`), `README.md` and `scripts/check.sh`.
- Everything else outside the allowed paths, including `.gitignore`, `docs/decisions.md`, `config/**`,
  `inputs/**`, model weights, generated media, local-only material.

## Acceptance criteria
- [ ] Only the allowed paths are added or modified; no tracked file is modified or deleted
      (`git status --short --untracked-files=all` lists exactly 16 untracked files and nothing else).
- [ ] No existing Python, episode, prompt, workflow, README or `scripts/check.sh` change.
- [ ] `AGENTS.md` holds the global rules: local-only, no paid cloud generation services; `workflows/official`
      untouched; no weights, generated media, secrets or local-only material in Git; bug fixes with
      regression tests; no deleting, skipping or weakening tests; `./scripts/check.sh` as the single formal
      gate, run after every change; no concurrent ComfyUI or renders; the shared resources
      `~/dev/ComfyUI`, `~/AI_models/comfyui`, `~/AI_renders/comfyui`, `localhost:8188`, Apple MPS/GPU;
      Qwen output non-commercial; final takes, licence confirmation and publication need the owner;
      no out-of-scope refactoring; decision entries for architecture or generation-parameter changes;
      `docs/status/current.md` as the only current-state source, stage docs as history.
- [ ] `CLAUDE.md` is short, imports `@AGENTS.md`, and gives the gate, agent roster, start modes, audit
      prompt, rules/skills/settings notes and a docs index without duplicating `AGENTS.md`.
- [ ] `.claude/settings.json` is valid JSON; `disableBypassPermissionsMode: "disable"`; no `defaultMode`;
      no hooks; the only allow rule is `Bash(./scripts/check.sh)`; renders, ComfyUI, downloads, commits,
      pushes, merges/rebases/resets and governance edits are in `ask`; `workflows/official`, model
      weights, the ComfyUI checkout, `.env`/token reads and force pushes are in `deny`.
- [ ] `.claude/rules/*.md` frontmatter contains only `paths`.
- [ ] Five agents with only documented frontmatter fields, `name` equal to the file name, no `memory`,
      `Agent` in every `disallowedTools`:
  - [ ] `project-architect`: no Write/Edit/NotebookEdit, `permissionMode: plan`, start only from a
        Manual/default or Plan parent, stops if the parent mode cannot be confirmed.
  - [ ] `episode-director`: preloads `h3-short-drama-direction`; uses `h3-prompt-writing` only if present
        and degrades safely when it is missing; no infrastructure edits, no ComfyUI, no renders.
  - [ ] `pipeline-engineer`: regression test for every bug fix; no delivered episode content; no renders.
  - [ ] `render-operator`: no Write/Edit/NotebookEdit; runs only approved card commands; main checkout
        only, from a new Manual/default session; one at a time; render lock with owner file
        (task ID, PID, start time, checkout), ownership check before release, `rmdir`, no `rm -rf`,
        stop on mismatch or uncertainty; never picks final takes.
  - [ ] `independent-project-auditor`: no Write/Edit/NotebookEdit/Agent, `omitClaudeMd: true`,
        `permissionMode: dontAsk`, no memory; four-field prompt; Manual/default parent only; reads every
        untracked file in full; runs exactly `./scripts/check.sh`; reports severity, `file:line`, evidence,
        recommendation; never fixes; states honestly that path-scoped rules may still load.
- [ ] `docs/status/current.md` states: Phase 0 done (`4ca5016`), baseline 17 passed / 4 skipped / 0 failed
      with the reason for each skip, rendering and licensing limits, Phase 1 in progress.
- [ ] `docs/tasks/TEMPLATE.md` contains status, owner/agent, goal and background, allowed paths, forbidden
      paths, acceptance criteria, verification commands, risks, human approval points, final handoff record.
- [ ] `./scripts/check.sh`: 17 passed, 4 skipped, 0 failed.
- [ ] No commit, push or render.

## Verification commands
```
git status --short --untracked-files=all
git diff --name-only
./scripts/check.sh
```
Frontmatter and JSON were also checked with a throwaway script (session scratchpad, not in the repo).

## Risks
- Path limits for the writing agents (episode-director, pipeline-engineer) are enforced by instructions,
  rules and audit only; per-agent path enforcement would need hook scripts (out of scope).
- Read-only boundaries depend on the parent session's permission mode (Auto, Accept Edits and Bypass
  override a subagent's `permissionMode`).
- `Bash(git push *)` does not match `git -C <dir> push` (documented limitation of Bash rules).
- After merging, sessions in worktrees under `.claude/worktrees/` also load the main checkout's
  `CLAUDE.md`; `.gitignore` does not list `.claude/worktrees/` (only the main checkout's
  `.git/info/exclude` does). Both are recorded as follow-ups in `docs/status/current.md`.
- New agents and settings take effect only in a new Claude Code session.

## Human approval points
- [x] Card approved — 2026-10-26 (governance plan approved by the owner in session; bootstrap exception)
- [x] Bootstrap follow-up (this card, four-field audit prompt, untracked-file audit step) — 2026-10-26
- [x] Independent audit result reviewed by the owner
- [x] Commit (and push) — only on the owner's request — local commit approved 2026-10-26; push and merge not approved yet

## Audit record
I ran the audit and the verdict is **PASS**, with three minor findings and one nit. No blocker or major issues.

```
Audit: docs/tasks/2026-10-26-phase1-agent-governance.md  base 4ca5016  head working tree (HEAD = 4ca5016ca5351ffeb44c0fc0a335e5230ccaa749, no commits)
Parent mode confirmed Manual/default: yes
Gate: 17 passed, 4 skipped, 0 failed  (baseline: 17 passed, 4 skipped, 0 failed)
Verdict: PASS
```

The prompt had exactly the four fields and no implementer summary. The parent mode is stated in the prompt, and my session behaved accordingly: several non-read-only commands were denied while `./scripts/check.sh` ran.

**Acceptance criteria**
- **[PASS] Only allowed paths changed.** `git status --short --untracked-files=all` lists exactly 16 `??` paths, all on the card's allowed list. `git diff --name-only 4ca5016` is empty and `git log 4ca5016..HEAD` is empty.
- **[PASS] No Python, episode, prompt, workflow, README or `check.sh` change.** `git diff --stat 4ca5016 -- workflows/official scripts episodes prompts README.md .gitignore docs/decisions.md config inputs` prints nothing.
- **[PASS] `AGENTS.md` holds every required global rule.**
  - Local-only and no paid services: §1. Non-negotiables: §3 (items 1–5 and 7). Shared resources with all five named: §4. Qwen non-commercial: §5. Owner approvals for takes, licence and publication: §7. Sources of truth: §9.
  - The decision references are correct: D11 covers Comfy Cloud and partner/`api_*` nodes, D14 covers fl2va/ref2va memory, and D16, D17 and D18 match their claims.
- **[PASS] `CLAUDE.md`.** It is 54 lines and imports `@AGENTS.md` at line 5. It has the gate, agent roster, start modes, four-field audit prompt, rules/skills/settings notes and a docs index. Overlap with `AGENTS.md` is limited to one-line pointers.
- **[PASS] `.claude/settings.json`.**
  - `jq` parses it. Top-level keys are only `$schema` and `permissions`. `disableBypassPermissionsMode` is `"disable"`, there is no `defaultMode` and no hooks, and the only allow rule is `Bash(./scripts/check.sh)`.
  - The ask list covers renders, ComfyUI, downloads, commit, push, merge, rebase, reset and governance edits.
  - The deny list covers `workflows/official`, `~/AI_models`, `~/dev/ComfyUI`, `.env`/`*.token` reads and force pushes (with a gap, see findings).
- **[PASS] Rule files contain only `paths` in their frontmatter.** I read all five in full.
- **[PASS] Five agents.** Each `name` matches its file name, none has `memory`, and all have `Agent` in `disallowedTools`.
  - **[PASS] `project-architect`:** Write/Edit/NotebookEdit blocked, `permissionMode: plan`, and it stops if the parent mode is unconfirmed (lines 14–17).
  - **[PASS] `episode-director`:**
    - It preloads `h3-short-drama-direction`, which exists at `.claude/skills/h3-short-drama-direction/SKILL.md`.
    - Its fallback when `h3-prompt-writing` is missing is at lines 16–22. The skill really is absent in this worktree, and the fallback's source, `docs/third_party.md`, exists.
    - Infrastructure edits, ComfyUI and renders are forbidden (lines 33–34).
  - **[PASS] `pipeline-engineer`:** a regression test is required for every bug fix (line 19), and delivered episodes and renders are forbidden (lines 29–31).
  - **[PASS] `render-operator`:** Write/Edit/NotebookEdit blocked, approved card commands only, main-checkout checks, one at a time. The lock's owner file records task, PID, start time and checkout. Ownership is checked before `rm owner && rmdir`, `rm -rf` is never used, it stops on a mismatch or unclear state, and it never picks final takes.
  - **[PASS] `independent-project-auditor`:** all criterion items are present. My own run is consistent: no `CLAUDE.md` in my startup context, a path rule loaded when I read `docs/tasks/…`, and `dontAsk` denials happened.
- **[PASS] `docs/status/current.md`.**
  - It records Phase 0 done at `4ca5016` and the 17/4/0 baseline. Each skip reason matches what `check.sh` printed: `_owner_selfie`, `nailong`, `Urban_Lifestyle_Commercial` and vision integration.
  - It has rendering and licensing limits and shows Phase 1 as in progress.
- **[PASS] `docs/tasks/TEMPLATE.md`** has every required section, plus a render-task table.
- **[PASS] `./scripts/check.sh`** printed `17 passed, 4 skipped, 0 failed`.
- **[PASS] No commit or push:** HEAD equals the base. **[NOT VERIFIED] No render:** nothing in Git suggests a render, but I did not inspect `~/AI_renders`.

**Findings (most severe first)**
- **minor** `.claude/settings.json:12-13` — The force-push deny rules only catch `--force` or `-f` placed right after `git push`. Forms like `git push origin main --force`, `git push --force-with-lease` and `git push origin +main` don't match them. They still hit the ask rule `Bash(git push *)`, so they ask instead of being blocked.
  - Evidence: the rules are `"Bash(git push --force *)"` and `"Bash(git push -f *)"`.
  - Recommendation: the owner decides whether to add deny patterns such as `Bash(git push * --force*)`, `Bash(git push --force-with-lease*)` and `Bash(git push *+*)`, or to record the gap under Risks.
- **minor** `.claude/agents/*.md:4` (all five agents) — `tools` lists `Grep` and `Glob`, but those tools don't exist in this installed version.
  - Evidence: calling Grep returned "No such tool available: Grep. Grep is not available in this session — search file contents with `grep` via the Bash tool instead." My tool list contained only Read and Bash.
  - Recommendation: drop `Grep` and `Glob` from `tools`, or note that searching goes through Bash `grep`. It is harmless today but misleading.
- **minor** `.claude/agents/independent-project-auditor.md:20-21` together with `.claude/settings.json` — Under `dontAsk`, the auditor is denied several read-only checks it needs.
  - Evidence: these were denied: `git ls-files <paths>`, `python3 -m json.tool .claude/settings.json`, a multi-path `ls -d …`, and `grep -n -A12 "^---$" <five rule files>`. These were allowed: `jq`, single-path `ls`, `grep -n`, `git diff --stat`.
  - Effect: the frontmatter and JSON checks in the handoff (done "with a throwaway script", card line 103) can't be reproduced the same way. I worked around this with `jq` and by reading every file in full.
  - Recommendation: as the card's own handoff says, give the owner the exact rules to decide on (e.g. `Bash(git ls-files *)`). Or document which tools the auditor is expected to use.
- **nit** `docs/tasks/2026-10-26-phase1-agent-governance.md:103` — The throwaway frontmatter/JSON check is not in the repo, so it can't be re-run.
  - Recommendation: list the exact commands in the card's verification section.

**Not verified**
- Whether `omitClaudeMd` and the other frontmatter fields appear in the official docs for 2.1.311. I had no network access and `claude --version` was not attempted. Indirect evidence that it works: no `CLAUDE.md` or `AGENTS.md` content was in my startup context.
- That `/memory` loads `CLAUDE.md` and `AGENTS.md`, and that the ask/deny rules prompt as intended in a fresh session. That needs interactive sessions.
- The card's claim that the bootstrap follow-up touched only `CLAUDE.md`, the auditor file and the card. All files are untracked, so there is no history to check.
- That `scripts/review_server.py`, `episodes/README.md` and `episodes/_multiref` are tracked files. `git ls-files` was denied; the other referenced files exist (I read them or listed them).
- That no render happened in `~/AI_renders`. I did not inspect it, to stay inside the repo.

Files audited, all under `/Users/marcusmao/dev/AI_short_drama/.claude/worktrees/phase1-agent-governance/`:
- `AGENTS.md`
- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/rules/` (five files)
- `.claude/agents/` (five files)
- `docs/status/current.md`
- `docs/tasks/TEMPLATE.md`
- `docs/tasks/2026-10-26-phase1-agent-governance.md`

### Owner disposition — 2026-10-26
Written by the owner's session after the audit; not part of the auditor's report. The owner accepts the
audit PASS. The three minor findings and the nit are non-blocking known limitations: not fixed, and no
permissions widened.
- **Force-push pattern gaps:** accepted for Phase 1. All normal `git push` commands still ask; stronger
  enforcement would need a hook in a later task.
- **Grep/Glob in agent `tools`:** accepted as a runtime limitation of background subagents; the documented
  fields stay for now.
- **Auditor denied read-only commands under `dontAsk`:** no new auditor allow rules. Least privilege is
  preferred, because the audit completed successfully.
- **Throwaway verification script not reproducible:** accepted as a nit.
- **Interactive checks:** completed by the owner. `CLAUDE.md` and `AGENTS.md` loaded, the project
  Ask/Deny/Allow rules loaded, and `Bash(*pipeline.py*)` produced a confirmation prompt.

## Final handoff record
Written by the implementing session. The auditor treats this as claims to verify.
- Files changed: 16 new, untracked files — the 15 governance files listed under "Allowed paths" plus this
  card. No tracked file modified or deleted.
- Tests added or changed: none (no code changed).
- `./scripts/check.sh` before (on `4ca5016`, after merging main): `17 passed, 4 skipped, 0 failed`
- `./scripts/check.sh` after: `17 passed, 4 skipped, 0 failed`
- Checks run: `claude --version` → 2.1.311; `settings.json` parses as JSON; every agent/rule frontmatter
  uses only documented fields, agent names match file names, no `memory`, `Agent` disallowed everywhere.
- No commit, no push, no render, no ComfyUI start, no download.
- Not done / open questions: the new agents, `/memory` loading of `CLAUDE.md` + `AGENTS.md` and the
  permission rules are not yet verified in a fresh session; the first independent audit is pending. If
  the auditor is denied a command it needs under `dontAsk`, the exact rule goes to the owner for approval.
- Noticed outside the scope (reported, not fixed): `.claude/worktrees/` is not in `.gitignore`; ancestor
  `CLAUDE.md` loading for worktree sessions.
