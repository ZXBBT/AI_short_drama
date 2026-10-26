#!/usr/bin/env bash
# Standard checks for developers and agents: the offline unit tests and `episode.py validate` for every
# episode. Deterministic: no macOS Vision, no ComfyUI, no rendering, no downloads, no network.
#
#   scripts/check.sh                              # standard checks (run before and after every change)
#   RUN_VISION_INTEGRATION=1 scripts/check.sh     # + the real macOS Vision face check (optional)
#   PY=/path/to/python scripts/check.sh           # another interpreter (default: the ComfyUI venv)
#
# Every check prints its full output; PASS / FAIL comes from its exit code only. Exit 1 if anything failed.
# SKIP: an episode whose only errors are missing local-only references listed in local_only_reason
# (untracked and gitignored by owner decision), and the Vision check when not enabled or not possible here.
set -u -o pipefail
cd "$(dirname "$0")/.." || exit 2
PY="${PY:-$HOME/dev/ComfyUI/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "check.sh: Python interpreter not found: $PY (set PY=...)" >&2
  exit 2
fi

# Reference pictures kept on this Mac only, never in Git (.gitignore, owner decisions 2026-10-24).
# A missing file may be skipped only for the episode and path listed here.
local_only_reason() {  # $1 episode, $2 path -> prints why it is local only; fails if not listed
  case "$1|$2" in
    "Urban_Lifestyle_Commercial|inputs/Urban_Lifestyle_Commercial/ref_can_v1.png")
      echo "product imitating a real beer trademark, local only until the licensing review" ;;
    "_owner_selfie|inputs/_owner_selfie/ref_girl_v1.png")
      echo "third-party reference picture, local only (owner 2026-10-24)" ;;
    "nailong|inputs/nailong/nailong_ref_v1.png")
      echo "third-party character / trademark reference, local only (owner 2026-10-24)" ;;
    *) return 1 ;;
  esac
}

local_only_skip() {  # $1 episode, $2 validate output -> prints the SKIP reason, or fails (= FAIL)
  local ep=$1 line path why reasons="" n=0
  local re='^ERROR: asset [^[:space:]]+: file missing ([^[:space:]]+)$'
  while IFS= read -r line; do
    case "$line" in ERROR:*) ;; *) continue ;; esac
    [[ $line =~ $re ]] || return 1                                     # any other error is real
    path=${BASH_REMATCH[1]}
    why=$(local_only_reason "$ep" "$path") || return 1                 # not in the list
    git ls-files --error-unmatch -- "$path" >/dev/null 2>&1 && return 1  # tracked in Git: must exist
    git check-ignore -q -- "$path" || return 1                         # not gitignored
    reasons+="${reasons:+; }local-only reference missing: $path ($why)"
    n=$((n + 1))
  done <<< "$2"
  [ "$n" -gt 0 ] && echo "$reasons"
}

results=()  # "STATUS|name|reason"
OUT="" RC=0
run() {  # $1 name, then the command; prints its full output, sets OUT and RC
  local name=$1
  shift
  echo
  echo "=== $name"
  OUT=$("$@" 2>&1)
  RC=$?
  [ -n "$OUT" ] && printf '%s\n' "$OUT"
  echo "--- $name: exit $RC"
}

for t in episode brief assemble autopick take_checks; do
  run "test_$t" "$PY" "scripts/test_$t.py"
  if [ "$RC" -eq 0 ]; then results+=("PASS|test_$t|"); else results+=("FAIL|test_$t|exit $RC"); fi
done

for y in episodes/*/episode.yaml; do
  dir=${y%/episode.yaml}
  ep=${dir#episodes/}
  run "validate $ep" "$PY" scripts/episode.py validate "$dir"
  if [ "$RC" -eq 0 ]; then
    results+=("PASS|validate $ep|")
  elif why=$(local_only_skip "$ep" "$OUT"); then
    echo "SKIP validate $ep: $why"
    results+=("SKIP|validate $ep|$why")
  else
    results+=("FAIL|validate $ep|exit $RC")
  fi
done

if [ "${RUN_VISION_INTEGRATION:-}" = "1" ]; then
  run "vision integration" "$PY" scripts/test_vision_integration.py
  case "$RC" in
    0) results+=("PASS|vision integration|") ;;
    77) results+=("SKIP|vision integration|$(printf '%s\n' "$OUT" | sed -n 's/^SKIP: //p' | tail -1)") ;;
    *) results+=("FAIL|vision integration|exit $RC") ;;
  esac
else
  results+=("SKIP|vision integration|not enabled (RUN_VISION_INTEGRATION=1 to run)")
fi

echo
echo "=== Summary"
passed=0 skipped=0 failed=0
for r in "${results[@]}"; do
  IFS='|' read -r status name why <<< "$r"
  printf '%-4s  %-38s %s\n' "$status" "$name" "$why"
  case "$status" in PASS) passed=$((passed + 1)) ;; SKIP) skipped=$((skipped + 1)) ;; *) failed=$((failed + 1)) ;; esac
done
echo "$passed passed, $skipped skipped, $failed failed"
[ "$failed" -eq 0 ]
