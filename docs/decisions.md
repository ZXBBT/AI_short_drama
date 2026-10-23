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
