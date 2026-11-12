/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { testPrefix } from "../smoke.config"
import { createClientFromStorageState, SmokeApiClient, CatalogItem } from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { navigateAndWait, assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const CATALOGER_AUTH = path.join(__dirname, "../.auth/cataloger.json")

test.use({ storageState: CATALOGER_AUTH })

test.describe("Cataloger Smoke Test", () => {
  let client: SmokeApiClient
  let testItem: CatalogItem

  test.beforeAll(async () => {
    client = createClientFromStorageState(CATALOGER_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("staff cataloging page loads", async ({ page }) => {
    await navigateAndWait(page, "/staff/cataloging")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("create a test catalog item via API", async () => {
    testItem = await client.createCatalogItem("Cataloger Book")
    expect(testItem.id).toBeGreaterThan(0)
    expect(testItem.title).toContain("[TEST:")
  })

  test("search for test item in staff catalog", async ({ page }) => {
    await navigateAndWait(page, "/staff/cataloging")
    await assertPageResponsive(page)

    // Look for a search input on the cataloging page
    const searchInput = page
      .getByRole("searchbox")
      .or(page.getByPlaceholder(/search/i))
      .first()
    if (await searchInput.isVisible()) {
      await searchInput.fill(testPrefix())
      await searchInput.press("Enter")
      await page.waitForTimeout(2000)
    }
  })

  test("catalog item detail page loads", async ({ page }) => {
    await navigateAndWait(page, `/catalog/${testItem.id}`)
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })
})
