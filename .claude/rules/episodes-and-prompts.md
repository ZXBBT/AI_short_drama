---
paths:
  - "episodes/**"
  - "prompts/**"
  - "subtitles/**"
---

# Episodes, prompts and subtitles

General rules: `AGENTS.md`. Format reference: `episodes/README.md`, `docs/stage8-brief-format.md`.

- Write shots and prompts with both skills: `h3-prompt-writing` (official format; may be missing in a
  worktree — then follow the fallback in `.claude/agents/episode-director.md`) and
  `h3-short-drama-direction` (project direction rules).
- After editing a brief or episode, run the offline checks (they need no ComfyUI):
  `~/dev/ComfyUI/.venv/bin/python scripts/brief.py check-plan episodes/<name>` (when the episode has a
  `brief.yaml`), `~/dev/ComfyUI/.venv/bin/python scripts/episode.py validate episodes/<name>`, and
  `./scripts/check.sh`.
- Any change to a prompt, size, seed, recipe or input picture changes the shot's fingerprint: its finished
  takes no longer count and the shot (and shots that continue it) would render again. Say so in the
  handoff, with the list of affected shots (`episode.py plan` shows it).
- Confirmed episodes (`sunlight`, `midnight_call`, `Urban_Lifestyle_Commercial`) are delivered work: change
  them only when the card names them.
- `selections.yaml` and its `_confirmed` entry record the owner's picks. Agents never write them, never run
  `episode.py select`, and never confirm on the review page.
- Do not render, start ComfyUI or run `pipeline.py` from an editing task; rendering is a separate approved
  card (`AGENTS.md` §4).
- Reference pictures referenced from an episode must be either tracked in `inputs/` or listed as
  local-only by owner decision; never add a third-party or trademark picture to Git.
- Subtitles (`subtitles/*.srt`) are written by `assemble.py`; edit by hand only when the card says so.
