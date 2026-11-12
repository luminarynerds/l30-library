#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -eu
# Substitute domain variable in nginx config
# Only substitute ${DOMAIN} -- leave nginx's own $variables untouched
DOMAIN="${DOMAIN:-localhost}"
export DOMAIN
envsubst '${DOMAIN}' < /etc/nginx/nginx.conf > /tmp/nginx-rendered.conf
mv /tmp/nginx-rendered.conf /etc/nginx/nginx.conf
echo "Configured nginx for domain: $DOMAIN"

CONFIG_FILE="${CONFIG_FILE:-/etc/nginx/nginx.conf}"

echo "Starting nginx with configuration: $CONFIG_FILE"

# Wait for backend and frontend to be reachable before starting nginx
# This ensures Docker DNS is ready and services are initialized
echo "Waiting for backend and frontend services to be reachable..."
max_attempts=60
attempt=0
wait_time=1

while [ $attempt -lt $max_attempts ]; do
  backend_ready=0
  frontend_ready=0

  # Test backend connectivity (port + HTTP health check)
  if nc -z l30-backend 8000 2>/dev/null; then
    if curl -sf --max-time 2 -H "Host: localhost" http://l30-backend:8000/health >/dev/null 2>&1; then
      backend_ready=1
    fi
  fi

  # Test frontend connectivity (port + HTTP health check)
  if nc -z frontend 80 2>/dev/null; then
    if curl -sf --max-time 2 http://frontend:80/ >/dev/null 2>&1; then
      frontend_ready=1
    fi
  fi

  if [ $backend_ready -eq 1 ] && [ $frontend_ready -eq 1 ]; then
    echo "✓ Both backend and frontend are ready!"
    break
  fi

  attempt=$((attempt + 1))
  status="Backend=$([ $backend_ready -eq 1 ] && echo '✓' || echo '✗') Frontend=$([ $frontend_ready -eq 1 ] && echo '✓' || echo '✗')"
  echo "Attempt $attempt/$max_attempts: $status (waiting ${wait_time}s before retry...)"
  sleep $wait_time

  # Exponential backoff: increase wait time slightly, cap at 3 seconds
  if [ $wait_time -lt 3 ]; then
    wait_time=$((wait_time + 1))
  fi
done

if [ $attempt -eq $max_attempts ]; then
  echo "⚠ Warning: Not all services became reachable within ${max_attempts} seconds"
  echo "⚠ Starting nginx anyway - services may still be initializing"
  echo "⚠ Check service logs if requests fail"
fi

# Remove stdout symlinks so logs write to real files (shared volume)
rm -f /var/log/nginx/access.log /var/log/nginx/error.log
touch /var/log/nginx/access.log /var/log/nginx/error.log
echo "Starting nginx..."
exec nginx -g "daemon off;" -c "$CONFIG_FILE"
