# Qwen-Image 2.1 on this Mac (MPS test, 2026-10-26)

To-do #3 / task #8. Licence: Qwen RESEARCH LICENSE, so every picture below is **non-commercial**
(research/evaluation only; decision D17). Graphs follow the official templates (copies in
`workflows/official/image_qwen_image_2_1_*__templates-0.11.89.json`), built by `scripts/qwen_image.py`;
records in `runs/2026-10-26/qwen_image__*.json`; pictures in `~/AI_renders/comfyui/qwen_image/`
(contact sheet `_qwen_mps_test_sheet.jpg`). M5 Max 64 GB, ComfyUI 0.42.1, PyTorch attention.

## Results

| Run | Mode | Size | Time | Peak memory | Result |
|---|---|---|---|---|---|
| Q1 s1 / s2 | text-to-image, 25 steps | 1024x1536 | 2.1 / 2.9 min | 39.6 GiB | photoreal portrait, face 487-502 px, Vision quality **0.77-0.78** |
| Q1T | turbo, 8 steps | 1024x1536 | **1.1 min** | 35.1 GiB | same quality (0.84), slightly smoother skin |
| Q3 | text in the picture | 1024x1024 | 1.9 min | 34.6 GiB | sign reads "SUNLiGHT CAFE" (OCR, confidence 1.0), chalkboard "Fresh coffee 9am - 6pm" legible |
| Q2 | 2K plate (9:16) | 1152x2048 | 3.8 min | 30.3 GiB | very photoreal empty park path, phone-photo look |
| Q5 / Q6 | edit / background removal | ref 480x864 at resolution 1024 | 3.6-4.1 min | 42 GiB | **all-black picture** (NaN, no error) |
| Q5b / Q6b | same with `--bf16-text-enc` | resolution 1024 | 1.8-2.4 min | 28 GiB | no NaN, but faces embossed / sketch-like |
| **Q5c** | **outfit edit**, `--bf16-text-enc` | **resolution 0** (template) | **1.0 min** | 26.4 GiB | identity kept exactly, white T-shirt → denim shirt |
| **Q6c** | **background removal** | resolution 0 | **1.0 min** | 26.2 GiB | clean cut-out with a real alpha channel |
| Q7 | 2 references (park plate + Lin) | resolution 1024 | – | out of memory | MPS allocation limit (88 GiB) |
| **Q7b** | 2 references | resolution 768 | **1.6 min** | 28.4 GiB | Lin seated on the plate's bench, park kept; she is small in the frame |

For comparison, the H3 still method (docs/quality-track-results.md, to-do #11) takes 2-4 min per 768x1376
still and scored 0.69-0.70.

## What we learned
1. **Text-to-image quality is higher than H3 stills** (face quality 0.77-0.84 vs 0.69-0.70) and as fast or
   faster. Turbo (8 steps) halves the time with no visible loss on a portrait.
2. **It draws text.** H3 garbles packaging and signs (take checks flag "DRY R", "500 гml"); Qwen wrote a
   two-word sign and a chalkboard line correctly. Usable for screen graphics, signs and product labels
   (non-commercial).
3. **Edits need two settings on MPS** (D17): `--bf16-text-enc` at ComfyUI start (the CPU fp16 text
   encoder overflowed to NaN on pictures) and `resolution` 0. With both, edits take about a minute and keep
   the face exactly.
4. **Two references work at a lower budget** (768): useful for placing a character in a location plate as
   a start frame for H3 I2V. Ask for a closer framing ("from the waist up") to get a usable face size.

## Limits and open points
- Non-commercial only: Qwen pictures may be used for tests, look development and references we later
  replace; never in a monetised video without a commercial licence (to-do #8 licensing review).
- `--bf16-text-enc` was tested with Qwen only; H3 runs keep the normal launch. Restart ComfyUI between the two.
- The prompt enhancer (extra 9B model) stayed off, as in the templates.
