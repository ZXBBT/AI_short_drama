# Practice: MiniMax H3 video in the ComfyUI UI

Goal: learn H3 hands-on in the UI (text-to-video first, then image-to-video, then
reference-to-video) without crashing the Mac or losing track of what worked.
Start with `docs/practice-sdxl.md` if the basic UI ideas (nodes, seed, steps, queue) are new.

Facts below were checked on 2026-10-23 against ComfyUI v0.42.1, frontend 1.55.18, templates
0.11.89 and the Hugging Face repo `Comfy-Org/MiniMax-H3` @ `e5eb578a`. Menu names may differ in
other versions.

Status labels used in this guide:

| Label | Meaning |
|---|---|
| ✅ tested | rendered successfully on this Mac (records in `runs/`) |
| ⚠️ untested | all models are downloaded and it should work, but nobody has run it here yet |
| ⛔ needs download | a model is missing; downloading it needs your approval first |

---

## 0. Before every session

1. **Close heavy apps** (Chrome, Docker, games). H3 itself uses ~52 GiB of the 64 GiB memory.
2. **Open Activity Monitor → Memory tab.** Watch *Memory Pressure* (green/yellow/red) and *Swap
   Used* at the bottom.
   - Swap is disk used as overflow memory. Our normal runs used 6–11 GiB; that is fine.
   - **If swap goes above ~20 GiB, or pressure is red,** cancel the run (✕ on the running job in
     the queue panel) and use smaller settings next time. Heavy swapping wears the SSD and can
     make the Mac freeze.
3. **Start ComfyUI** in the Terminal app (not inside this Claude chat):
   ```
   ~/dev/AI_short_drama/scripts/launch_comfyui.sh
   ```
   Open http://127.0.0.1:8188 when Terminal prints `To see the GUI go to: http://127.0.0.1:8188`.
   The Terminal window is the log: model loading, progress bars and errors appear there.
4. **Stop** with `Ctrl+C` in that Terminal window.
5. **Restart ComfyUI when you switch between model families** (T2V/I2V ⇄ R2V, or H3 ⇄ SDXL). Each
   H3 diffusion model is 21 GB; restarting guarantees two of them are never held in memory at
   once. (The frontend also has an *Unload Models* command, but a restart is the simplest
   reliable method.)

---

## 1. What is downloaded and what it is for

All files live in `~/AI_models/comfyui/` (outside Git and iCloud). Checksums are in
`models/manifest.tsv` and `models/practice_manifest.tsv`; `scripts/verify_models.sh` re-checks them.

| Folder / file | Size | Role | Used by |
|---|---|---|---|
| `diffusion_models/minimax_h3_fl2va_pruned_int8_convrot` | 21.0 GB | The video+audio generator ("fl2va" = first/last-frame to video+audio; with no frames it does text-to-video) | T2V, I2V, first+last frame |
| `text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq` | 15.7 GB | Reads your prompt *and any input images* (Qwen3-VL). Runs on the **CPU**, ~30 s per new prompt | every H3 workflow |
| `vae/minimax_h3_video_vae_fp16` | 5.2 GB | Turns the generated latent into video frames. **Use this one, not int8 (crashes on Mac, decision D5)** | every H3 workflow |
| `vae/minimax_h3_audio_vae_fp32` | 0.6 GB | Turns the latent's audio part into stereo sound | every H3 workflow |
| `loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16` | 2.0 GB | Optional "Lightning" speed-up: 8 steps instead of 20. Brighter, more CG look; pushed swap to 24.8 GiB here, so **off by default** (D13) | T2V, I2V turbo switch |
| `diffusion_models/minimax_h3_ref2va_pruned_int8_convrot` | 21.0 GB | The reference-to-video generator ("ref2va"): keeps characters/style from reference pictures, videos, audio | R2V, Multiframe Reference |
| `checkpoints/sd_xl_base_1.0` | 6.9 GB | SDXL still-image model, **practice only** (`docs/practice-sdxl.md`). Can also make first frames for I2V experiments | SDXL template |

**Not downloaded** (see §7): the R2V turbo LoRA, the Fun ControlNet patches and pose models, the 10 style embeddings, and the
int8 text encoder (27.1 GB; fallback only, not needed).

---

## 2. Which official templates can run

Open templates from the left sidebar → **Templates** → search "MiniMax H3".

