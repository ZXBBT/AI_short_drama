# Version log

The single source of truth for "what exactly was installed". Update it whenever anything
changes, together with a fresh snapshot (`scripts/capture_env.sh`).

## Pinned targets
| Component | Target | Decision |
|---|---|---|
| ComfyUI | tag `v0.42.1` = commit `63be2f9b82ad0dac88a7ceaa28a9cf3154125a18` | D2 |
| Python | 3.13 (Homebrew `python@3.13`), venv at `~/dev/ComfyUI/.venv` | D3 |
| PyTorch | 2.14.1 (stable) | D4 |
| torchvision | 0.29.1 (matches torch 2.14.1); torchaudio not installed (unused by ComfyUI v0.42.1) | D4 |
| Python packages | exact list in `env/comfyui-venv-freeze.txt` | — |
| H3 model repo | `Comfy-Org/MiniMax-H3` @ `e5eb578a89295337b8ff433a035929ce0279e0b6` | `models/manifest.tsv` |

Reinstall the venv exactly: `.venv/bin/python -m pip install -r ~/dev/AI_short_drama/env/comfyui-venv-freeze.txt`

## Installed (filled in at each stage)
| Date | Stage | Component | Version | Notes |
|---|---|---|---|---|
| 2026-10-23 | 0 | macOS | 26.6.2 (25G83) | pre-existing |
| 2026-10-23 | 0 | Xcode CLT | 26.3 | pre-existing |
| 2026-10-23 | 0 | Git | 2.50.1 (Apple Git-155) | pre-existing |
| 2026-10-23 | 0 | Homebrew | 5.1.12 | pre-existing |
| 2026-10-23 | 2 | python@3.13 (Homebrew) | 3.13.17 | installed with `HOMEBREW_NO_INSTALL_CLEANUP=1`; `python3` still 3.14.5 |
| 2026-10-23 | 2 | Homebrew deps upgraded | ca-certificates 2026-10-20, readline 8.3.6, sqlite 3.54.1, xz 5.8.4 | side effect of python@3.13; old versions kept; openssl@3 unchanged (3.6.2) |
| 2026-10-23 | 2 | ComfyUI | v0.42.1 (`63be2f9`) | git clone at `~/dev/ComfyUI`, detached at tag |
| 2026-10-23 | 2 | venv | Python 3.13.17, pip 26.2.2 | `~/dev/ComfyUI/.venv` |
| 2026-10-23 | 2 | torch / torchvision | 2.14.1 / 0.29.1 | MPS available; GPU working-set cap 51.8 GiB |
| 2026-10-23 | 2 | comfy-kitchen / comfy-aimdo | 0.2.39 / 0.5.6 | pinned by ComfyUI requirements; aimdo inactive on macOS |
| 2026-10-23 | 2 | frontend / templates | 1.55.18 / 0.11.89 | pinned by ComfyUI requirements |
| 2026-10-23 | 3 | H3 model files | Comfy-Org/MiniMax-H3 @ `e5eb578a` | 5 required files from `models/manifest.tsv`, SHA-256 verified |
