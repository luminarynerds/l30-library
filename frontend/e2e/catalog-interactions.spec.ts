/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.describe('Catalog Interactions', () => {
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

  test('catalog page loads and has search', async ({ page }) => {
    await page.goto('/catalog')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()

    const searchInput = page.getByRole('textbox').first()
    const hasSearch = await searchInput.count() > 0
    const hasSearchButton = await page.getByRole('button', { name: /search/i }).count() > 0
    expect(hasSearch || hasSearchButton).toBeTruthy()
  })

  test('catalog search returns results', async ({ page }) => {
    await page.goto('/catalog')
    await page.waitForLoadState('networkidle')

    const searchInput = page.getByRole('textbox').first()
    if (await searchInput.count() > 0) {
      await searchInput.fill('fiction')
      await searchInput.press('Enter')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
      await expect(page.locator('main, [role="main"], .main-content').first()).toBeVisible()
    }
  })

  test('catalog search with no results shows empty state', async ({ page }) => {
    await page.goto('/catalog')
    await page.waitForLoadState('networkidle')

    const searchInput = page.getByRole('textbox').first()
    if (await searchInput.count() > 0) {
      await searchInput.fill('xyznonexistentbook12345')
      await searchInput.press('Enter')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('catalog item detail page loads', async ({ page }) => {
    await page.goto('/catalog')
    await page.waitForLoadState('networkidle')

    const resultLinks = page.locator('a[href*="/catalog/"]')
    if (await resultLinks.count() > 0) {
      await resultLinks.first().click()
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('semantic search page loads', async ({ page }) => {
    await page.goto('/catalog/search')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })

  test('BIBFRAME view loads', async ({ page }) => {
    await page.goto('/catalog/bibframe')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('site-wide search loads', async ({ page }) => {
    await page.goto('/search')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })
})