| Template title | Task | Diffusion model | Status here |
|---|---|---|---|
| MiniMax H3: Text to Video | prompt → video+audio | fl2va | ✅ tested, use our copy (§4) |
| MiniMax H3: Image to Video | first image (+ optional last image) → video | fl2va | ✅ tested by owner in the UI (§5) |
| Image to Video | same as above, but starts with an empty prompt | fl2va | ⚠️ untested, runnable now (§5) |
| MiniMax H3: Reference to Video | reference images/videos/audio → new video | **ref2va** | ⚠️ untested, runnable now (§6) |
| MiniMax H3: Multiframe Reference | pin up to 4 images at chosen seconds | **ref2va** | ⚠️ untested, runnable now (§7) |
| MiniMax H3 Fun ControlNet Union | copy the motion of a pose video | **ref2va** + extra models | ⛔ not planned yet (§7) |
| anything starting with `api_` or labelled Cloud / Partner / "Max" | runs on MiniMax's or Comfy's paid servers | — | **do not use** (D11) |

All official H3 templates select the int8 video VAE. **Every time you open one, switch the video
VAE to `minimax_h3_video_vae_fp16.safetensors` before pressing Run.** If you forget, the render
runs for minutes and then fails at the very end (the error mentions `VAEDecode` / `_int_mm`).

---

## 3. Settings every H3 workflow shares

**Size (Resolution Selector node).** You pick an aspect ratio and a megapixel budget; the node
computes width × height (multiples of 32). Time and memory grow with pixels × frames.

| Megapixels | 16:9 landscape | 9:16 portrait (phone drama) | 1:1 square |
|---|---|---|---|
| 0.2 | 608 × 352 ✅ | 352 × 608 | 448 × 448 |
| 0.4 | 864 × 480 ✅ | 480 × 864 | 640 × 640 |

Portrait 0.4 MP has the same pixel count as the tested 864 × 480, so expect similar time, but it
has not been rendered here yet.

**Duration → frames.** You type seconds; a math node converts them to a frame count of the form
17k + 5 (5, 22, 39, 56, 73, …, 124), because the model works in blocks of 17 frames. Output is
24 fps.

| Duration you type | Frames | Real length |
|---|---|---|
| 0.2 | 5 | 0.2 s |
| 1 | 39 | 1.6 s |
| 2 | 56 | 2.3 s |
| 3 | 73 | 3.0 s |
| 5 (template default) | 124 | 5.2 s |

The node's tooltip says H3 was trained on ~124–362 frames (5–15 s). Shorter clips worked well
here, but quality may differ; longer clips are the real goal for drama but are **untested on this
Mac** (memory risk). Grow duration one step at a time and watch swap.

**Measured times (T2V, 20 steps, nothing else running):**

| Size | Frames | Total time | Swap peak |
|---|---|---|---|
| 608 × 352 | 5 | ~2 min | 6–11 GiB |
| 608 × 352 | 22 | ~2.3 min | 7 GiB |
| 608 × 352 | 56 | ~4.5 min | 9 GiB |
| 864 × 480 | 56 | ~9 min | 10 GiB |

**Seed.** Same seed + same settings + same software = identical video (verified in Stage 5).
Set *control after generate* to **fixed** while comparing settings; use **randomize** to explore.

**Steps / sampler / scheduler.** Template defaults: 20 steps, `res_multistep`, `simple`. Leave
them alone at first. Fewer steps is faster but rougher.

**What re-runs.** ComfyUI caches finished nodes. Changing only the seed skips the ~30 s prompt
encoding; changing the prompt or input image re-runs it.

**Outputs.** Videos (`.mp4` with sound) go to `~/AI_renders/comfyui/video/` (filename prefix
`MiniMax_H3`). The workflow is embedded in the file: drag an `.mp4` back onto the canvas to
restore the exact settings and seed.

---

## 4. Text to Video (T2V) ✅

1. **Workflow → Open** → `~/dev/AI_short_drama/workflows/project/h3_t2v_mps_baseline.json`.
   This is the official template with the fp16 VAE already selected, 0.2 MP and 0.2 s. All the
   settings sit on one big node (a *subgraph*: a group of nodes folded into one; double-click
   its title to look inside, use the breadcrumb at the top to go back).
