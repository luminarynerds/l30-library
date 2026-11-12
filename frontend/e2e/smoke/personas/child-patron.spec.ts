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

const CHILD_AUTH = path.join(__dirname, "../.auth/child.json")

test.use({ storageState: CHILD_AUTH })

test.describe("Child Patron Smoke Test", () => {
  let client: SmokeApiClient

  test.beforeAll(async () => {
    client = createClientFromStorageState(CHILD_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("catalog page loads", async ({ page }) => {
    await navigateAndWait(page, "/catalog")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("account page loads", async ({ page }) => {
    await page.goto("/account")
    await page.waitForLoadState("domcontentloaded")
    await page.waitForTimeout(500)
    // Child may be redirected to login or shown account — both OK
    if (!page.url().includes("/login")) {
      await assertPageResponsive(page)
    }
  })

  test("youth programs page loads", async ({ page }) => {
    await navigateAndWait(page, "/youth")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("reading programs page loads", async ({ page }) => {
    await navigateAndWait(page, "/programs")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("events page loads", async ({ page }) => {
    await navigateAndWait(page, "/events")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })
})
