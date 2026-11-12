/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

const indieRoutes = [
  { path: '/indie', name: 'Indie Catalog' },
  { path: '/indie/discover', name: 'Discover' },
  { path: '/indie/feed', name: 'Feed' },
  { path: '/indie/audiobooks', name: 'Audiobooks' },
]

test.describe('Indie Author Platform', () => {
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

  for (const route of indieRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      const response = await page.goto(route.path)
      expect(response?.status()).toBeLessThan(500)
      await expect(page.locator('body')).toBeVisible()
    })
  }

  test('indie catalog has book listings', async ({ page }) => {
    await page.goto('/indie')
    await page.waitForLoadState('networkidle')

    const links = await page.getByRole('link').count()
    expect(links).toBeGreaterThan(0)
  })

  test('book detail loads if books exist', async ({ page }) => {
    await page.goto('/indie')
    await page.waitForLoadState('networkidle')

    const bookLinks = page.locator('a[href*="/indie/book/"]')
    if (await bookLinks.count() > 0) {
      await bookLinks.first().click()
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    }
  })
})
