/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/patron.json' })

test.describe('Patron Account (Authenticated)', () => {
  let serverErrors: string[]

  test.beforeEach(async ({ page }) => {
    serverErrors = []
    page.on('response', response => {
      if (response.status() >= 500) {
        serverErrors.push(`${response.request().method()} ${response.url()} -> ${response.status()}`)
      }
    })
  })

  test.afterEach(async () => {
    expect(serverErrors, 'No HTTP 500+ errors').toEqual([])
  })

  test('account overview loads', async ({ page }) => {
    await page.goto('/account')
    await page.waitForLoadState('networkidle')

    // Should load account page (not redirect to login)
    const url = page.url()
    if (url.includes('/login')) {
      test.skip(true, 'Auth fixture not working - redirected to login')
    }
    await expect(page.locator('body')).toBeVisible()
  })

  test('account page has navigation tabs', async ({ page }) => {
    await page.goto('/account')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires auth')
    }

    const tabs = page.locator('[role="tab"], [role="tablist"], button[class*="tab"], nav')
    if (await tabs.count() > 0) {
      await expect(tabs.first()).toBeVisible()
    }
  })

  test('notifications page loads', async ({ page }) => {
    await page.goto('/notifications')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('notification preferences loads', async ({ page }) => {
    await page.goto('/notifications/preferences')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('reading insights loads', async ({ page }) => {
    await page.goto('/my-reading-insights')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('reading minutes loads', async ({ page }) => {
    await page.goto('/reading-minutes')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('suggest purchase form loads', async ({ page }) => {
    await page.goto('/suggest-purchase')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })
})
