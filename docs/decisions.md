# Decision log

Each entry: what was decided, why, and what would make us revisit it.

## D1 — PyTorch MPS, not MLX (2026-10-23)
- **Why:** project requirement. Community MLX-SDPA workarounds for H3 on Mac are therefore out of scope.
- **Revisit if:** never without explicit owner approval.

## D2 — Manual Git install of ComfyUI, pinned tag, not ComfyUI Desktop (2026-10-23)
- **Why:** reproducibility. Desktop bundles its own Python/PyTorch and self-updates; the latest
  Desktop release verifiable on GitHub (v0.9.4, 2026-05-28) bundles core 0.22.3, older than the
  H3 minimum (0.34.3) and the September MPS fixes. The web UI is identical, so learning transfers.
- **Revisit if:** Desktop ships a pinnable core ≥ the version we use.

## D3 — Python 3.13 (Homebrew `python@3.13`) in a dedicated venv (2026-10-23)
- **Why:** ComfyUI README calls 3.13 "very well supported"; 3.14 may break some dependencies.
  Conda base is left untouched to avoid conda/pip mixing.
- **Alternative considered:** uv-managed standalone Python (no shared Homebrew libs, exact patch
  pin). Owner chose Homebrew, accepting upgrades of shared libs (ca-certificates, readline,
  sqlite, xz). Installed with `HOMEBREW_NO_INSTALL_CLEANUP=1` so old versions were kept.
- **Note:** `brew upgrade` can move python@3.13 to a newer patch release; record it in
  `env/versions.md` if that happens.

## D4 — PyTorch stable 2.14.1, pinned (2026-10-23)
- **Why:** ComfyUI README suggests nightly on Mac, but nightlies are not reproducible.
- **Revisit if:** a needed MPS fix exists only in nightly (record exact nightly build string if so).
- **Known limit:** no `torch._int_mm` on MPS in 2.14.1 → ComfyUI dequantizes int8 weights to fp16
  per layer (saves memory, no int8 speed-up).

## D5 — Official fp16 video VAE instead of the template's int8_convrot VAE (2026-10-23)
- **Why:** `minimax_h3_video_vae_int8_convrot` crashes at VAEDecode on MPS (`aten::_int_mm`);
  fix PR Comfy-Org/ComfyUI#16890 still open. `minimax_h3_video_vae_fp16` is official (same repo).
- **Effect:** +2.4 GB disk; template's VAE loader must be switched to the fp16 file.
- **Revisit if:** #16890 (or equivalent) is merged into the pinned ComfyUI version.

## D6 — Diffusion model: `minimax_h3_fl2va_pruned_int8_convrot` (template default) (2026-10-23)
- **Why:** bf16 pruned (40 GB) leaves too little headroom in 64 GB unified memory; fp8 has no
  compute benefit on MPS; w6a8 needs activation-quant kernels MPS lacks.

## D7 — Text encoder: `nvfp4_awq` first, `int8_convrot` as fallback (2026-10-23)
- **Why:** template default and smallest (15.7 GB), but stock-MPS support is unverified.
  Stage 2 micro-tests decide before the large download.

## D8 — Add a small-model practice step to Stage 2, before H3 downloads (2026-10-23)
- **Why:** learn the ComfyUI UI with seconds-long renders instead of minutes-long H3 renders.

## D9 — Keep ComfyUI's default device policy on MPS; never force the text encoder to GPU (2026-10-23)
- **Measured** (`scripts/mps_quant_check.py`, result GO): ComfyUI v0.42.1 puts text encoders on
  **CPU** (vram_state SHARED) and diffusion model + VAE on **MPS**. MPS has no float8 dtype at all
  (`Undefined type Float8_e4m3fn`), and nvfp4 block scales are float8, so the nvfp4 text encoder
  only works on CPU. int8 ConvRot dequant + fp16 matmul on MPS is correct (rel.err 0.9%).
