/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { createClientFromStorageState, SmokeApiClient } from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { navigateAndWait, assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const DIR_AUTH = path.join(__dirname, "../.auth/director.json")

test.use({ storageState: DIR_AUTH })

/** Navigate to a staff/admin page, handling auth redirects. */
async function loadPage(page: import("@playwright/test").Page, routePath: string) {
  await page.goto(routePath)
  await page.waitForLoadState("domcontentloaded")
  await page.waitForTimeout(500)
  if (page.url().includes("/login")) return
  await assertPageResponsive(page)
  await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
}

test.describe("Director Smoke Test", () => {
  let client: SmokeApiClient

  test.beforeAll(async () => {
    client = createClientFromStorageState(DIR_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("staff dashboard loads", async ({ page }) => {
    await loadPage(page, "/staff")
  })

  test("admin dashboard loads", async ({ page }) => {
    await loadPage(page, "/staff/admin")
  })

  test("admin settings loads", async ({ page }) => {
    await loadPage(page, "/staff/admin/settings")
  })

  test("admin users page loads", async ({ page }) => {
    await loadPage(page, "/staff/admin/users")
  })

  test("admin feature flags loads", async ({ page }) => {
    await loadPage(page, "/staff/admin/features")
  })

  test("staff reports loads", async ({ page }) => {
    await loadPage(page, "/staff/reports")
  })

  test("admin circulation rules loads", async ({ page }) => {
    await loadPage(page, "/staff/admin/circulation-rules")
  })
})
