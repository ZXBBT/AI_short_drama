# SeedVR2 video upscaling on this Mac (to-do #10, 2026-10-26)

Owner request: "a higher resolution on generated video". SeedVR2 (ByteDance, Apache 2.0, one-step video
restoration) through ComfyUI core nodes, graph = the official template
`workflows/official/utility_seedvr2_3b_int8_upscale_video__templates-0.11.89.json` (subgraph, split latent off),
built by `scripts/upscale.py`. Files: `models/manifest_seedvr2.tsv` (Comfy-Org/SeedVR2 rev df48879, sha256
verified). Records: `runs/2026-10-26/upscale__*.json`; videos: `~/AI_renders/comfyui/upscaled/`.

## Results (x2, 1 step, seed 1)

| Clip | Model | Colour | Time | Encode / upscale / decode | Peak memory | Frame-to-frame change (flicker) |
|---|---|---|---|---|---|---|
| Sunlight P2, 480x864 → **960x1728**, 107 frames | 3B | none | 9.1 min | 124 / 68 / 348 s | 46.6 GiB | 2.81 → 3.60 |
| same | **7B sharp** | none | 9.9 min | 136 / 105 / 347 s | 49.3 GiB | 2.81 → 3.40 |
| same | 3B | lab | 9.4 min | | 43.2 GiB | 3.55 |
| same | **7B sharp** | **lab** | 9.9 min | | 50.1 GiB | **3.37** |
| Commercial S2B2, 864x480 → **1728x960**, 90 frames | 3B | none | 8.5 min | 116 / 61 / 333 s | 41.2 GiB | 2.20 → 2.49 |
| same | 7B sharp | none | 8.4 min | 116 / 89 / 298 s | 52.3 GiB | 2.20 → 2.50 |

No memory failures; temporal chunking was not needed at these sizes.

## What we saw
- **Both models add real detail**: eyelashes, hair strands, skin texture, and the faces of background people,
  which were mush at 480x864, become readable. Much better than plain resizing.
- **3B adds artefacts**: glittering specks in the foliage and an oily shine on the nose. **7B sharp is clean**
  and costs only ~40 s more (the time is mostly the tiled VAE decode, 5-6 min, the same for both).
- **Colour:** the template's `none` warms the picture and raises contrast (std 61.9 → 65.4). `lab` restores
  the original contrast (62.5) and hue balance; overall ~3 levels darker. **Default here: 7B sharp + lab.**
- Frame-to-frame change rises ~20 % (more fine detail moving). I compared still frames only; whether this
  shows as shimmer must be judged by eye in motion (owner review of sunlight_v2-hd).

## How to use it (optional step before assembly)
1. Pick and confirm takes as usual (structure before polish: never upscale to fix a bad take).
2. In cut.yaml, add `upscale: 7b_sharp` to the shots to upscale (or all).
3. `scripts/upscale.py --cut episodes/<ep>/cut.yaml` upscales exactly the picked takes (skips ones done).
4. `scripts/assemble.py episodes/<ep>/cut.yaml`: the editor finds each upscale by the take's sha256;
   `native` becomes the upscaled size, smaller shots in the same cut are scaled to match.
Cost: about 10 min per 4 s shot, so a 5-shot episode adds ~45 min.
