/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Page, expect } from "@playwright/test"

/** Navigate to a page and wait for it to be interactive */
export async function navigateAndWait(page: Page, path: string) {
  const response = await page.goto(path)
  expect(response?.status()).toBeLessThan(500)
  await page.waitForLoadState("domcontentloaded")
  return response
}

/** Assert page is responsive (not stuck loading) */
export async function assertPageResponsive(page: Page) {
  await expect(page.locator("body")).toBeVisible({ timeout: 10000 })
  // Check for infinite loading spinners
  const spinner = page.locator(
    '[aria-label="Loading"], [role="status"][aria-busy="true"]'
  )
  if ((await spinner.count()) > 0) {
    await expect(spinner.first()).not.toBeVisible({ timeout: 15000 })
  }
}

/** Get counts of interactive elements on the page */
export async function getInteractiveElements(page: Page) {
  return {
    buttons: await page.getByRole("button").count(),
    links: await page.getByRole("link").count(),
    textboxes: await page.getByRole("textbox").count(),
    selects: await page.getByRole("combobox").count(),
    checkboxes: await page.getByRole("checkbox").count(),
  }
}

/** Assert common page structure */
export async function assertPageStructure(page: Page) {
  await expect(
    page
      .locator('main, [role="main"], #main-content, .main-content')
      .first()
  ).toBeVisible({ timeout: 10000 })
}
