---
paths:
  - "workflows/**"
  - "models/**"
  - "inputs/**"
  - "env/**"
---

# Workflows, model manifests, input pictures and environment logs

General rules: `AGENTS.md` §3, §5-§6.

- `workflows/official/` holds unmodified official templates. Never edit them (the settings deny it). Our
  changes go into `workflows/project/`, and every deviation from an official template is logged in
  `docs/decisions.md`.
- `models/` holds manifests only (file names, sizes, SHA-256) and verification logs. Weights live in
  `~/AI_models/comfyui` and are never committed, moved or edited by agents. Downloads
  (`scripts/fetch_models.sh`) need the owner's approval; verify with `scripts/verify_models.sh`.
- `inputs/` holds small reference pictures. Before adding one, state its origin and licence. Third-party
  people, characters, trademarks or products stay local-only (gitignored by owner decision) and are
  listed in `scripts/check.sh` only with the owner's approval.
- Pictures made with Qwen-Image 2.1 are non-commercial (D17): name or tag them so they can be found and
  replaced before any monetised use.
- `env/` records versions and environment snapshots. Append; do not rewrite history. Installing or
  upgrading software needs the owner's approval.
