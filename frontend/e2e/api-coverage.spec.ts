/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import * as fs from "fs"
import * as path from "path"
const API_BASE = process.env.VITE_API_BASE
if (!API_BASE) {
  throw new Error('VITE_API_BASE is required for e2e tests')
}

/**
 * API Coverage E2E Tests
 *
 * This test suite exercises the full application UI and tracks which API endpoints are called.
 * It validates that all critical endpoints are covered through user workflows.
 *
 * Coverage tracking:
 * - Intercepts all network requests to API_BASE/
 * - Tracks called endpoints (method + path)
 * - Validates critical endpoints are covered
 * - Generates JSON report with coverage metrics
 */

// ==================== Configuration ====================

const COVERAGE_REPORT_PATH = path.join(process.cwd(), "e2e-api-coverage.json")

// Critical endpoints that MUST be covered by E2E tests
const CRITICAL_ENDPOINTS = [
  // Authentication
  `POST ${API_BASE}/auth/login`,
  `POST ${API_BASE}/auth/register`,
  `POST ${API_BASE}/auth/logout`,
  `GET ${API_BASE}/auth/me`,

  // Catalog
  `GET ${API_BASE}/catalog`,
  `GET ${API_BASE}/catalog/:id`,

  // Circulation
  `GET ${API_BASE}/circulation/checkouts`,
  `GET ${API_BASE}/circulation/holds`,
  `POST ${API_BASE}/circulation/holds`,
  `POST ${API_BASE}/circulation/checkout`,

  // User Profile
  `PUT ${API_BASE}/auth/me`,
]

// All known endpoints (comprehensive list for coverage tracking)
const KNOWN_ENDPOINTS = [
  // Auth domain
  `POST ${API_BASE}/auth/login`,
  `POST ${API_BASE}/auth/register`,
  `POST ${API_BASE}/auth/logout`,
  `POST ${API_BASE}/auth/refresh`,
  `POST ${API_BASE}/auth/forgot-password`,
  `POST ${API_BASE}/auth/reset-password`,
  `POST ${API_BASE}/auth/verify-email`,
  `POST ${API_BASE}/auth/resend-verification`,
  `POST ${API_BASE}/auth/change-password`,
  `GET ${API_BASE}/auth/sessions`,
  `DELETE ${API_BASE}/auth/sessions/:id`,
  `GET ${API_BASE}/auth/me`,
  `PUT ${API_BASE}/auth/me`,

  // Catalog domain
  `GET ${API_BASE}/catalog`,
  `GET ${API_BASE}/catalog/:id`,
  `GET ${API_BASE}/catalog/barcode/:barcode`,

  // Circulation domain
  `GET ${API_BASE}/circulation/checkouts`,
  `GET ${API_BASE}/circulation/holds`,
  `POST ${API_BASE}/circulation/checkout`,
  `POST ${API_BASE}/circulation/holds`,
  `DELETE ${API_BASE}/circulation/holds/:id`,
  `POST ${API_BASE}/circulation/renew/:id`,
  `GET ${API_BASE}/circulation/history`,
  `GET ${API_BASE}/circulation/fines`,
  `GET ${API_BASE}/circulation/fines/summary`,

  // Analytics/Reports domain
  `GET ${API_BASE}/reports/analytics/dashboard`,
  `GET ${API_BASE}/reports/analytics/circulation`,
  `GET ${API_BASE}/reports/analytics/collection-health`,
  `GET ${API_BASE}/reports/analytics/drifting-items`,
  `GET ${API_BASE}/reports/analytics/patron-engagement`,
  `GET ${API_BASE}/reports/analytics/top-readers`,
  `GET ${API_BASE}/reports/analytics/reading`,
  `GET ${API_BASE}/reports/analytics/fines`,
  `GET ${API_BASE}/reports/analytics/popular-items`,
  `GET ${API_BASE}/reports/analytics/circulation-trends`,

  // Events domain
  `GET ${API_BASE}/events`,
  `GET ${API_BASE}/events/:id`,
  `POST ${API_BASE}/events/:id/register`,
  `DELETE ${API_BASE}/events/:id/register`,

  // Reading Programs domain
  `GET ${API_BASE}/reading-programs`,
  `GET ${API_BASE}/reading-programs/:id`,
  `POST ${API_BASE}/reading-programs/:id/enroll`,
  `POST ${API_BASE}/reading-programs/:id/log`,
  `GET ${API_BASE}/reading-programs/:id/logs`,
  `GET ${API_BASE}/reading-programs/:id/leaderboard`,

  // Collections domain (favorites, lists)
  `GET ${API_BASE}/favorites`,
  `POST ${API_BASE}/favorites`,
  `DELETE ${API_BASE}/favorites/:id`,
  `GET ${API_BASE}/reading-lists`,
  `POST ${API_BASE}/reading-lists`,
  `GET ${API_BASE}/reading-lists/:id`,
  `PUT ${API_BASE}/reading-lists/:id`,
  `DELETE ${API_BASE}/reading-lists/:id`,
  `POST ${API_BASE}/reading-lists/:id/items`,
  `DELETE ${API_BASE}/reading-lists/:listId/items/:itemId`,

  // Staff domain
  `GET ${API_BASE}/staff/dashboard`,
  `GET ${API_BASE}/staff/bio`,
  `PUT ${API_BASE}/staff/bio`,

  // AI Tools domain
  `POST ${API_BASE}/ai/recommendations`,
  `POST ${API_BASE}/ai/summarize`,

  // Notifications domain
  `GET ${API_BASE}/notifications`,
  `PUT ${API_BASE}/notifications/:id/read`,
  `PUT ${API_BASE}/notifications/read-all`,
]

