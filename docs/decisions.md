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

## D11 — Launch only via `scripts/launch_comfyui.sh` (2026-10-23)
- localhost only, `--disable-all-custom-nodes`, models from `config/extra_model_paths.yaml`,
  output to `~/AI_renders/comfyui`, wrapped in `caffeinate -i`.
- The template library also lists "Comfy Cloud" / "partner" MiniMax nodes and `api_*` templates;
  those send work to paid remote services and are not used.
