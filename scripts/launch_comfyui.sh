#!/bin/zsh
# Start the pinned ComfyUI with this project's settings. Stop it with Ctrl+C.
#   - localhost only (not reachable from other devices on the network)
#   - models from ~/AI_models/comfyui, renders to ~/AI_renders/comfyui
#   - no custom nodes (official core nodes only)
#   - caffeinate -i keeps the Mac from idle-sleeping while ComfyUI runs
# Extra ComfyUI flags can be appended, e.g. scripts/launch_comfyui.sh --port 8189
# Attention: PyTorch's by default (D16: same picture, ~8% faster, ~4 GB less memory than ComfyUI's
# sub-quadratic default). COMFY_ATTENTION=default starts ComfyUI with its own default instead
# (needed for episodes whose recipe has no `attention:` key, e.g. h3_base_v1).

REPO=${0:A:h:h}
COMFY_DIR=${COMFY_DIR:-$HOME/dev/ComfyUI}
OUT_DIR=$HOME/AI_renders/comfyui

ATTENTION=${COMFY_ATTENTION:-pytorch}
ATTN_FLAG=()
case $ATTENTION in
  pytorch) ATTN_FLAG=(--use-pytorch-cross-attention) ;;
  default) ;;
  *) echo "COMFY_ATTENTION must be pytorch or default"; exit 2 ;;
esac

mkdir -p "$OUT_DIR"
cd "$COMFY_DIR" || exit 1
echo "ComfyUI $(git describe --tags --always --dirty) at $COMFY_DIR"
echo "Attention: $ATTENTION"
echo "Open http://127.0.0.1:8188 once it says 'To see the GUI go to'"

exec caffeinate -i .venv/bin/python main.py \
  --listen 127.0.0.1 \
  --port 8188 \
  --extra-model-paths-config "$REPO/config/extra_model_paths.yaml" \
  --output-directory "$OUT_DIR" \
  --disable-all-custom-nodes \
  "${ATTN_FLAG[@]}" \
  "$@"
