#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Generate PWA icons from favicon.svg using Node.js
 * Requires: npm install sharp
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const iconDir = __dirname;
const faviconPath = path.join(iconDir, '..', 'favicon.svg');

// Color scheme from brand
const COLORS = {
  brown: '#3E362E',
  orange: '#9e5a2d',
  cream: '#F9F6F0',
  dark: '#2C241B'
};

// Icon sizes to generate
const SIZES = [
  { name: 'icon-72x72.png', size: 72, purpose: 'any' },
  { name: 'icon-96x96.png', size: 96, purpose: 'any' },
  { name: 'icon-128x128.png', size: 128, purpose: 'any' },
  { name: 'icon-144x144.png', size: 144, purpose: 'any' },
  { name: 'icon-152x152.png', size: 152, purpose: 'any' },
  { name: 'icon-192x192.png', size: 192, purpose: 'any' },
  { name: 'icon-384x384.png', size: 384, purpose: 'any' },
  { name: 'icon-512x512.png', size: 512, purpose: 'any' },
  { name: 'maskable-icon-192x192.png', size: 192, purpose: 'maskable' },
  { name: 'maskable-icon-512x512.png', size: 512, purpose: 'maskable' },
  // Apple icons
  { name: 'apple-touch-icon-120x120.png', size: 120, purpose: 'apple' },
  { name: 'apple-touch-icon-152x152.png', size: 152, purpose: 'apple' },
  { name: 'apple-touch-icon-167x167.png', size: 167, purpose: 'apple' },
  { name: 'apple-touch-icon-180x180.png', size: 180, purpose: 'apple' }
];

// Create SVG with brown background and simple icon
function createSvgBuffer(size, isMaskable = false) {
  const padding = isMaskable ? Math.round(size * 0.1) : 0;
  const innerSize = size - (padding * 2);

  // Simple book icon - two rectangles forming an open book
  const bookWidth = Math.round(innerSize * 0.6);
  const bookHeight = Math.round(innerSize * 0.8);
  const bookX = Math.round(padding + (innerSize - bookWidth) / 2);
  const bookY = Math.round(padding + (innerSize - bookHeight) / 2);

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="${size}" height="${size}" fill="${COLORS.brown}"/>
  <!-- Book left page -->
  <rect x="${bookX}" y="${bookY}" width="${Math.round(bookWidth / 2)}" height="${bookHeight}" fill="${COLORS.orange}" opacity="0.9"/>
  <!-- Book right page -->
  <rect x="${bookX + Math.round(bookWidth / 2)}" y="${bookY}" width="${Math.round(bookWidth / 2)}" height="${bookHeight}" fill="${COLORS.cream}"/>
  <!-- Book spine -->
  <line x1="${bookX + Math.round(bookWidth / 2)}" y1="${bookY}" x2="${bookX + Math.round(bookWidth / 2)}" y2="${bookY + bookHeight}" stroke="${COLORS.dark}" stroke-width="1"/>
</svg>`;

  return Buffer.from(svg);
}

async function generateIcons() {
  console.log('Generating PWA icons...\n');

  for (const iconConfig of SIZES) {
    try {
      const svgBuffer = createSvgBuffer(iconConfig.size, iconConfig.purpose === 'maskable');
      const outputPath = path.join(iconDir, iconConfig.name);

      await sharp(svgBuffer)
        .png()
        .toFile(outputPath);

      console.log(`✓ Generated ${iconConfig.name} (${iconConfig.size}x${iconConfig.size}, ${iconConfig.purpose})`);
    } catch (error) {
      console.error(`✗ Failed to generate ${iconConfig.name}:`, error.message);
    }
  }

  console.log('\n✓ Icon generation complete!');
  console.log('\nNext steps:');
  console.log('1. Update frontend HTML to include apple-touch-icon meta tags');
  console.log('2. Update robots.txt with correct domain');
  console.log('3. Test with: https://www.pwabuilder.com/');
}

generateIcons().catch(console.error);
