# Version log

The single source of truth for "what exactly was installed". Update it whenever anything
changes, together with a fresh snapshot (`scripts/capture_env.sh`).

## Pinned targets (decided, not yet installed)
| Component | Target | Decision |
|---|---|---|
| ComfyUI | tag `v0.42.1` | D2 |
| Python | 3.13 (Homebrew `python@3.13`), venv at `~/dev/ComfyUI/.venv` | D3 |
| PyTorch | 2.14.1 (stable) | D4 |
| torchvision | matching 2.14.1 release (0.29.1) | D4 |
| H3 model repo | `Comfy-Org/MiniMax-H3` @ `e5eb578a89295337b8ff433a035929ce0279e0b6` | `models/manifest.tsv` |

## Installed (filled in at each stage)
| Date | Stage | Component | Version | Notes |
|---|---|---|---|---|
| 2026-10-23 | 0 | macOS | 26.6.2 (25G83) | pre-existing |
| 2026-10-23 | 0 | Xcode CLT | 26.3 | pre-existing |
| 2026-10-23 | 0 | Git | 2.50.1 (Apple Git-155) | pre-existing |
| 2026-10-23 | 0 | Homebrew | 5.1.12 | pre-existing |
