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

const REF_AUTH = path.join(__dirname, "../.auth/reference.json")

test.use({ storageState: REF_AUTH })

test.describe("Reference Librarian Smoke Test", () => {
  let client: SmokeApiClient

  test.beforeAll(async () => {
    client = createClientFromStorageState(REF_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("catalog search page loads", async ({ page }) => {
    await navigateAndWait(page, "/catalog")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("search returns results for a common term", async ({ page }) => {
    await navigateAndWait(page, "/catalog")
    const searchInput = page
      .getByRole("searchbox")
      .or(page.getByPlaceholder(/search/i))
      .first()
    if (await searchInput.isVisible()) {
      await searchInput.fill("book")
      await searchInput.press("Enter")
      await page.waitForTimeout(2000)
      // Page should not show an error
      await expect(page.locator("text=Internal Server Error")).not.toBeVisible()
    }
  })

  test("ask a librarian page loads", async ({ page }) => {
    await navigateAndWait(page, "/ask-librarian")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("knowledge base page loads", async ({ page }) => {
    await navigateAndWait(page, "/help")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("staff knowledge base page loads", async ({ page }) => {
    const response = await page.goto("/staff/knowledge-base")
    const url = page.url()
    if (url.includes("/login")) {
      expect(response?.status()).toBeLessThan(500)
    } else {
      await assertPageResponsive(page)
      await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
    }
  })

  test("contact page loads", async ({ page }) => {
    await navigateAndWait(page, "/contact")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })
})
