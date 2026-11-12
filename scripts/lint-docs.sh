#!/usr/bin/env bash
# Lint script for docs/staff-training/. Greps for the issues the writing
# standards in the design spec call out. Non-zero exit on any finding.
#
# Usage: scripts/lint-docs.sh [path]
# Defaults to docs/staff-training if no path given.

set -euo pipefail

ROOT="${1:-docs/staff-training}"

if [[ ! -d "$ROOT" ]]; then
    echo "lint-docs: directory not found: $ROOT" >&2
    exit 2
fi

EXIT=0

# 1. Em dashes (we use double hyphens "--" instead).
if grep -rn --include='*.md' -P '\xe2\x80\x94' "$ROOT" 2>/dev/null; then
    echo "lint-docs: em dashes found (use -- instead)" >&2
    EXIT=1
fi

# 2. Banned words.
for word in 'click here' 'simply' 'just ' 'obviously'; do
    if grep -rni --include='*.md' -F "$word" "$ROOT" 2>/dev/null; then
        echo "lint-docs: banned phrase '$word' found" >&2
        EXIT=1
    fi
done

# 3. Leftover TODO/FIXME.
if grep -rn --include='*.md' -E '\b(TODO|FIXME|XXX|TBD)\b' "$ROOT" 2>/dev/null; then
    echo "lint-docs: leftover TODO/FIXME/XXX/TBD" >&2
    EXIT=1
fi

# 4. Missing frontmatter. Every .md must start with '---' on line 1.
# Exception: _templates/ and _assets/.
while IFS= read -r -d '' file; do
    if [[ "$file" == */_templates/* || "$file" == */_assets/* ]]; then
        continue
    fi
    first_line=$(head -n1 "$file")
    if [[ "$first_line" != "---" ]]; then
        echo "lint-docs: missing frontmatter: $file" >&2
        EXIT=1
    fi
done < <(find "$ROOT" -name '*.md' -print0)

# 5. Broken relative links (rough: anything that links to ./x.md or ../x.md
# where the target file doesn't exist). Skip http(s) and anchors.
while IFS= read -r -d '' file; do
    dir=$(dirname "$file")
    # Extract markdown link targets that look like relative paths.
    grep -oE '\]\([^)]+\)' "$file" 2>/dev/null \
        | sed -E 's/^\]\(//; s/\)$//' \
        | grep -v -E '^(https?:|mailto:|#|/)' \
        | while IFS= read -r target; do
            # Strip anchor fragment.
            target_path="${target%%#*}"
            [[ -z "$target_path" ]] && continue
            if [[ ! -e "$dir/$target_path" ]]; then
                echo "lint-docs: broken link in $file: $target" >&2
                EXIT=1
            fi
        done
done < <(find "$ROOT" -name '*.md' -print0)

# 6. Unfilled tokens. Every {{...}} in a published doc is a bug.
# (Templates and the README's explanation block are exceptions.)
while IFS= read -r -d '' file; do
    if [[ "$file" == */_templates/* ]]; then
        continue
    fi
    # Allow {{tokens}} only in fenced code blocks or inline code.
    # Quick heuristic: warn but don't fail. Future work: parse out code blocks.
    if grep -n '{{[a-z_]\+}}' "$file" 2>/dev/null | grep -v '`{{' >/dev/null; then
        echo "lint-docs: unfilled token in $file (use backticks if illustrative)" >&2
        # Warning only -- don't bump EXIT.
    fi
done < <(find "$ROOT" -name '*.md' -print0)

if [[ "$EXIT" -eq 0 ]]; then
    echo "lint-docs: clean"
fi

exit $EXIT
