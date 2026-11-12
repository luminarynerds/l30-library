/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Lighthouse CI Configuration
 *
 * Defines performance, accessibility, best practices, and SEO thresholds
 * for all public pages.
 *
 * @see https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md
 */

module.exports = {
  ci: {
    collect: {
      // URLs to test (relative to the running server)
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
      // Number of runs per URL for more stable results
      numberOfRuns: 3,
      // Start the dev server before testing
      startServerCommand: "npm run preview",
      startServerReadyPattern: "Local:",
      startServerReadyTimeout: 30000,
      settings: {
        // Throttling settings (simulate slower connection)
        preset: "desktop",
        // Form factor
        formFactor: "desktop",
        // Screen emulation
        screenEmulation: {
          mobile: false,
          width: 1350,
          height: 940,
          deviceScaleFactor: 1,
          disabled: false,
        },
      },
    },
    assert: {
      assertions: {
        // Performance thresholds
        "categories:performance": ["warn", { minScore: 0.7 }],

        // Accessibility thresholds (strict - we aim for WCAG compliance)
        "categories:accessibility": ["error", { minScore: 0.85 }],

        // Best practices
        "categories:best-practices": ["warn", { minScore: 0.8 }],

        // SEO
        "categories:seo": ["warn", { minScore: 0.8 }],

        // Specific accessibility audits that must pass
        "bypass": "error",              // Skip links
        "color-contrast": "warn",       // Color contrast
        "document-title": "error",      // Page title
        "html-has-lang": "error",       // HTML lang attribute
        "image-alt": "error",           // Image alt text
        "label": "error",               // Form labels
        "link-name": "error",           // Link text
        "meta-viewport": "error",       // Viewport meta tag

        // Performance audits
        "first-contentful-paint": ["warn", { maxNumericValue: 3000 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 4000 }],
        "cumulative-layout-shift": ["warn", { maxNumericValue: 0.1 }],
        "total-blocking-time": ["warn", { maxNumericValue: 500 }],
      },
    },
    upload: {
      // Store results locally (can be changed to Lighthouse CI server)
      target: "temporary-public-storage",
    },
  },
}
