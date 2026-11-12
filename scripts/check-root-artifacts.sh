#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

WHITELIST_FILE=".root-artifact-whitelist"
ROOT_PATTERN='(SUMMARY|VERIFICATION|ANALYSIS|REPORT|DELIVERABLE|CHECKLIST)'
HANDOFF_PATTERN='(^|/)(\.claude/|CLAUDE\.md$|.*(IMPLEMENTATION_SUMMARY|ARCHITECTURE_DIAGRAM|CONSOLIDATION_CHANGES|START_HERE)\.(md|txt)$|setup-claude-skills\.sh$)'

mapfile -t matches < <(find . -maxdepth 1 -type f \
  | sed 's|^\./||' \
  | rg -i "$ROOT_PATTERN" || true)

unexpected=()
for file in "${matches[@]}"; do
  [[ -z "$file" ]] && continue
  if [[ ! -f "$WHITELIST_FILE" ]] || ! rg -qx --fixed-strings "$file" "$WHITELIST_FILE"; then
    unexpected+=("$file")
  fi
done

mapfile -t handoffs < <(
  git ls-files \
    | while IFS= read -r file; do
        [[ -e "$file" ]] && printf '%s\n' "$file"
      done \
    | rg -i "$HANDOFF_PATTERN" || true
)
unexpected+=("${handoffs[@]}")

if ((${#unexpected[@]} > 0)); then
  echo "Repository handoff or artifact files detected:"
  printf ' - %s\n' "${unexpected[@]}"
  echo
  echo "Keep durable docs under docs/. Do not commit agent configuration, task handoffs, or generated status reports."
  exit 1
fi

echo "Repository artifact hygiene: clean."
