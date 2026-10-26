#!/bin/zsh
# Install MiniMax's official `h3-prompt-writing` skill as a Claude Code project skill
# (.claude/skills/h3-prompt-writing/), pinned to one commit of github.com/MiniMax-AI/MiniMax-H3 and
# checked file by file with SHA-256 (same idea as fetch_models.sh).
#
# Why only this skill: the other 8 skills in that repo require the MiniMax Hub agent (cloud canvas and
# hub_* tools) and partly paid services (Seedance, ElevenLabs); they are not portable to this local setup.
# The repo has no licence file, so the skill files are not committed to Git (see .gitignore) — this
# script is, so anyone can reinstall exactly the same files. Review: docs/third_party.md.
#
#   scripts/fetch_h3_skills.sh
set -euo pipefail
REPO=${0:A:h:h}
COMMIT=d21241f0a4b3acbb34c97dae47fa417b7065e438
SRC="https://raw.githubusercontent.com/MiniMax-AI/MiniMax-H3/$COMMIT/skills/h3-prompt-writing"
DEST="$REPO/.claude/skills/h3-prompt-writing"
FILES=(
  "a7000443588ca3f145e3b3fd8900f14e0325dc460bd811268fac89a9dc8e56d0  SKILL.md"
  "2cfebc096a6e08370f288d468d90b60f7f9bcb938f94bf090816e910e48e75fc  references/base-en.txt"
  "1e574f356716ad55612247ffb7bbccbcdb484ad96599d63c7dca1af186b1fab7  references/ref-en.txt"
  "7770c9d784b7251ab882ee29a738219a3f01811e57ba7fc7822fa83eb8438c1a  agents/openai.yaml"
)
mkdir -p "$DEST/references" "$DEST/agents"
for entry in "${FILES[@]}"; do
  sha=${entry%%  *}; rel=${entry#*  }
  curl -fsSL "$SRC/$rel" -o "$DEST/$rel.part"
  got=$(shasum -a 256 "$DEST/$rel.part" | cut -d' ' -f1)
  if [[ $got != $sha ]]; then
    echo "MISMATCH $rel (got $got)"; exit 1
  fi
  mv "$DEST/$rel.part" "$DEST/$rel"
  echo "OK   $rel"
done
echo "installed h3-prompt-writing @ ${COMMIT:0:7} -> ${DEST#$REPO/}"