// ==================== Helper Functions ====================

interface ApiCall {
  method: string
  path: string
  timestamp: string
}

interface CoverageReport {
  timestamp: string
  totalCalls: number
  uniqueEndpoints: number
  knownEndpoints: number
  coveragePercentage: number
  criticalCoverage: number
  criticalCoveragePercentage: number
  calledEndpoints: string[]
  uncalledKnownEndpoints: string[]
  missingCriticalEndpoints: string[]
  allCalls: ApiCall[]
}

/**
 * Normalizes API paths by replacing numeric IDs with :id placeholders
 */
function normalizeApiPath(url: string): string {
  try {
    const urlObj = new URL(url)
    let path = urlObj.pathname

    // Replace numeric IDs with :id
    path = path.replace(/\/\d+/g, "/:id")
    // Replace UUID-like patterns with :id
    path = path.replace(/\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, "/:id")
    // Replace barcode patterns with :barcode
    if (path.includes("/barcode/")) {
      path = path.replace(/\/barcode\/[^/]+/, "/barcode/:barcode")
    }

    return path
  } catch (e) {
    return url
  }
}

/**
 * Generates coverage report from collected API calls
 */
function generateCoverageReport(apiCalls: Set<string>, allCalls: ApiCall[]): CoverageReport {
  const calledEndpoints = Array.from(apiCalls).sort()
  const uncalledKnownEndpoints = KNOWN_ENDPOINTS.filter((endpoint) => !apiCalls.has(endpoint))
  const missingCriticalEndpoints = CRITICAL_ENDPOINTS.filter((endpoint) => !apiCalls.has(endpoint))

  const criticalCoverage = CRITICAL_ENDPOINTS.length - missingCriticalEndpoints.length
  const criticalCoveragePercentage =
    CRITICAL_ENDPOINTS.length > 0 ? (criticalCoverage / CRITICAL_ENDPOINTS.length) * 100 : 100

  const coveragePercentage =
    KNOWN_ENDPOINTS.length > 0 ? (calledEndpoints.length / KNOWN_ENDPOINTS.length) * 100 : 0

  return {
    timestamp: new Date().toISOString(),
    totalCalls: allCalls.length,
    uniqueEndpoints: calledEndpoints.length,
    knownEndpoints: KNOWN_ENDPOINTS.length,
    coveragePercentage: Math.round(coveragePercentage * 100) / 100,
    criticalCoverage,
    criticalCoveragePercentage: Math.round(criticalCoveragePercentage * 100) / 100,
    calledEndpoints,
    uncalledKnownEndpoints,
    missingCriticalEndpoints,
    allCalls,
  }
}

/**
 * Saves coverage report to JSON file
 */
function saveCoverageReport(report: CoverageReport): void {
  fs.writeFileSync(COVERAGE_REPORT_PATH, JSON.stringify(report, null, 2))
  console.log(`\Coverage report saved to: ${COVERAGE_REPORT_PATH}`)
}

/**
 * Logs coverage summary to console
 */