2. Press **Run** once without changes (~2 min). This proves the session is healthy.
3. Exercises, **one change per run**:
   1. Duration 0.2 → 1 → 2 (keep 0.2 MP). Watch how time grows.
   2. Megapixels 0.2 → 0.4 at 2 s (the D13 baseline: 864 × 480, ~9 min).
   3. Aspect ratio 9:16 at 0.4 MP: your first vertical shot.
   4. Same settings, three seeds: see how much variation the seed alone gives.
   5. Write your own prompt (below), keeping the seed fixed.
4. **Prompting.** H3 follows a storyboard-like prompt very literally. The template prompt is a
   good model: a style line, then shots with time ranges, camera moves, what characters do and
   say, and an audio line. Example skeleton:
   ```
   Style: cinematic, warm indoor light, shallow depth of field.
   [0s-1s] Medium shot: a young woman at a café table looks up from her phone, surprised.
   [1s-2s] Close-up: she whispers "You came back."
   Audio: soft café chatter, a cup set down, her quiet voice.
   ```
   Keep the timeline inside the clip's real length. Spoken lines in quotes become voice.
5. **Turbo switch:** leave **off**. If you try it once: nothing else open, 0.2 MP, and watch swap.

---

## 5. Image to Video (I2V) and first + last frame

I2V ✅ tested by the owner on 2026-10-23: 9:16, 0.2 MP (352 × 608), 5 s = 124 frames, ~9.5 min
per take (`runs/2026-10-23/ui_midnight_call_*`). First + last frame ⚠️ untested.

1. Templates → **MiniMax H3: Image to Video** → open.
2. On the big subgraph node, change before the first run:
   - `vae_name` (the video VAE) → `minimax_h3_video_vae_fp16.safetensors`
   - duration **5 → 1** (template default would be 124 frames, far beyond what was tested)
   - leave the turbo/Lightning switch **off**
3. On the **Resolution Selector** (template default 1:1, 0.4 MP = 640 × 640): set **0.2 MP**
   and an aspect ratio that **matches your image**. The first frame is *stretched* to the video
   size, not cropped, so a mismatched aspect ratio squashes the picture.
4. **Load Image** node: click *choose file to upload* and pick your image (the template's sample
   image is not installed). Uploads are stored in `~/dev/ComfyUI/input/`. For anything you want to
   keep, also copy the image into `~/dev/AI_short_drama/inputs/` (tracked by Git).
5. **Prompt:** refer to the image as `<Picture 1>` and describe what moves, the camera and the
   sound, e.g. `The woman from <Picture 1> turns toward the window as rain starts; slow push-in;
   audio: rain on glass.` Don't re-describe everything visible; describe the change.
6. Run. Write down the time and swap peak.

**The keyframe must already show the prompt's scene.** If the picture shows her standing by a
window but the prompt describes her at a desk, H3 obeys the prompt and inserts a hard cut to a
new scene (seen in `midnight_call` take01 at 1.5 s, despite "no cut" in the prompt). Make the
keyframe match the shot's opening, or describe what the keyframe shows.

