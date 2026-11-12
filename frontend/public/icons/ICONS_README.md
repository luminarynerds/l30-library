<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# PWA Icons for Library Service Center

This directory contains the icons required for the PWA (Progressive Web App) manifest.

## Required Icons

The following PNG icons are required for full PWA compatibility:

### Standard Icons (purpose: "any")
These icons are used for app installation, home screen, and app switcher.

| File | Size | Usage |
|------|------|-------|
| `icon-72x72.png` | 72x72 | Android low-res |
| `icon-96x96.png` | 96x96 | Android medium-res, shortcuts |
| `icon-128x128.png` | 128x128 | Chrome Web Store |
| `icon-144x144.png` | 144x144 | Windows tiles |
| `icon-152x152.png` | 152x152 | iOS default |
| `icon-192x192.png` | 192x192 | Android high-res (required) |
| `icon-384x384.png` | 384x384 | Android extra-high-res |
| `icon-512x512.png` | 512x512 | Splash screen (required) |

### Maskable Icons (purpose: "maskable")
Maskable icons have extra padding and can be cropped to various shapes by different platforms.
The safe zone is a circle with a radius of 40% of the icon size, centered.

| File | Size | Usage |
|------|------|-------|
| `maskable-icon-192x192.png` | 192x192 | Android adaptive icon |
| `maskable-icon-512x512.png` | 512x512 | Android adaptive icon, splash |

### Apple Touch Icons
iOS requires specific icon sizes for optimal display.

| File | Size | Usage |
|------|------|-------|
| `apple-touch-icon-120x120.png` | 120x120 | iPhone |
| `apple-touch-icon-152x152.png` | 152x152 | iPad |
| `apple-touch-icon-167x167.png` | 167x167 | iPad Pro |
| `apple-touch-icon-180x180.png` | 180x180 | iPhone Retina |

## Brand Colors

Use these colors from the library brand when creating icons:

- **Background (brown)**: `#3E362E` (lsc-brown)
- **Accent (orange)**: `#9e5a2d` (lsc-orange) or `#C67C48` for lighter variant
- **Light (cream)**: `#F9F6F0` (lsc-cream)
- **Dark**: `#2C241B` (lsc-dark)

## Design Guidelines

1. **Standard Icons**: Use the existing favicon design (open book icon) scaled to each size
2. **Maskable Icons**: Same design but with 20% padding on all sides to ensure the icon fits within the safe zone
3. **Consistent branding**: Match the `favicon.svg` design - brown background with orange book graphic
4. **High contrast**: Ensure the icon is recognizable at small sizes

## Generating Icons

You can generate all icons from the existing `favicon.svg`:

### Using ImageMagick
```bash
# Standard icons
convert -background none -resize 192x192 ../favicon.svg icon-192x192.png
convert -background none -resize 512x512 ../favicon.svg icon-512x512.png
# ... repeat for other sizes

# Maskable icons (with padding)
convert -background "#3E362E" -gravity center -resize 153x153 -extent 192x192 ../favicon.svg maskable-icon-192x192.png
convert -background "#3E362E" -gravity center -resize 410x410 -extent 512x512 ../favicon.svg maskable-icon-512x512.png
```

### Using a PWA Icon Generator
You can also use online tools:
- https://www.pwabuilder.com/imageGenerator
- https://realfavicongenerator.net/
- https://maskable.app/ (for testing maskable icons)

## Testing

1. **Chrome DevTools**: Open DevTools > Application > Manifest to verify the manifest loads correctly
2. **Lighthouse**: Run a Lighthouse PWA audit to check for missing icons
3. **Maskable.app**: Upload maskable icons to verify safe zone coverage

## Temporary Placeholder

The `placeholder.svg` file can be used as a reference. It mirrors the favicon design and can be converted to PNG at any size.
