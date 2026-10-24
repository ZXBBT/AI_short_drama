# Episodes

One folder per episode. Design and reasons: `docs/automation-plan.md`.

```
episodes/<name>/
  episode.yaml      what to render (you write it; Claude can draft it from a script)
  selections.yaml   which take you chose per shot (written by `episode.py select`, or by hand)
  cut.yaml          the edit: play order, frame ranges, per-shot gain, subtitles, output sizes
```

Takes (videos) go to `~/AI_renders/comfyui/episodes/<name>/<shot>/`; one record per take in
`runs/<date>/<name>__<shot>__<take>.json` (all settings, input checksums, timings, memory, checks).

## Commands
Run from the repo with ComfyUI's Python (`PY=~/dev/ComfyUI/.venv/bin/python`):

| Command | What it does | Needs ComfyUI running? |
|---|---|---|
| **`$PY scripts/pipeline.py episodes/X`** | **everything below in one go**: validate, start ComfyUI if needed, render with re-rolls, review sheets, assemble when all picks are made; exit 0 = done, 2 = waiting for you | starts it if needed |
| `$PY scripts/review_server.py episodes/X` | review page at http://127.0.0.1:8189: play every take, click **Pick** | no |
| `$PY scripts/episode.py validate episodes/X` | checks the file: ids, files, seeds, tags, links, sizes | no |
| `$PY scripts/episode.py plan episodes/X` | render order and status of every shot (todo / done / blocked) | no |
| `$PY scripts/episode.py render episodes/X --dry-run` | shows what would be rendered | no |
| `$PY scripts/episode.py render episodes/X [--shot S001]` | renders missing takes, one at a time; refuses if ComfyUI is busy; stops on any failure or swap > 20 GiB | yes |
| `$PY scripts/episode.py select episodes/X S001 <take_id>` | records your choice | no |
| `$PY scripts/episode.py frame video.mp4 best out.png` | extracts a frame (best / last / seconds) | no |
| `$PY scripts/review_sheet.py episodes/X S001 S002` | contact sheet of a shot's takes, for choosing | no |
| `$PY scripts/assemble.py episodes/X/cut.yaml [--dry-run]` | joins the selected takes into the episode (see `cut.yaml`) | no |
| `$PY scripts/assemble.py episodes/X --init` | writes a default `cut.yaml` (all shots in file order, auto levelling on) | no |
| `$PY scripts/test_episode.py`, `test_assemble.py` | offline self-tests | no |

## episode.yaml
```yaml
episode: midnight_call          # folder/record name
recipe: h3_base_v1              # config/recipes/h3_base_v1.yaml: sampler, steps, model files
defaults:                       # apply to every shot unless the shot overrides them
  aspect: "9:16"                # 1:1 2:3 3:2 3:4 4:3 9:16 16:9 21:9
  megapixels: 0.2               # 0.2 -> 352x608 portrait; 0.4 -> 480x864
  duration: 5                   # seconds -> 17k+5 frames (5 s -> 124 frames)
  takes: 1                      # seeds per shot: seed, seed+1, ...
assets:                         # images in inputs/ (tracked by Git)
  kf_desk: inputs/midnight_call/kf_S001_desk_v1.png
characters:
  woman: {description: ..., refs: [kf_desk]}   # refs = asset ids
shots:
  S001:                         # shot id; shots render in dependency order, not file order
    type: i2v                   # t2v | i2v | flf2v | r2v
    first: kf_desk              # i2v/flf2v: asset id, or {shot: S000, frame: best|last|<seconds>}
    # last: kf_door             # flf2v only
    # refs: [woman]             # r2v only: characters/assets -> <Picture 1>, <Picture 2>, ...
    prompt: ...                 # or prompt_file: prompts/<episode>/S001.txt
    seed: 757358688076805       # or seeds: [1, 2, 3]
    # takes: 3
    # recipe_overrides: {scheduler: beta}   # experiments only: sampler, scheduler, steps, ref_image_size
    # allow_cuts: true          # H3's own hard cuts are wanted here (default false: a cut = failed check)
    # max_rerolls: 1            # extra seeds when a take fails a check (default 1; seed = first + 1000 + k)
    note: free text
```

**Take id** = first 8 characters of the shot's fingerprint + `_s<seed>`. The fingerprint is a hash
of everything that decides the picture except the seed (graph, prompt, size, recipe, model
checksums, input-image pixels). Edit a shot → new fingerprint → `plan` shows it as `todo` again;
old takes stay on disk and in `runs/`.

**Continuations** (`first: {shot: S001, frame: best}`) use the take selected in
`selections.yaml`, so they show `blocked` until you select one. The chosen frame index is
recorded; the earlier take must be cut at that frame when editing (see the plan, §3).

**Quality checks and re-rolls.** Every take is checked for unwanted hard cuts and, for I2V, whether
frame 0 follows the input image. A take that fails is kept (you can still pick it) but does not count
as good; the renderer tries the next seed until the shot has enough good takes or its `max_rerolls`
budget is used up (state `needs_review`). Errors, defective videos and swap stops halt the batch.

## Common mistakes
- Editing a prompt and expecting old takes to count: they belong to the old fingerprint.
- Writing `<Picture 2>` when the shot has one image: validate rejects it.
- Running `render` while you are rendering in the UI: it refuses; wait until the queue is empty.
- Putting large videos in `inputs/`: only small images belong in Git.
