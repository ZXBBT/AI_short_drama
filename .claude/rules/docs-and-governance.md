---
paths:
  - "docs/**"
  - "README.md"
  - "AGENTS.md"
  - "CLAUDE.md"
  - ".claude/**"
---

# Docs and governance files

General rules: `AGENTS.md` §7-§9.

- `docs/status/current.md` is the only description of the current state. Update it when a phase or task
  changes the state (test baseline, phase, limits); write facts with dates and commit hashes, not plans.
- Stage reports (`docs/stage*`, `docs/*-results.md`, `docs/automation-plan.md`) and README's "Stage status"
  table are history. Do not rewrite them to look current; add new results as new files or sections.
- `docs/decisions.md` is append-only: new D-number for each decision; to change one, add a new entry that
  supersedes it and says so. Decisions need the owner's approval.
- Task cards live in `docs/tasks/`, one per task, from `TEMPLATE.md`. Keep the audit record exactly as the
  auditor wrote it.
- Governance files (`AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `.claude/rules/**`,
  `.claude/agents/**`) change only on an approved card. Keep `CLAUDE.md` short and free of rules that
  duplicate `AGENTS.md`. Agent files use only documented frontmatter fields.
- Never widen `.claude/settings.json` (new allow rules, removing deny/ask rules, permission modes)
  without the owner's explicit approval of the exact rule.
- Docs are in English, like the rest of the repo.
