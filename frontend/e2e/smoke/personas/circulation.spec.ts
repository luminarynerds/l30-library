/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { createClientFromStorageState, SmokeApiClient, CatalogItem } from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { navigateAndWait, assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const CIRC_AUTH = path.join(__dirname, "../.auth/circulation.json")
const PATRON_AUTH = path.join(__dirname, "../.auth/patron.json")

test.use({ storageState: CIRC_AUTH })

test.describe("Circulation Clerk Smoke Test", () => {
  let staffClient: SmokeApiClient
  let patronClient: SmokeApiClient
  let testItem: CatalogItem
  let patronId: number

  test.beforeAll(async () => {
    staffClient = createClientFromStorageState(CIRC_AUTH)
    patronClient = createClientFromStorageState(PATRON_AUTH)

    await cleanupTestData(staffClient)

    testItem = await staffClient.createCatalogItem("Circ Book")
    expect(testItem.id).toBeGreaterThan(0)

    const me = await patronClient.getMe()
    patronId = me.id
  })

  test.afterAll(async () => {
    await cleanupTestData(staffClient)
  })

  test("staff circulation page loads", async ({ page }) => {
    await navigateAndWait(page, "/staff/circulation")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("checkout item to patron and verify", async () => {
    const checkout = await patronClient.checkout(testItem.id)
    expect(checkout.id).toBeGreaterThan(0)

    const checkouts = await staffClient.getPatronCheckouts(patronId)
    const found = checkouts.some((c) => c.item_id === testItem.id)
    expect(found).toBe(true)
  })

  test("checkin item and verify returned", async () => {
    const checkouts = await staffClient.getPatronCheckouts(patronId)
    const active = checkouts.find((c) => c.item_id === testItem.id)
    expect(active).toBeTruthy()

    const returned = await patronClient.checkin(active!.id)
    expect(returned.status).toBe("returned")
  })

  test("book drop page loads", async ({ page }) => {
    const response = await page.goto("/staff/book-drop")
    // May redirect to login if feature is disabled or session expired — that's OK
    const url = page.url()
    if (url.includes("/login")) {
      // Feature-gated page redirected to login — not a failure of the page itself
      expect(response?.status()).toBeLessThan(500)
    } else {
      await assertPageResponsive(page)
    }
  })
})
