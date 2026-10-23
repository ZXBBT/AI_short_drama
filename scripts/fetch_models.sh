#!/bin/zsh
# Download and verify model files listed in a manifest, pinned to one Hugging Face revision.
# Usage: scripts/fetch_models.sh [manifest] [role-prefix]
#   default: models/manifest.tsv, role prefix "required"
#   e.g.     scripts/fetch_models.sh models/manifest.tsv fallback
#
# Each file is downloaded to <name>.part (resumable), its size and SHA-256 are checked against
# the manifest, and only then renamed to its final name. A file that already exists under its
# final name is only size-checked (run scripts/verify_models.sh for a full re-hash).
# Never deletes anything; a mismatching download stays as .part for inspection.

REPO_DIR=${0:A:h:h}
MANIFEST=${1:-$REPO_DIR/models/manifest.tsv}
ROLE=${2:-required}
DEST=${MODELS_DIR:-$HOME/AI_models/comfyui}

HF_REPO=$(sed -n 's/^#repo: *//p' "$MANIFEST")
REV=$(sed -n 's/^#revision: *//p' "$MANIFEST")
[[ -n $HF_REPO && -n $REV ]] || { echo "manifest lacks #repo/#revision lines"; exit 2; }
echo "repo $HF_REPO @ $REV -> $DEST (role: $ROLE*)"

fail=0
while IFS=$'\t' read -r rel size sha role; do
  [[ $rel == \#* || $rel == repo_path || $rel == local_path || $role != $ROLE* ]] && continue
  out=$DEST/$rel
  mkdir -p "${out:h}"
  if [[ -f $out ]]; then
    if [[ $(stat -f%z "$out") == $size ]]; then echo "SKIP (present, size ok) $rel"; continue; fi
    echo "FAIL existing file has wrong size, not touching it: $out"; fail=1; continue
  fi
  echo "GET  $rel ($((size / 1000000)) MB)"
  t0=$SECONDS
  if ! curl -fL --retry 10 --retry-delay 10 --retry-all-errors -C - -sS -o "$out.part" \
      "https://huggingface.co/$HF_REPO/resolve/$REV/$rel"; then
    echo "FAIL download error (partial kept, rerun to resume): $rel"; fail=1; continue
  fi
  got=$(stat -f%z "$out.part")
  if [[ $got != $size ]]; then echo "FAIL size $got != $size: $rel"; fail=1; continue; fi
  hash=$(shasum -a 256 "$out.part" | cut -d' ' -f1)
  if [[ $hash != $sha ]]; then echo "FAIL sha256 mismatch (kept as .part): $rel"; fail=1; continue; fi
  mv "$out.part" "$out"
  echo "OK   $rel sha256 verified ($((SECONDS - t0))s)"
done < "$MANIFEST"

[[ $fail == 0 ]] && echo "ALL DONE" || echo "FINISHED WITH ERRORS"
exit $fail
