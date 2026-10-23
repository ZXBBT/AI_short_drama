# Stage 5 — Reproducibility and scaling on MPS (2026-10-23)

All runs: ComfyUI v0.42.1, torch 2.14.1 (MPS), default attention (`attention_sub_quad`),
template prompt, seed 757358688076805, sampler `res_multistep` / scheduler `simple`, fp16 video
VAE (D5), cache cleared before each Stage 5 run. Full records in `runs/2026-10-23/`.

| Run | Size | Frames (s) | Steps | Text enc s | Sampling s | Video decode s | Total s | Mem peak GiB | Swap peak GiB | Black | Audio finite |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stage4_a | 608×352 | 5 (0.21) | 20 | 30.3 | 77.3 | 9.5 | 123 | 52.9 | 11.2 | 0 | ✅ |
| stage5_repro_a | 608×352 | 5 (0.21) | 20 | 28.1 | 71.5 | 4.1 | 110 | 52.4 | 6.4 | 0 | ✅ |
| stage5_b | 608×352 | 22 (0.92) | 20 | 28.8 | 96.7 | 3.4 | 139 | 52.3 | 6.8 | 0 | ✅ |
| stage5_c | 608×352 | 56 (2.33) | 20 | 28.8 | 222.3 | 12.3 | 272 | 53.2 | 8.7 | 0 | ✅ |
| stage5_d | 864×480 | 56 (2.33) | 20 | 28.6 | 450.4 | 33.6 | 522 | 57.8 | 9.8 | 0 | ✅ |
| stage5_e | 864×480 | 56 (2.33) | 8 turbo | 29.4 | 213.2 | 31.4 | 280 | 58.3 | **24.8** | 0 | ✅ |

Sampling times include loading the diffusion model to MPS (~15–30 s).

## Findings
1. **Reproducible:** `stage5_repro_a` vs `stage4_a` — decoded video frames and audio samples
   identical (max diff 0), after clearing ComfyUI's cache. Same seed + same graph + same
   environment ⇒ same output on this Mac.
2. **Scaling:** sampling grows roughly linearly with frames at 608×352 (≈4 s/frame-step-batch
   beyond fixed overhead) and ~2× when pixels double (608×352 → 864×480). Text encoding is a
   constant ~29 s per prompt (CPU).
3. **Memory:** peak is dominated by resident models (~52 GiB at any size so far); activations add
   a few GiB at 864×480×56. Swap 6–11 GiB in normal runs.
4. **Turbo (8-step LoRA):** 2.1× faster sampling, same composition, brighter / more saturated /
   slightly more CG look. **Swap peaked at 24.8 GiB**, above the 20 GiB stop rule → ladder stopped;
   the planned PyTorch-attention comparison was **not run**.
5. Output quality at 864×480×56: the 4-shot storyboard in the prompt is followed with real cuts.

## Not yet known
- Clips longer than 2.3 s, resolutions above 864×480, PyTorch attention speed.
- Reproducibility after a reboot / across ComfyUI or PyTorch upgrades (expected to change).
