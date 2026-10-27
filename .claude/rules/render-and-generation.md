---
paths:
  - "config/**"
  - "runs/**"
  - "scripts/pipeline.py"
  - "scripts/episode.py"
  - "scripts/launch_comfyui.sh"
  - "scripts/run_h3_t2v.py"
  - "scripts/qwen_image.py"
  - "scripts/upscale.py"
  - "scripts/assemble.py"
---

# Rendering and generation settings

General rules: `AGENTS.md` §3-§4 and §7. Background: `docs/decisions.md` (D9-D18).

- These files start or drive ComfyUI, MPS and the shared folders. Running them for real (not `--help`,
  not `--dry-run`, not `validate`/`plan`) is a render and needs an approved render card, executed by
  `render-operator` from a new Manual/default session in the main checkout, holding the render lock.
- Never start a second ComfyUI or a render while one is running (port 8188 answering with a queue, another
  `main.py` process, or `~/AI_renders/comfyui/.render-lock` present).
- `config/recipes/` are versioned: a recipe never changes in place; a new behaviour is a new version
  (`h3_base_v3`, …) plus a `docs/decisions.md` entry. Same for `config/extra_model_paths.yaml`, launch
  flags, attention mode, render sizes and the swap limit.
- Measured limits on this Mac: 864x480 up to 107 frames, 608x352 up to 124 frames; swap > 20 GiB stops a
  render; fl2va and ref2va are never resident together; Qwen edits need `--bf16-text-enc`; H3 renders use
  the normal launch. Do not exceed them without an approved experiment card.
- `runs/` holds per-render records written by the scripts. Never edit or delete them by hand; they are the
  evidence that finished takes are not rendered twice.
- Upscaling (SeedVR2) and assembly write into `~/AI_renders/comfyui` and count as render work.
