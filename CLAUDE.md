# CLAUDE.md — Claude Code entry point

Project rules (all agents, all tools):

@AGENTS.md

## Start here
- Current state, test baseline and open limits: `docs/status/current.md` (the only status source).
- Quality gate: run `./scripts/check.sh` before and after every change (exactly this command).
- New task: copy `docs/tasks/TEMPLATE.md`; work starts only after the owner approves the card.
- The owner is a beginner: explain each action in plain words and say what it touches.

## Agents (`.claude/agents/`)
Only the main session starts agents; no agent can start another.

| Agent | Use for | Start only from |
|---|---|---|
| `project-architect` | read-only structure, dependency and refactor analysis | a Manual/default or Plan session |
| `episode-director` | brief, episode.yaml, shots, prompts | any session, on an approved card |
| `pipeline-engineer` | scripts, tests, schema | any session, on an approved card |
| `render-operator` | executing an approved render card | a **new Manual/default session in the main checkout** `/Users/marcusmao/dev/AI_short_drama` — never from a worktree session |
| `independent-project-auditor` | read-only audit of a finished card | a **Manual/default** session only |

- Permission mode matters: a parent session in Auto, Accept Edits or Bypass overrides a subagent's
  `permissionMode`, and a Plan parent keeps it in plan. The read-only agents still have Bash, so their
  read-only boundary depends on the parent mode in the table. If the mode cannot be confirmed, do not start them.
- Audit prompt: exactly four fields, nothing else — never the implementer's summary or explanations.
  The auditor runs `./scripts/check.sh` itself.
  ```
  Task card path: docs/tasks/<card>.md
  Base commit: <hash>
  Branch/worktree: <name or path>
  Parent permission mode: Manual/default
  ```

## Path rules (`.claude/rules/`)
Load automatically when matching files are read or edited: scripts and tests; episodes and prompts;
render and generation settings; workflows, models and assets; docs and governance.

## Skills
- `h3-short-drama-direction` (in Git): project direction rules for shots and prompts.
- `h3-prompt-writing` (MiniMax, not in Git): the official H3 prompt format. Missing in new worktrees;
  if absent, say so and follow the fallback in `.claude/agents/episode-director.md`. Do not download or
  copy it without the owner's approval (`scripts/fetch_h3_skills.sh`).

## Settings
`.claude/settings.json` is deliberately conservative: bypass mode disabled; renders, ComfyUI, downloads,
commits, pushes and governance edits always ask; the only pre-approved command is `./scripts/check.sh`.
Do not widen it without the owner's approval.

## Docs index
`README.md` (overview, quick start) · `docs/decisions.md` (D1-D18…) · `docs/third_party.md` ·
`episodes/README.md` · `docs/stage8-brief-format.md` · `docs/tasks/` · `docs/status/current.md`