- **Effect:** prompt encoding runs on CPU (slower, once per prompt). Do not use `--gpu-only`.

## D10 — Keep default attention (`attention_sub_quad`) for now (2026-10-23)
- **Why:** it is ComfyUI's default on this Mac and matched PyTorch SDPA (max diff 6e-5) in tests;
  chunking also limits tensor sizes (cf. INT_MAX issue #15315). `--use-pytorch-cross-attention`
  may be faster; compare only after a working baseline exists (Stage 5).

## D12 — Scripted H3 renders via `scripts/run_h3_t2v.py`, defaults read from the official template (2026-10-23)
- **Why:** every run gets an identical, recorded API graph + timings + memory + output checks in `runs/`.
- The template's turbo switch / frame-count math nodes are replaced by their resolved values
  (turbo off), which is graph-equivalent. UI-loadable equivalent: `workflows/project/h3_t2v_mps_baseline.json`.
- **Observed (Run A, 608×352, 5 frames):** works end-to-end on MPS; system memory peaked ~53 GiB
  with ~11 GiB swap, because the CPU text encoder (15 GB) and MPS diffusion model (20 GB) are
  both resident. Watch swap as length/resolution grow.

## D13 — Baseline render settings: 864×480, 20 steps, turbo off; turbo only for previews (2026-10-23)
- **Why:** 864×480×56 frames (2.3 s) renders in ~9 min with swap < 10 GiB and good quality
  (`docs/stage5-results.md`). Turbo halves sampling time but pushed swap to 24.8 GiB and changes
  the look, so it is not the default.
- **Revisit if:** swap behaviour of turbo is understood/fixed, or longer clips need a different budget.

## D14 — Download the R2V model `minimax_h3_ref2va_pruned_int8_convrot` (2026-10-23)
- **Why:** owner approved. Reference-to-video (and Multiframe Reference / Fun ControlNet) templates
  need ref2va, a separate set of weights from fl2va. Same pruned int8 ConvRot format as the working
  T2V model (D6), so the same MPS path is expected to work; not yet rendered on this Mac.
- Manifest role `r2v`. R2V turbo LoRA not downloaded (turbo stays off, D13).
- **Memory:** two 21 GB diffusion models must not be resident together; restart ComfyUI when
  switching between fl2va and ref2va workflows.

## D15 — Episode pipeline: shots as a dependency graph, versioned recipes, fingerprinted takes (2026-10-23)
- **Why:** see `docs/automation-plan.md` §3–4. Blind last-frame chaining accumulates drift and
  cannot tell which shots a re-render invalidates; explicit typed links + content fingerprints can.
- `scripts/episode.py` builds the same API graphs as the proven paths (offline test: T2V graph
  identical to `stage5_repro_a`; I2V graph matches the owner's UI run). Recipes in `config/recipes/`
  change only by new version. No CFG knob: official H3 graphs use `BasicGuider`.
- Safety: refuses to render while ComfyUI is busy (shared with the owner's UI), stops the batch on
  any failure or swap > 20 GiB, unloads models when switching fl2va <-> ref2va.

## D16 — PyTorch attention for new work: recipe `h3_base_v2` (owner-approved 2026-10-24)
- **Why:** quality track test QA vs Q2H (same graph and seed, 480x864x73): same shot and face quality,
  sampling 8 % faster, peak memory ~4 GB lower, swap peak 3.6 vs 9.4 GiB. Supersedes D10 for new work.
- Exact pixels differ (different rounding), so the attention mode is part of the recipe
  (`attention: pytorch`) and of the take fingerprint (only when not ComfyUI's default, so all
  `h3_base_v1` fingerprints and finished takes stay valid).
- `scripts/launch_comfyui.sh` starts PyTorch attention by default; `COMFY_ATTENTION=default` gives
  ComfyUI's own default (sub-quadratic) for v1 episodes. `pipeline.py` starts ComfyUI in the
  episode's mode; `episode.py render` refuses if the running ComfyUI is in the wrong mode.
- Started without a Terminal, ComfyUI often ignores Ctrl+C (SIGINT); the pipeline falls back to
  SIGTERM after 10 s (queue is always empty at that point).

## D11 — Launch only via `scripts/launch_comfyui.sh` (2026-10-23)
- localhost only, `--disable-all-custom-nodes`, models from `config/extra_model_paths.yaml`,
  output to `~/AI_renders/comfyui`, wrapped in `caffeinate -i`.
- The template library also lists "Comfy Cloud" / "partner" MiniMax nodes and `api_*` templates;
  those send work to paid remote services and are not used.

## D17 — Image model: Qwen-Image 2.1 (owner decision 2026-10-25; downloaded 2026-10-25, MPS-tested 2026-10-26)
- **Chosen over** Qwen-Image-Edit-2511 (Apache 2.0). Licence read at the source
  (huggingface.co/Qwen/Qwen-Image-2.1 `LICENSE`, sha256 8dc973f0…, release date 2026-09-20): Qwen RESEARCH
  LICENSE AGREEMENT — use only for "Non-Commercial" = "research or evaluation purposes only"; commercial use
  needs a separate licence from Qwen (model-business@notice.qwencloud.com). Pictures made with it are treated
  as **non-commercial**: they must be tagged as such and replaced (or licensed) before any monetised video.
- Official ComfyUI files (Comfy-Org/Qwen-Image-2.1, listed 2026-10-25; templates in
  comfyui-workflow-templates-json 0.1.115): text-to-image = `qwen_image_2.1_int8_convrot` 7.26 GB +
  `qwen3vl_8b_int8_convrot` 9.35 GB + prompt enhancer `qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot`
  9.47 GB + `qwen_image_2.1_vae_bf16` 0.68 GB = 26.8 GB; image edit adds `…pe_i2i.int8_convrot` 9.47 GB;
  background removal needs no extra file; turbo variant +7.26 GB.
- Downloaded (owner: "everything incl. turbo", 43.5 GB, `models/manifest_qwen_image_2.1.tsv`, rev 0217efd).
- MPS test 2026-10-26 (docs/qwen-image-results.md): every mode works. Two settings are required on MPS:
  1. **Edits: start ComfyUI with `--bf16-text-enc`.** The 8B text encoder runs on the CPU in fp16 and
     overflowed to NaN when it read a reference picture (all-black edits, no error). bf16 keeps fp32's range.
     Text-to-image is unaffected. H3 renders keep the normal launch (flag not tested with H3's encoder).
  2. **Edits: `resolution` 0** (the template's value: references keep their size). 1024 upscaled a
     480x864 reference and gave embossed, sketch-like faces; two references at 1024 ran out of memory.
  `scripts/qwen_image.py` records the ComfyUI launch flags and marks blank pictures as failed checks.

## D18 — Higher resolution: SeedVR2 as an optional upscale step (owner request 2026-10-26)
- Owner approved the download ("3B + 7B sharp"): `models/manifest_seedvr2.tsv` (Apache 2.0, Comfy-Org/SeedVR2
  rev df48879). Graph = official template `utility_seedvr2_3b_int8_upscale_video` (ComfyUI core nodes only).
- Tested 2026-10-26 (docs/seedvr2-results.md): x2 works on MPS at our sizes (480x864 → 960x1728,
  864x480 → 1728x960) in ~9-10 min per 4 s shot, 41-52 GiB peak. **Default: 7B sharp + `lab` colour**
  (3B adds sparkle artefacts; the template's colour `none` warms the picture). Deviation from the template:
  colour correction only.
- Workflow: optional, after picks are confirmed and before assembly (`upscale: 7b_sharp` per shot in
  cut.yaml, `scripts/upscale.py --cut`); never instead of fixing structure.
