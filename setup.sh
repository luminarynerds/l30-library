#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# =============================================================================
# L30 Library System - Setup Script
# =============================================================================
# Generates secrets and configures .env for a new L30 installation.
# Run once before starting the application.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}L30 Library System - Setup${NC}"
echo "==========================================="
echo ""

# --- Parse flags (non-interactive install support, see INSTALL.md) ---
DOMAIN=""
LIBRARY_NAME=""
FROM_EMAIL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --domain)
            DOMAIN="${2:-}"
            shift 2
            ;;
        --email)
            FROM_EMAIL="${2:-}"
            shift 2
            ;;
        --name)
            LIBRARY_NAME="${2:-}"
            shift 2
            ;;
        *)
            echo -e "${RED}Error: unknown argument '$1'${NC}"
            echo "Usage: ./setup.sh [--domain <domain>] [--email <email>] [--name <library name>]"
            exit 1
            ;;
    esac
done

# --- Check prerequisites ---
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: openssl is required but not installed.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker is required but not installed.${NC}"
    exit 1
fi

# --- Check for existing .env ---
if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env already exists.${NC}"
    read -rp "Overwrite? (y/N): " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

# --- Check .env.dist exists ---
if [ ! -f .env.dist ]; then
    echo -e "${RED}Error: .env.dist not found. Are you in the L30 directory?${NC}"
    exit 1
fi

# --- Prompt for any library details not already supplied via flags ---
if [ -z "$DOMAIN" ] || [ -z "$LIBRARY_NAME" ] || [ -z "$FROM_EMAIL" ]; then
    if [ -t 0 ]; then
        echo ""
        echo "Enter your library details:"
        echo ""
        [ -z "$DOMAIN" ] && read -rp "Domain (e.g. library.example.com): " DOMAIN
        [ -z "$LIBRARY_NAME" ] && read -rp "Library name (e.g. Springfield Public Library): " LIBRARY_NAME
        [ -z "$FROM_EMAIL" ] && read -rp "From email (e.g. hello@library.example.com): " FROM_EMAIL
    else
        echo -e "${RED}Error: no terminal attached and required value(s) missing.${NC}"
        [ -z "$DOMAIN" ] && echo -e "${RED}  Missing --domain${NC}"
        [ -z "$LIBRARY_NAME" ] && echo -e "${RED}  Missing --name${NC}"
        [ -z "$FROM_EMAIL" ] && echo -e "${RED}  Missing --email${NC}"
        echo "Usage: ./setup.sh --domain <domain> --email <email> --name \"<library name>\""
        exit 1
    fi
fi

# Validate inputs
if [ -z "$DOMAIN" ] || [ -z "$LIBRARY_NAME" ] || [ -z "$FROM_EMAIL" ]; then
    echo -e "${RED}Error: All fields are required.${NC}"
    exit 1
fi

# --- Portable in-place sed (BSD/macOS sed requires a backup-extension arg
# after -i; GNU sed doesn't. Avoid -i entirely: write to a temp file, then
# move it into place, which works identically on both.) ---
portable_sed_i() {
    local expr="$1"
    local file="$2"
    local tmp
    tmp="$(mktemp "${file}.XXXXXX")"
    sed "$expr" "$file" > "$tmp" && mv "$tmp" "$file"
}

# --- Generate secrets ---
echo ""
echo "Generating secrets..."

DB_PASSWORD=$(openssl rand -base64 32 | tr -d '=/+' | head -c 32)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d '=/+' | head -c 48)
SECRET_KEY=$(openssl rand -base64 48)
JWT_SECRET_KEY=$(openssl rand -base64 48)
PII_ENCRYPTION_KEY=$(openssl rand -base64 32)
PII_HASH_KEY=$(openssl rand -hex 32)
WATERMARK_SECRET_SALT=$(openssl rand -base64 32)
DOWNLOAD_IP_HASH_SALT=$(openssl rand -base64 32)
METISLIB_PATRON_HASH_SECRET=$(openssl rand -base64 32)
AUDIT_LOG_SIGNING_KEY=$(openssl rand -hex 32)

