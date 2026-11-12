#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

# PWA Icon Generator for Library Service Center
# Generates all required PNG icons from the SVG placeholders
#
# Requirements: ImageMagick (install via: brew install imagemagick or apt install imagemagick)
#
# Usage: ./generate-icons.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for ImageMagick
if ! command -v convert &> /dev/null; then
    echo "Error: ImageMagick is not installed."
    echo "Install it via:"
    echo "  macOS: brew install imagemagick"
    echo "  Ubuntu/Debian: sudo apt install imagemagick"
    echo "  Windows: choco install imagemagick"
    exit 1
fi

echo "Generating PWA icons for Library Service Center..."

# Standard icons from placeholder.svg
STANDARD_SIZES=(72 96 128 144 152 192 384 512)

for size in "${STANDARD_SIZES[@]}"; do
    echo "  Creating icon-${size}x${size}.png..."
    convert -background none -resize "${size}x${size}" placeholder.svg "icon-${size}x${size}.png"
done

# Maskable icons from maskable-placeholder.svg
MASKABLE_SIZES=(192 512)

for size in "${MASKABLE_SIZES[@]}"; do
    echo "  Creating maskable-icon-${size}x${size}.png..."
    convert -background none -resize "${size}x${size}" maskable-placeholder.svg "maskable-icon-${size}x${size}.png"
done

# Apple touch icons
APPLE_SIZES=(120 152 167 180)

for size in "${APPLE_SIZES[@]}"; do
    echo "  Creating apple-touch-icon-${size}x${size}.png..."
    convert -background none -resize "${size}x${size}" placeholder.svg "apple-touch-icon-${size}x${size}.png"
done

echo ""
echo "Done! All PWA icons have been generated."
echo ""
echo "Generated files:"
ls -la *.png 2>/dev/null || echo "  (no PNG files found - check for errors above)"
