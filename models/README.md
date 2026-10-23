# Models

`manifest.tsv` lists every model file the project uses: exact filename, size, expected SHA-256
and why it is needed. The weights themselves live in `~/AI_models/comfyui/` and are never
committed (see `.gitignore`).

A SHA-256 checksum is a fingerprint of a file. After download (Stage 3) each file is hashed
locally and compared with the manifest; a mismatch means a corrupt or different file.

Note: the official docs link the T2V turbo LoRA from `lightx2v/Minimax-h3-Turbo`; the same
filename also exists in `Comfy-Org/MiniMax-H3`. We use the Comfy-Org copy so every file comes
from one pinned repo revision.
