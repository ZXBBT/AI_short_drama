# Models

`manifest.tsv` lists every model file the project uses: exact filename, size, expected SHA-256
and why it is needed. The weights themselves live in `~/AI_models/comfyui/` and are never
committed (see `.gitignore`).

A SHA-256 checksum is a fingerprint of a file. After download (Stage 3) each file is hashed
locally and compared with the manifest; a mismatch means a corrupt or different file.

Note: the official docs and the `video_minimax_h3_t2v` template (templates 0.11.89) link the
T2V turbo LoRA from `lightx2v/Minimax-h3-Turbo`; the same filename also exists in
`Comfy-Org/MiniMax-H3`. We use the Comfy-Org copy so every file comes from one pinned repo
revision. Confirmed 2026-10-23: both copies have the identical SHA-256 (`2339acdf…b111e`).

## Scripts
- `scripts/fetch_models.sh [manifest] [role]` — download rows whose role starts with `role`
  (default `required`), pinned to the manifest's `#revision`, verify, then rename from `.part`.
- `scripts/verify_models.sh [manifest]` — read-only full re-hash of every present file.

## Download log
| Date | Files | Result | Record |
|---|---|---|---|
| 2026-10-23 | 5 required H3 files, 44.4 GB | all SHA-256 verified twice; visible in ComfyUI loaders | `verification/2026-10-23_stage3.txt` |
| 2026-10-23 | SDXL practice checkpoint, 6.9 GB | SHA-256 verified | `practice_manifest.tsv` |
