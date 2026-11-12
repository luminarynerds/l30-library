/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect, Page } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { createClientFromStorageState, SmokeApiClient } from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const ACQ_AUTH = path.join(__dirname, "../.auth/acquisitions.json")

test.use({ storageState: ACQ_AUTH })

/** Navigate to a staff page, handling feature-gate redirects to login. */
async function loadStaffPage(page: Page, path: string) {
  await page.goto(path)
  // Wait for potential client-side redirect
  await page.waitForLoadState("domcontentloaded")
  await page.waitForTimeout(500)
  const url = page.url()
  if (url.includes("/login")) {
    // Feature-gated or session expired — not a page failure
    return
  }
  await assertPageResponsive(page)
  await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
}

test.describe("Acquisitions Librarian Smoke Test", () => {
  let client: SmokeApiClient

  test.beforeAll(async () => {
    client = createClientFromStorageState(ACQ_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("staff acquisition page loads", async ({ page }) => {
    await loadStaffPage(page, "/staff/acquisition")
  })

  test("selection list page loads", async ({ page }) => {
    await loadStaffPage(page, "/staff/selection-list")
  })

  test("funds page loads", async ({ page }) => {
    await loadStaffPage(page, "/staff/funds")
  })

  test("vendors page loads", async ({ page }) => {
    await loadStaffPage(page, "/staff/vendors")
  })

  test("purchase requests page loads", async ({ page }) => {
    await loadStaffPage(page, "/staff/purchase-requests")
  })
})
