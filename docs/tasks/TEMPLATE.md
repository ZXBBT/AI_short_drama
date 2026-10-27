# <TASK-ID>: <short title>

Copy to `docs/tasks/<YYYY-MM-DD>-<slug>.md`. Work starts only when the owner sets the status to `approved`.
Rules: `AGENTS.md` §8.

## Status
`draft` | `approved` | `in_progress` | `implemented` | `in_audit` | `changes_requested` | `done` | `cancelled`

Current: `draft`

| Field | Value |
|---|---|
| Owner / responsible agent | <owner> / <episode-director \| pipeline-engineer \| render-operator \| project-architect> |
| Base commit | <hash> |
| Branch / worktree (or main checkout for renders) | <name / path> |
| Shared resources needed | none \| ComfyUI + MPS (render task) |

## Goal and background
<What should be true when this is done, and why. Links to decisions, earlier cards, owner messages.>

## Allowed paths
- <path or glob>

## Forbidden paths
- `workflows/official/**`, model weights, generated media, local-only inputs (always)
- <task-specific>

## Acceptance criteria
Each one checkable from files, diff or command output.
- [ ] <criterion>
- [ ] `./scripts/check.sh` summary is <expected, e.g. 17 passed, 4 skipped, 0 failed> or better, with no new SKIP
- [ ] Bug fixes have a regression test that fails without the fix

## Verification commands
```
./scripts/check.sh
<task-specific, e.g. ~/dev/ComfyUI/.venv/bin/python scripts/episode.py validate episodes/<name>>
```

## Risks
- <what could break, what would show it>

## Human approval points
- [ ] Card approved — <date>
- [ ] <render / download / decision entry / take choice / licence / commit / push> — <date>

## Render task (only for render cards)
| Field | Value |
|---|---|
| Exact commands | <copied verbatim; render-operator runs only these> |
| Target commit (main checkout) | <hash> |
| Episode / shots / seeds | <…> |
| ComfyUI launch mode | <PyTorch attention (default) \| COMFY_ATTENTION=default \| --bf16-text-enc> |
| Expected duration | <…> |
| Swap limit | <20 GiB default> |

## Audit record
<Pasted unchanged from independent-project-auditor's report, with date and audited commit.>

## Final handoff record
Written by the implementing agent. The auditor treats this as claims to verify.
- Files changed:
- Tests added or changed (and how they failed before the fix):
- `./scripts/check.sh` before (verbatim summary):
- `./scripts/check.sh` after (verbatim summary):
- Not done / open questions:
- Noticed outside the scope (reported, not fixed):
