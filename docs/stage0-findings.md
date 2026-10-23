# Stage 0 — System & compatibility audit (2026-10-23)

Read-only. Nothing installed or downloaded.

## System
| Item | Value |
|---|---|
| Machine | MacBook Pro, Apple M5 Max, 6P+12E CPU, 40-core GPU, Metal 4, 64 GB |
| OS | macOS 26.6.2 (25G83), arm64, native shell (not Rosetta) |
| Disk | internal APFS SSD, 1.3 TB free |
| iCloud | Desktop & Documents not synced; `~/dev` local |
| Tools | Xcode CLT 26.3, Git 2.50.1, Homebrew 5.1.12, brew Python 3.14.5, Miniconda (base 3.13.12, auto-activate off) |
| Missing | ffmpeg, git-lfs, hf CLI, Python 3.13 outside conda |
| Backups | Time Machine not configured |
| Power | `sleep 1` on AC → use `caffeinate -i` during long renders |

## Current upstream versions (checked 2026-10-23)
- ComfyUI v0.42.1 (2026-10-19). H3 templates need ≥ 0.34.3; FastH3 ≥ 0.36.0.
- PyTorch 2.14.1 stable (macOS arm64 wheels for cp310–cp314).
- comfy-kitchen 0.2.40 (pure Python; eager backend lists `mps` as a supported device).

## H3 on MPS — format by format
`torch._int_mm` is not implemented for MPS in PyTorch 2.14.1 (ComfyUI PR #16808 closed unmerged
after confirming this). ComfyUI v0.42.1 sets `supports_int8_compute()` = False on MPS and
dequantizes int8 weights per layer to fp16 (PRs #16130, #16285 merged).

| Component | File | Status on MPS | Decision |
|---|---|---|---|
| Diffusion | `minimax_h3_fl2va_pruned_int8_convrot` 20.97 GB | expected to work via dequant fallback; unverified locally | keep (D6) |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq` 15.69 GB | unverified on stock ComfyUI | test first; fallback int8_convrot 27.14 GB (D7) |
| Video VAE | `minimax_h3_video_vae_int8_convrot` | crashes at VAEDecode (PR #16890 open) | use `minimax_h3_video_vae_fp16` 5.21 GB (D5) |
| Audio VAE | `minimax_h3_audio_vae_fp32` 0.61 GB | fp32, no issue expected | keep |
| Turbo LoRA | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16` 1.96 GB | required by template model scan | keep |

Minimum download ≈ 44.4 GB (+27 GB if text-encoder fallback is needed).

## Open risks
1. Black video / NaN audio / `INT_MAX` on MPS (ComfyUI #15315) — closed by reporter using
   workarounds incl. MLX SDPA; not confirmed fixed in core. Start with low-res, short clips.
2. MPS out-of-memory while dequantizing INT8 ConvRot weights (ComfyUI #17264, open).
3. nvfp4 text encoder untested on stock MPS.
4. Speed unknown; dequant-on-the-fly gives no int8 speed-up.
5. Community fixes (`ComfyUI-AppleSilicon-FP8` custom node, MLX) conflict with project rules.
6. Weights license: `minimax-h3-community-license-agreement` (custom) → licensing gate.

## Sources
- https://huggingface.co/Comfy-Org/MiniMax-H3 (revision e5eb578a…, API file listing)
- https://docs.comfy.org/tutorials/video/minimax/minimax-h3-native
- https://docs.comfy.org/tutorials/video/minimax/minimax-h3-fastvideo
- https://github.com/Comfy-Org/ComfyUI (README, v0.42.1 `comfy/model_management.py`, `comfy/ops.py`)
- https://github.com/Comfy-Org/comfy-kitchen (README backend matrix, eager backend source)
- ComfyUI issues/PRs: #15315, #16130, #16284, #16285, #16808, #16890, #17264
- https://github.com/MiniMax-AI/MiniMax-H3/issues/56
- https://huggingface.co/Comfy-Org/MiniMax-H3/discussions/24
