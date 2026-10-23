#!/bin/zsh
# Read-only: prints a snapshot of the system and toolchain versions.
# Usage: scripts/capture_env.sh > env/snapshots/$(date +%F)_<label>.txt
# Optional: COMFY_DIR (default ~/dev/ComfyUI) to include ComfyUI + venv package versions.

COMFY_DIR=${COMFY_DIR:-$HOME/dev/ComfyUI}

echo "# snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "## system"
sw_vers
echo "arch: $(uname -m)  rosetta: $(sysctl -n sysctl.proc_translated 2>/dev/null)"
echo "cpu: $(sysctl -n machdep.cpu.brand_string)"
echo "ram_bytes: $(sysctl -n hw.memsize)"
echo "xcode_clt: $(pkgutil --pkg-info=com.apple.pkg.CLTools_Executables 2>/dev/null | awk '/version/{print $2}')"

echo "## tools"
for t in git brew python3.13 ffmpeg hf; do
  if command -v $t >/dev/null; then echo "$t: $($t --version 2>&1 | head -1)"; else echo "$t: not installed"; fi
done

echo "## comfyui"
if [ -d "$COMFY_DIR/.git" ]; then
  echo "path: $COMFY_DIR"
  echo "describe: $(git -C "$COMFY_DIR" describe --tags --always --dirty)"
  echo "commit: $(git -C "$COMFY_DIR" rev-parse HEAD)"
else
  echo "not installed at $COMFY_DIR"
fi

echo "## venv packages"
if [ -x "$COMFY_DIR/.venv/bin/python" ]; then
  "$COMFY_DIR/.venv/bin/python" --version
  "$COMFY_DIR/.venv/bin/python" -m pip freeze
  "$COMFY_DIR/.venv/bin/python" -c "import torch; print('torch', torch.__version__, 'mps_available', torch.backends.mps.is_available())"
else
  echo "no venv at $COMFY_DIR/.venv"
fi
