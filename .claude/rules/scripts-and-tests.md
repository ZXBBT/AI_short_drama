---
paths:
  - "scripts/**"
---

# Scripts and tests

Applies to everything under `scripts/` (Python, zsh, Swift, tests). General rules: `AGENTS.md` §2-§3.

- Tests are the `scripts/test_*.py` files run by `./scripts/check.sh`. They must stay offline and
  deterministic: no ComfyUI, no rendering, no network, no real macOS Vision (Vision belongs only in
  `scripts/test_vision_integration.py`, which is opt-in).
- A bug fix comes with a regression test in the matching `test_*.py`, written so it fails without the fix.
  Say in the handoff which test and how you saw it fail.
- Never remove, skip, loosen or stub out an existing assertion, and never add an episode or path to the
  skip list in `check.sh`, to get a green result. If a test looks wrong, stop and report it.
- `scripts/check.sh` is the formal gate: changing it needs the owner's approval (the settings ask for it).
  A new test file must also be added to the gate's test list, in the same approved change.
- Keep graph-building code byte-compatible with the proven paths: `episode.py` graphs are compared to
  recorded runs in the tests (D12, D15). A change that alters fingerprints of finished takes is an
  architecture decision (`docs/decisions.md`).
- Do not touch generation defaults (recipes, sizes, attention, launch flags) from a code task; those are
  decisions, see `.claude/rules/render-and-generation.md`.
- Use the ComfyUI venv Python (`~/dev/ComfyUI/.venv/bin/python`). No new dependencies, no `pip install`,
  no `pyproject.toml` or packaging changes unless a task card says so.
- Run `./scripts/check.sh` after every change and paste its summary line into the handoff.
