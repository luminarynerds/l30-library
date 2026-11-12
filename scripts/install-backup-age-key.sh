#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# L30 Library System - Wire age public key(s) into the backup pipeline
#
# One-shot installer. Given one or more age public recipients on the command
# line, this:
#   1. Validates each recipient looks like an age public key
#   2. Ensures `age` is installed
#   3. Writes the recipients to /etc/l30/backup-recipients
#   4. Appends BACKUP_AGE_RECIPIENTS_FILE to /opt/l30/.env.prod (idempotent)
#   5. Runs an encrypt smoke test
#
# The matching SECRET key must NEVER be placed on this host. Keep it in the
# team password manager + a sealed cold-storage copy.
#
# Usage:
#   sudo ./install-backup-age-key.sh age1xxxxxxxxx... [age1yyyyy...]
#
# Idempotent: re-running with the same recipients is a no-op. Re-running with
# different recipients OVERWRITES the recipients file (additive recipient
# changes belong in a manual edit; this script is for fresh setup).

set -euo pipefail

ENV_FILE="/opt/l30/.env.prod"
RECIPIENTS_DIR="/etc/l30"
RECIPIENTS_FILE="$RECIPIENTS_DIR/backup-recipients"
ENV_VAR_NAME="BACKUP_AGE_RECIPIENTS_FILE"

die() { echo "ERROR: $*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "Must run as root"
[ $# -ge 1 ]        || die "At least one age recipient is required (e.g. age1xxxx...)"

for r in "$@"; do
    [[ "$r" =~ ^age1[a-z0-9]{50,}$ ]] \
        || die "Recipient does not look like an age public key: $r"
done

if ! command -v age >/dev/null 2>&1; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "==> Installing age via apt"
        apt-get update -qq && apt-get install -y age
    else
        die "\`age\` is not installed and apt-get is unavailable. Install age manually: https://github.com/FiloSottile/age"
    fi
fi

echo "==> Writing $RECIPIENTS_FILE"
install -d -m 0755 -o root -g root "$RECIPIENTS_DIR"
# Recipients are PUBLIC keys, not secrets — 0644 is correct.
{ for r in "$@"; do echo "$r"; done; } > "$RECIPIENTS_FILE"
chmod 0644 "$RECIPIENTS_FILE"
chown root:root "$RECIPIENTS_FILE"

echo "==> Wiring $ENV_VAR_NAME into $ENV_FILE"
if [ ! -f "$ENV_FILE" ]; then
    die "$ENV_FILE not found. Run setup.sh first to generate it."
fi

# Idempotent: replace any existing line, otherwise append.
if grep -qE "^[#[:space:]]*${ENV_VAR_NAME}=" "$ENV_FILE"; then
    # Use a temp file so we don't corrupt .env.prod on a failed sed.
    TMP=$(mktemp)
    sed -E "s|^[#[:space:]]*${ENV_VAR_NAME}=.*|${ENV_VAR_NAME}=${RECIPIENTS_FILE}|" "$ENV_FILE" > "$TMP"
    install -m 0600 -o root -g root "$TMP" "$ENV_FILE"
    rm -f "$TMP"
    echo "    (updated existing entry)"
else
    {
        echo ""
        echo "# --- Backup at-rest encryption (age) ---"
        echo "${ENV_VAR_NAME}=${RECIPIENTS_FILE}"
    } >> "$ENV_FILE"
    echo "    (appended new entry)"
fi

echo "==> Smoke test: encrypting a test payload"
TEST_OUT=$(mktemp)
trap 'rm -f "$TEST_OUT"' EXIT
echo "l30-age-smoke-test" | age -R "$RECIPIENTS_FILE" > "$TEST_OUT"
if ! head -c 21 "$TEST_OUT" | grep -q '^age-encryption.org/v1$'; then
    die "Smoke test failed: output is not a valid age archive"
fi
echo "    OK ($(wc -c < "$TEST_OUT") bytes, age framing verified)"

cat <<EOF

=========================================================================
DONE. age recipients wired into the backup pipeline.

Verify end-to-end with a real backup run:

    sudo /opt/l30/scripts/automated-backup.sh
    ls -la /opt/l30/backups/daily/ | tail -3

You should see a fresh l30_backup_*.sql.gz.age (note the .age suffix).
The backup log will report 'encrypted=1'.

Reminder: the matching SECRET key (l30-backup.key) must NEVER live on
this host. Restores happen on a separate machine that holds the identity.
=========================================================================
EOF
