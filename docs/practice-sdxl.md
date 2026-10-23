# Practice: learn ComfyUI with SDXL (Stage 2)

Goal: learn the UI with renders that take seconds, before H3 renders that take minutes.
Model: `sd_xl_base_1.0.safetensors` (practice only, see `models/practice_manifest.tsv`).
Reference copy of the template: `workflows/official/image_sdxl_simple__templates-0.11.89.json`.

Menu names below are from frontend 1.55.18 and may differ slightly in other versions.

## 0. Start and stop
- Start: `~/dev/AI_short_drama/scripts/launch_comfyui.sh` in Terminal, then open http://127.0.0.1:8188
- Stop: press `Ctrl+C` in that Terminal window.
- The Terminal window is the log: it shows load times, progress bars and errors. Keep it visible.

## 1. Load the official template
Templates (left sidebar) → search **"SDXL1.0: Text to Image (Simple)"** → open.
You will see 5 working nodes, which is the shape of almost every diffusion workflow:

| Node | Job |
|---|---|
| Load Checkpoint | loads model + text encoder (CLIP) + VAE from one file |
| CLIP Text Encode ×2 | turns positive / negative prompt text into conditioning |
| Empty Latent Image | sets resolution and batch size (a blank "canvas" in latent space) |
| KSampler | the denoising loop: seed, steps, cfg, sampler, scheduler |
| VAE Decode → Save Image | converts the latent into pixels and writes a PNG |

H3 has the same shape, but loads model / text encoder / VAE from **separate** files.

## 2. First run
Click **Run**. The first run is slower (model loads from disk); watch the Terminal log.
Output lands in `~/AI_renders/comfyui/`.

## 3. Exercises (change ONE thing at a time, note the result)
1. **Seed:** set KSampler `control after generate` to **fixed**, run twice. Same image? (This is
   the reproducibility question Stage 5 tests for H3 on MPS.)
2. **Steps:** 25 → 10 → 40. Watch time vs. quality.
3. **CFG:** 7 → 3 → 12. Low = loose/soft, high = literal/over-saturated.
4. **Resolution:** 1024×1024 → 768×768. SDXL is trained at ~1024²; far below looks worse.
5. **Negative prompt:** delete it and compare.
6. **Metadata:** drag a saved PNG from `~/AI_renders/comfyui/` back onto the canvas — the full
   workflow and seed are restored, because ComfyUI embeds them in the PNG.
7. **Export:** Workflow menu → Export → save into `~/dev/AI_short_drama/workflows/project/`.

## Common mistakes
- Changing several settings at once, then not knowing which one mattered.
- Leaving the seed on `randomize` and being unable to recreate a good result.
- Editing the official template file instead of saving your own copy.
- Closing the Terminal window (that stops ComfyUI).
