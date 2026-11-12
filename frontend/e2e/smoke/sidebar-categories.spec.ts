/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { navigateAndWait, assertPageResponsive } from "../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const ADMIN_AUTH = path.join(__dirname, "../../.auth/admin.json")

test.use({ storageState: ADMIN_AUTH })

test.describe("Staff Sidebar Categories Smoke Test", () => {
  /**
   * Filter console errors, excluding React dev warnings and hydration mismatches
   * which are not indicative of real page failures.
   */
  function isRealError(message: string): boolean {
    const ignorePatterns = [
      /React does not recognize/,
      /Warning:/,
      /Hydration mismatch/,
      /react-dom.development.js/,
      /Non-Error promise rejection/,
    ]
    return !ignorePatterns.some((pattern) => pattern.test(message))
  }

  /**
   * Navigate to a page and verify it loads correctly.
   * Checks: response status, main content element, no real console errors, expected text.
   */
  async function verifySidebarPage(
    page: import("@playwright/test").Page,
    path: string,
    expectText: string,
  ) {
    const errors: string[] = []
    const errorListener = (msg: string) => {
      if (isRealError(msg)) {
        errors.push(msg)
      }
    }

    const consoleListener = (msg: import("@playwright/test").ConsoleMessage) => {
      if (msg.type() === "error") {
        errorListener(msg.text())
      }
    }
    page.on("console", consoleListener)

    await navigateAndWait(page, path)
    await assertPageResponsive(page)

    // Verify main content exists
    await expect(page.locator("main, [role='main'], #main-content, .main-content").first()).toBeVisible({
      timeout: 10000,
    })

    // Verify no real console errors accumulated
    expect(errors).toEqual([])

    // Verify expected text is present
    await expect(page.locator("body")).toContainText(expectText, { timeout: 10000 })

    // Clean up console listener to prevent stacking across calls
    page.off("console", consoleListener)
  }

  test.describe("Primary Category Routes", () => {
    test("Dashboard loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff", "Dashboard")
    })

    test("Front Desk - Circulation loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/circulation", "Circulation")
    })

    test("Collection - Cataloging loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/cataloging", "Catalog")
    })

    test("Library - Events loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/events", "Event")
    })

    test("Board loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/admin/board", "Board")
    })

    test("Reports - Analytics loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/admin/analytics", "Analytics")
    })

    test("Admin - Features loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/admin/features", "Feature")
    })
  })

  test.describe("Sub-Route Coverage", () => {
    test("Checkout - Streamlined loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/checkout/streamlined", "Checkout")
    })

    test("Acquisition loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/acquisition", "Acquisition")
    })

    test("Home Delivery loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/home-delivery", "Delivery")
    })

    test("Board - Treasurer loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/admin/board-treasurer", "Treasurer")
    })

    test("Reports - Unified loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/reports/unified", "Report")
    })

    test("Admin - Settings loads", async ({ page }) => {
      await verifySidebarPage(page, "/staff/admin/settings", "Settings")
    })
  })
})
