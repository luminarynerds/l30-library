#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e

SECRETS_FILE=/secrets/.env.generated

if [ -f "$SECRETS_FILE" ]; then
    echo "Secrets already exist at $SECRETS_FILE — skipping generation"
    exit 0
fi

echo "Generating secrets..."

SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

cat > "$SECRETS_FILE" << EOF
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
REDIS_PASSWORD=${REDIS_PASSWORD}
FERNET_KEY=${FERNET_KEY}
DATABASE_URL=postgresql+asyncpg://l30:${POSTGRES_PASSWORD}@database:5432/l30
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
EOF

printf '%s' "$POSTGRES_PASSWORD" > /secrets/db_password
printf '%s' "$REDIS_PASSWORD" > /secrets/redis_password

chmod 600 "$SECRETS_FILE" /secrets/db_password /secrets/redis_password

echo "Secrets written to $SECRETS_FILE"