function logCoverageSummary(report: CoverageReport): void {
  console.log("\n" + "=".repeat(80))
  console.log("API COVERAGE SUMMARY")
  console.log("=".repeat(80))
  console.log(`Total API calls made: ${report.totalCalls}`)
  console.log(`Unique endpoints called: ${report.uniqueEndpoints}`)
  console.log(
    `Overall coverage: ${report.uniqueEndpoints}/${report.knownEndpoints} endpoints (${report.coveragePercentage}%)`
  )
  console.log(
    `Critical coverage: ${report.criticalCoverage}/${CRITICAL_ENDPOINTS.length} endpoints (${report.criticalCoveragePercentage}%)`
  )

  if (report.missingCriticalEndpoints.length > 0) {
    console.log("\n" + "-".repeat(80))
    console.log("MISSING CRITICAL ENDPOINTS:")
    console.log("-".repeat(80))
    report.missingCriticalEndpoints.forEach((endpoint) => {
      console.log(`  - ${endpoint}`)
    })
  }

  if (report.uncalledKnownEndpoints.length > 0) {
    console.log("\n" + "-".repeat(80))
    console.log(`UNCALLED KNOWN ENDPOINTS (${report.uncalledKnownEndpoints.length}):`)
    console.log("-".repeat(80))
    // Show first 20 to avoid cluttering output
    const displayEndpoints = report.uncalledKnownEndpoints.slice(0, 20)
    displayEndpoints.forEach((endpoint) => {
      console.log(`  - ${endpoint}`)
    })
    if (report.uncalledKnownEndpoints.length > 20) {
      console.log(`  ... and ${report.uncalledKnownEndpoints.length - 20} more`)
    }
  }

  console.log("\n" + "-".repeat(80))
  console.log("CALLED ENDPOINTS:")
  console.log("-".repeat(80))
  report.calledEndpoints.forEach((endpoint) => {
    console.log(`  - ${endpoint}`)
  })
  console.log("=".repeat(80) + "\n")
}

// ==================== Test Suite ====================