# --- Build .env from template ---
cp .env.dist .env

# Replace placeholders
portable_sed_i "s|DOMAIN=your-library.example.com|DOMAIN=${DOMAIN}|" .env
portable_sed_i "s|LIBRARY_NAME=Your Library|LIBRARY_NAME=${LIBRARY_NAME}|" .env
portable_sed_i "s|FROM_EMAIL=library@example.com|FROM_EMAIL=${FROM_EMAIL}|" .env
portable_sed_i "s|FRONTEND_URL=https://your-library.example.com|FRONTEND_URL=https://${DOMAIN}|" .env
portable_sed_i "s|CORS_ORIGINS=https://your-library.example.com,https://www.your-library.example.com|CORS_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}|" .env

# Replace secrets
portable_sed_i "s|DB_PASSWORD=CHANGE_ME|DB_PASSWORD=${DB_PASSWORD}|" .env
portable_sed_i "s|REDIS_PASSWORD=CHANGE_ME|REDIS_PASSWORD=${REDIS_PASSWORD}|" .env
portable_sed_i "s|SECRET_KEY=CHANGE_ME|SECRET_KEY=${SECRET_KEY}|" .env
portable_sed_i "s|JWT_SECRET_KEY=CHANGE_ME|JWT_SECRET_KEY=${JWT_SECRET_KEY}|" .env
portable_sed_i "s|PII_ENCRYPTION_KEY=CHANGE_ME|PII_ENCRYPTION_KEY=${PII_ENCRYPTION_KEY}|" .env
portable_sed_i "s|PII_HASH_KEY=CHANGE_ME|PII_HASH_KEY=${PII_HASH_KEY}|" .env
portable_sed_i "s|WATERMARK_SECRET_SALT=CHANGE_ME|WATERMARK_SECRET_SALT=${WATERMARK_SECRET_SALT}|" .env
portable_sed_i "s|DOWNLOAD_IP_HASH_SALT=CHANGE_ME|DOWNLOAD_IP_HASH_SALT=${DOWNLOAD_IP_HASH_SALT}|" .env
portable_sed_i "s|METISLIB_PATRON_HASH_SECRET=CHANGE_ME|METISLIB_PATRON_HASH_SECRET=${METISLIB_PATRON_HASH_SECRET}|" .env
portable_sed_i "s|AUDIT_LOG_SIGNING_KEY=CHANGE_ME|AUDIT_LOG_SIGNING_KEY=${AUDIT_LOG_SIGNING_KEY}|" .env

# --- Create branding.json ---
if [ -f branding.json.example ]; then
    echo "Creating branding.json..."
    sed "s|Your Library Name|${LIBRARY_NAME}|g" branding.json.example > branding.json
    # Update domain
    portable_sed_i "s|https://yourlibrary.org|https://${DOMAIN}|g" branding.json
    # Update contact email
    portable_sed_i "s|hello@yourlibrary.org|${FROM_EMAIL}|g" branding.json
else
    echo -e "${YELLOW}Warning: branding.json.example not found, skipping branding setup.${NC}"
fi

# --- Done ---
echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "  Domain:  ${DOMAIN}"
echo "  Library: ${LIBRARY_NAME}"
echo "  Email:   ${FROM_EMAIL}"
echo ""
echo "Files created:"
echo "  .env           - Environment configuration (secrets generated)"
[ -f branding.json ] && echo "  branding.json  - Library branding"
echo ""
echo -e "${YELLOW}Run: docker compose -f docker-compose.dist.yml up -d --build${NC}"
echo ""
echo "The app listens on 127.0.0.1:8081. Put a TLS reverse proxy in front"
echo "for public access -- INSTALL.md Step 7 has a copy-paste nginx config."
