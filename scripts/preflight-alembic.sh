#!/usr/bin/env bash
# Preflight gate: refuse to proceed if alembic has >1 head.
# L30 main routinely ships with multi-head migrations; merging without
# a mergepoint causes "relation exists" or "table missing" on backend startup.
set -euo pipefail

heads=$(docker exec l30-backend alembic heads 2>/dev/null | grep -v "^$" | wc -l | tr -d " ")

if [[ "$heads" -le 1 ]]; then
  echo "alembic preflight OK (heads=$heads)"
  exit 0
fi

echo "alembic preflight FAIL: $heads heads detected" >&2
echo >&2
docker exec l30-backend alembic heads >&2
echo >&2
echo "Resolve with a merge revision:" >&2
echo "  docker exec l30-backend alembic merge -m 'merge heads' <rev1> <rev2>" >&2
exit 1