**First + last frame (FLF2V):** add a second **Load Image** node (double-click the canvas →
search "Load Image"), and drag its IMAGE output onto the subgraph's `last_frame` input. H3 then
plans the motion between the two pictures. The last frame is centre-cropped (not stretched) to
the video size. In the prompt the second image is very likely `<Picture 2>` (images are passed
in the order first, last; inferred from the node's code).

**"Image to Video" (empty-prompt version):** the same workflow, started with a blank prompt.
Useful for **shot continuity**: use the last frame of your previous clip as the first frame of
the next one. To grab a last frame on macOS: open the `.mp4` in QuickTime Player, go to the end,
**Edit → Copy**, then in Preview **File → New from Clipboard** and save as PNG.

Practice idea: make a still with SDXL (`docs/practice-sdxl.md`, 1344 × 768 is ~16:9), then
animate it with I2V.

---

## 6. Reference to Video (R2V) ⚠️ untested

**What it does:** you give up to 9 reference images (plus up to 3 videos and 3 audio clips),
and H3 makes a *new* shot that keeps a character's identity, outfit, style or voice. For short
drama this is the key tool for keeping the same actor across shots.

**Model:** R2V uses its own diffusion model, `minimax_h3_ref2va_pruned_int8_convrot` (21.0 GB,
downloaded and SHA-256 verified 2026-10-23, decision D14). It has the same format as the T2V model
that already works here, so it is expected to run, but nobody has rendered with it on this Mac
yet. Reference images add work to every sampling step, so expect it to be slower and use more
memory than T2V at the same size. (The R2V turbo LoRA is not downloaded; turbo stays off.)

**Practice steps:**
1. Restart ComfyUI (§0.5), then Templates → **MiniMax H3: Reference to Video**.
2. In this template the nodes are not folded into a subgraph; you see them all. Change:
   - **Load VAE** node showing `..._video_vae_int8_convrot` → `minimax_h3_video_vae_fp16.safetensors`
   - **Float (Duration)**: 5 → **1**; **Resolution Selector**: **0.2 MP**
   - **Boolean (Enable Lightning LoRA)**: keep **false** (that LoRA isn't downloaded)
   - On **MiniMax H3 Reference to Video**: keep `ref_image_size` = **match** (`max` keeps
     references at up to 2048 px, which is slower and heavier)
3. Upload your own pictures into the two **Load Image** nodes. More references: connecting one
   makes the next empty `ref_image_` slot appear on the node.
4. **Prompt tags follow connection order:** `ref_image_0` is `<Picture 1>`, `ref_image_1` is
   `<Picture 2>`, and so on (audio is `<Audio 1>`, videos `<Video 1>`). Delete tags for inputs
   you didn't connect (the sample prompt mentions `<Audio 1>` but has no audio connected). Be
   explicit, e.g. `<Picture 1> is the main character, a woman in a grey coat. Use her face and
   outfit exactly.`
5. The template's note says the `beta` or `normal` scheduler often beats `simple` for
   reference-heavy prompts: a good single-change experiment once a first run works.

---

## 7. The rest (later)

- **Multiframe Reference:** pins images at chosen seconds (e.g. 1.5 s, 3 s, 5 s) using
  *Add Guide for MiniMax H3* nodes. Uses the same ref2va model as §6 (downloaded). Same VAE
  switch; default duration 5 s: shorten it and move the pin times inside the clip.
- **Fun ControlNet Union:** copies a dancer's pose from a video. Needs ref2va plus a ControlNet
  patch (2.3 GB) and two pose-detection models. Not planned until the basic pipeline works.
- **Style embeddings:** 10 tiny files (10.7 MB total, e.g. `minimaxh3_bullet_time`), used by
  writing `embedding:minimaxh3_bullet_time` in a prompt. Optional; a small download that would
  still go through the manifest and needs approval.
- **SDXL:** stills only, see `docs/practice-sdxl.md`.

---

## 8. Keep a record of what works

- **Workflows:** after a result you like, **Workflow → Export** into
  `~/dev/AI_short_drama/workflows/project/` with a descriptive name
  (e.g. `h3_i2v_cafe_test.json`). Don't overwrite `h3_t2v_mps_baseline.json`.
- **Prompts:** save good prompts as text files in `prompts/`.
- **Input images:** copy them into `inputs/`.
- **Notes:** for each run, write down template, size, duration, seed, time and swap peak. These
  numbers decide the Stage 6 budget.
- Ask Claude to commit them; renders stay in `~/AI_renders/` (never in Git).

## 9. Common mistakes

| Symptom | Cause / fix |
|---|---|
| Fails at the very end, error mentions `VAEDecode` or `_int_mm` | int8 video VAE still selected → switch to fp16 VAE |
| Red outline on a loader, "value not in list" | that model isn't downloaded (e.g. the ref2v turbo LoRA) or a filename is misspelled; refresh the browser page after a new download |
| "Load Image" error on a fresh template | the sample image isn't installed → upload your own |
| Picture looks squashed in I2V | aspect ratio doesn't match the image (first frame is stretched) |
| Run takes far longer than the table, Mac sluggish | swap is high: cancel, close apps, restart ComfyUI, use 0.2 MP / shorter duration |
| You pressed Run several times | each press queues another full render; remove extras in the queue panel |
| Two different seeds, nearly identical videos | control after generate was *fixed*; or only the seed changed on a very short clip |

**Never:** launch with `--gpu-only`, install custom nodes, or use `api_` / Cloud / Partner
templates without discussing it first.

## 10. Licensing

H3 weights are under the *MiniMax H3 Community License Agreement*; SDXL under OpenRAIL++. Until
the licensing gate is reviewed, treat every render as **learning material only**: no
monetization, client delivery or public commercial posting.
