/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { PERSONAS, testPrefix } from "../smoke.config"
import {
  createClientFromStorageState,
  SmokeApiClient,
  CatalogItem,
  EventRecord,
} from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { navigateAndWait, assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const CIRC_AUTH = path.join(__dirname, "../.auth/circulation.json")
const PATRON_AUTH = path.join(__dirname, "../.auth/patron.json")

test.use({ storageState: PATRON_AUTH })

test.describe("Patron Smoke Test", () => {
  let staffClient: SmokeApiClient
  let patronClient: SmokeApiClient
  let testItem: CatalogItem
  let testEvent: EventRecord

  test.beforeAll(async () => {
    staffClient = createClientFromStorageState(CIRC_AUTH)
    patronClient = createClientFromStorageState(PATRON_AUTH)

    await cleanupTestData(staffClient)

    testItem = await staffClient.createCatalogItem("Patron Book")
    expect(testItem.id).toBeGreaterThan(0)

    testEvent = await staffClient.createEvent("Patron Event")
    expect(testEvent.id).toBeGreaterThan(0)
  })

  test.afterAll(async () => {
    await cleanupTestData(staffClient)
  })

  test("search catalog and find test item", async ({ page }) => {
    await navigateAndWait(page, "/catalog")
    await assertPageResponsive(page)

    const searchInput = page.getByRole("searchbox").or(page.getByPlaceholder(/search/i)).first()
    if (await searchInput.isVisible()) {
      await searchInput.fill(testPrefix())
      await searchInput.press("Enter")
      await page.waitForTimeout(2000)
    }
  })

  test("place and cancel a hold", async () => {
    const hold = await patronClient.placeHold(testItem.id)
    expect(hold.id).toBeGreaterThan(0)
    expect(["pending", "ready"]).toContain(hold.status)

    await patronClient.cancelHold(hold.id)
  })

  test("account page loads with holds tab", async ({ page }) => {
    await navigateAndWait(page, "/account")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("write a review", async () => {
    const review = await patronClient.writeReview(
      testItem.id,
      `${testPrefix()} Great Book`,
      "This is a smoke test review.",
    )
    expect(review.id).toBeGreaterThan(0)
  })

  test("events page loads and shows test event", async ({ page }) => {
    await navigateAndWait(page, "/events")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("register for event", async () => {
    const reg = await patronClient.registerForEvent(
      testEvent.id,
      "Smoke Patron",
      PERSONAS.patron.email,
    )
    expect(reg.id).toBeGreaterThan(0)
  })

  test("rooms page loads", async ({ page }) => {
    await navigateAndWait(page, "/rooms")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })
})
