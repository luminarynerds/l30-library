/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { defineConfig, devices } from "@playwright/test"

/**
 * Playwright E2E Test Configuration
 *
 * Configuration for end-to-end testing of public pages including:
 * - Accessibility audits (axe-core)
 * - Broken link detection
 * - Visual regression testing
 * - Cross-browser testing
 * - Journey-specific smoke tests with multiple viewports
 * - Performance budget assertions
 *
 * @see https://playwright.dev/docs/test-configuration
 */

// Custom device configurations for journey testing
const customDevices = {
  "Mobile 375px": {
    ...devices["Pixel 5"],
    viewport: { width: 375, height: 812 },
  },
  "Mobile 390px": {
    ...devices["Pixel 5"],
    viewport: { width: 390, height: 844 },
  },
  "Tablet 768px": {
    ...devices["iPad"],
    viewport: { width: 768, height: 1024 },
  },
}

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI for reliability */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use */
  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["json", { outputFile: "playwright-report/results.json" }],
    ["junit", { outputFile: "playwright-report/junit.xml" }],
    ["list"],
  ],
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: process.env.BASE_URL || "http://localhost:5173",

    /* Collect trace when retrying the failed test */
    trace: "on-first-retry",

    /* Take screenshot on failure */
    screenshot: "only-on-failure",

    /* Video recording */
    video: "on-first-retry",

    /* Action timeout for faster failure detection */
    actionTimeout: 10000,
  },

  /* Configure projects for major browsers and viewports */
  projects: [
    // Journey smoke tests on Chromium (primary browser)
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },

    // Mobile viewport tests for journey completeness
    {
      name: "mobile-375px",
      use: customDevices["Mobile 375px"],
    },
    {
      name: "mobile-390px",
      use: customDevices["Mobile 390px"],
    },
    {
      name: "tablet-768px",
      use: customDevices["Tablet 768px"],
    },

    // Cross-browser testing (Firefox and WebKit)
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },

    // Authenticated role-based projects
    {
      name: "chromium-admin",
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/admin.json" },
    },
    {
      name: "chromium-staff",
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/staff.json" },
    },
    {
      name: "chromium-patron",
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/patron.json" },
    },

    // Smoke test setup (authenticates all smoke personas)
    {
      name: "smoke-setup",
      testMatch: /smoke\/smoke-setup\.ts/,
    },
    // Smoke test personas (depends on smoke-setup for auth)
    {
      name: "smoke",
      testDir: "./e2e/smoke/personas",
      dependencies: ["smoke-setup"],
      fullyParallel: false,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.BASE_URL || "http://localhost:8081",
      },
    },
    // Exploratory sweep (screenshots + snapshots for AI review)
    {
      name: "explore",
      testMatch: /smoke\/exploratory\.spec\.ts/,
      fullyParallel: false,
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.BASE_URL || "http://localhost:8081",
      },
    },
  ],

  /* Run your local dev server before starting the tests.
     Skip when running smoke tests against the docker stack. */
  webServer: process.env.SMOKE_ONLY
    ? undefined
    : {
        command: "npm run dev",
        url: "http://localhost:5173",
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
      },

  /* Global timeout for each test */
  timeout: 60 * 1000,

  /* Expect timeout */
  expect: {
    timeout: 5000,
  },

  /* Output folder for test artifacts */
  outputDir: "test-results/",
})
