/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import path from "path"
import { fileURLToPath } from "url"
import { createClientFromStorageState, SmokeApiClient, EventRecord } from "../helpers/api"
import { cleanupTestData } from "../helpers/cleanup"
import { navigateAndWait, assertPageResponsive } from "../../helpers/test-utils"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const YOUTH_AUTH = path.join(__dirname, "../.auth/youth.json")

test.use({ storageState: YOUTH_AUTH })

test.describe("Youth Services Smoke Test", () => {
  let client: SmokeApiClient
  let testEvent: EventRecord

  test.beforeAll(async () => {
    client = createClientFromStorageState(YOUTH_AUTH)
    await cleanupTestData(client)
  })

  test.afterAll(async () => {
    await cleanupTestData(client)
  })

  test("staff events page loads", async ({ page }) => {
    await navigateAndWait(page, "/staff/events")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("create a test event via API", async () => {
    testEvent = await client.createEvent("Youth Storytime")
    expect(testEvent.id).toBeGreaterThan(0)
    expect(testEvent.title).toContain("[TEST:")
  })

  test("public events page loads", async ({ page }) => {
    await navigateAndWait(page, "/events")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("reading programs page loads", async ({ page }) => {
    await navigateAndWait(page, "/programs")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })

  test("youth programs page loads", async ({ page }) => {
    await navigateAndWait(page, "/youth")
    await assertPageResponsive(page)
    await expect(page.locator("main, [role='main'], .main-content").first()).toBeVisible()
  })
})
