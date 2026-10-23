#!/bin/zsh
# Read-only: re-hash every model file from a manifest that exists locally and compare SHA-256.
# Usage: scripts/verify_models.sh [manifest]   (default models/manifest.tsv)

REPO_DIR=${0:A:h:h}
MANIFEST=${1:-$REPO_DIR/models/manifest.tsv}
DEST=${MODELS_DIR:-$HOME/AI_models/comfyui}

fail=0
while IFS=$'\t' read -r rel size sha role; do
  [[ $rel == \#* || $rel == repo_path || $rel == local_path ]] && continue
  out=$DEST/$rel
  if [[ ! -f $out ]]; then echo "absent   $rel ($role)"; continue; fi
  hash=$(shasum -a 256 "$out" | cut -d' ' -f1)
  if [[ $hash == $sha ]]; then echo "OK       $rel"; else echo "MISMATCH $rel"; fail=1; fi
done < "$MANIFEST"
exit $fail