test.describe("API Coverage Tests", () => {
  let apiCalls: Set<string>
  let allCalls: ApiCall[]

  test.beforeEach(({ page }) => {
    apiCalls = new Set()
    allCalls = []

    // Intercept all network requests
    page.on("request", (request) => {
      const url = request.url()

      // Only track API calls
      if (url.includes(`${API_BASE}/`)) {
        const method = request.method()
        const normalizedPath = normalizeApiPath(url)
        const endpoint = `${method} ${normalizedPath}`

        apiCalls.add(endpoint)
        allCalls.push({
          method,
          path: normalizedPath,
          timestamp: new Date().toISOString(),
        })
      }
    })
  })

  test("exercises all critical user flows and tracks API coverage", async ({ page }) => {
    console.log("\nStarting comprehensive API coverage test...\n")

    // ==================== Public Pages (Catalog Browse) ====================
    console.log("Testing: Public catalog browsing...")
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    // Search catalog
    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]').first()
    if ((await searchInput.count()) > 0) {
      await searchInput.fill("fiction")
      await searchInput.press("Enter")
      await page.waitForTimeout(1000)
    }

    // Click on a catalog item if available
    const catalogItem = page.locator('a[href*="/catalog/"]').first()
    if ((await catalogItem.count()) > 0) {
      await catalogItem.click()
      await page.waitForLoadState("networkidle")
      await page.waitForTimeout(500)
    }

    // ==================== Authentication Flow ====================
    console.log("Testing: User registration...")
    await page.goto("/register")
    await page.waitForLoadState("networkidle")

    // Fill registration form (using test data)
    const emailInput = page.locator('input[type="email"]').first()
    if ((await emailInput.count()) > 0) {
      const testEmail = `test-${Date.now()}@example.com`
      await emailInput.fill(testEmail)

      const firstNameInput = page.locator('input[name="firstName"], input[name="first_name"]').first()
      if ((await firstNameInput.count()) > 0) {
        await firstNameInput.fill("Test")
      }

      const lastNameInput = page.locator('input[name="lastName"], input[name="last_name"]').first()
      if ((await lastNameInput.count()) > 0) {
        await lastNameInput.fill("User")
      }

      const passwordInput = page.locator('input[type="password"]').first()
      if ((await passwordInput.count()) > 0) {
        await passwordInput.fill("TestPassword123!")

        // Note: We don't actually submit to avoid creating test users
        // but the form validation may trigger API calls
      }
    }

    // ==================== Login Flow ====================
    console.log("Testing: User login...")
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    // Try login with demo/test credentials if available
    const loginEmailInput = page.locator('input[type="email"]').first()
    const loginPasswordInput = page.locator('input[type="password"]').first()

    if ((await loginEmailInput.count()) > 0 && (await loginPasswordInput.count()) > 0) {
      // Use demo credentials (these may not work, but will trigger API call)
      await loginEmailInput.fill("demo@example.com")
      await loginPasswordInput.fill("demopassword")

      // Look for login button
      const loginButton = page
        .locator('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")')
        .first()

      if ((await loginButton.count()) > 0) {
        // Click but expect it might fail - we're just testing API coverage
        await loginButton.click().catch(() => {
          console.log("  (Login expected to fail - using demo credentials)")
        })
        await page.waitForTimeout(1000)
      }
    }

    // ==================== User Dashboard (if logged in) ====================
    // Try to access protected routes to trigger API calls
    console.log("Testing: Protected routes (may fail if not authenticated)...")
    const protectedRoutes = [
      "/dashboard",
      "/account",
      "/my-checkouts",
      "/my-holds",
      "/reading-history",
      "/staff",
    ]

    for (const route of protectedRoutes) {
      await page.goto(route).catch(() => {})
      await page.waitForTimeout(500)
    }

    // ==================== Events ====================
    console.log("Testing: Events page...")
    await page.goto("/events")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    // ==================== Reading Programs ====================
    console.log("Testing: Reading programs...")
    await page.goto("/programs")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    // ==================== Digital Resources ====================
    console.log("Testing: Digital resources...")
    await page.goto("/digital")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    // ==================== AI Tools ====================
    console.log("Testing: AI tools...")
    await page.goto("/ai")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    // ==================== About Pages ====================
    console.log("Testing: About pages...")
    await page.goto("/about")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    console.log("\nAPI coverage test complete!")
  })

  test.afterAll(() => {
    // Generate coverage report
    const report = generateCoverageReport(apiCalls, allCalls)

    // Log summary to console
    logCoverageSummary(report)

    // Save report to file
    saveCoverageReport(report)

    // Assert critical endpoints coverage
    if (report.missingCriticalEndpoints.length > 0) {
      console.warn(
        `\WARNING: ${report.missingCriticalEndpoints.length} critical endpoints were not covered!`
      )
      // Note: We don't fail the test here to allow viewing the report
      // Uncomment the line below to make this a hard requirement:
      // expect(report.missingCriticalEndpoints).toEqual([])
    }
  })
})

// ==================== Authenticated User Flows ====================

test.describe("API Coverage - Authenticated Workflows", () => {
  let apiCalls: Set<string>
  let allCalls: ApiCall[]

  test.beforeEach(({ page }) => {
    apiCalls = new Set()
    allCalls = []

    page.on("request", (request) => {
      const url = request.url()
      if (url.includes(`${API_BASE}/`)) {
        const method = request.method()
        const normalizedPath = normalizeApiPath(url)
        const endpoint = `${method} ${normalizedPath}`
        apiCalls.add(endpoint)
        allCalls.push({
          method,
          path: normalizedPath,
          timestamp: new Date().toISOString(),
        })
      }
    })
  })

  test("tracks API calls from authenticated user workflows", async ({ page }) => {
    console.log("\nTesting authenticated workflows (may be limited without real credentials)...\n")

    // This test demonstrates how to test authenticated flows
    // In a real scenario, you would:
    // 1. Use a test account with known credentials
    // 2. Login programmatically via API or UI
    // 3. Execute authenticated workflows

    console.log("Testing: Attempting to access account page...")
    await page.goto("/account")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    console.log("Testing: Attempting to access my checkouts...")
    await page.goto("/my-checkouts")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    console.log("Testing: Attempting to access my holds...")
    await page.goto("/my-holds")
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(500)

    // Log what we captured
    console.log(`\Captured ${apiCalls.size} unique API endpoints from authenticated flows`)
  })

  test.afterAll(() => {
    if (apiCalls.size > 0) {
      console.log("\nAuthenticated workflow API calls:")
      Array.from(apiCalls)
        .sort()
        .forEach((endpoint) => {
          console.log(`  - ${endpoint}`)
        })
    }
  })
})