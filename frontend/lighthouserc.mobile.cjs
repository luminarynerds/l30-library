/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Lighthouse CI Configuration -- Mobile
 *
 * Mobile form factor audit with strict accessibility thresholds.
 * Run with: npx lhci autorun --config=lighthouserc.mobile.js
 */

module.exports = {
  ci: {
    collect: {
      url: [
        "http://localhost:5173/",
        "http://localhost:5173/catalog",
        "http://localhost:5173/events",
        "http://localhost:5173/programs",
        "http://localhost:5173/about",
        "http://localhost:5173/contact",
        "http://localhost:5173/accessibility",
        "http://localhost:5173/privacy",
        "http://localhost:5173/learn",
        "http://localhost:5173/learning-paths",
        "http://localhost:5173/digital",
        "http://localhost:5173/ai",
        "http://localhost:5173/login",
        "http://localhost:5173/register",
      ],
      numberOfRuns: 1,
      startServerCommand: "npm run preview -- --host 127.0.0.1 --port 5173",
      startServerReadyPattern: "Local:",
      startServerReadyTimeout: 30000,
      settings: {
        
        formFactor: "mobile",
        screenEmulation: {
          mobile: true,
          width: 375,
          height: 667,
          deviceScaleFactor: 2,
          disabled: false,
        },
        chromeFlags: "--no-sandbox --headless=new --disable-dev-shm-usage",
      },
    },
    assert: {
      assertions: {
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "bypass": "error",
        "color-contrast": "error",
        "document-title": "error",
        "html-has-lang": "error",
        "image-alt": "error",
        "label": "error",
        "link-name": "error",
        "meta-viewport": "error",
        "button-name": "error",
      },
    },
    upload: {
      target: "temporary-public-storage",
    },
  },
}
