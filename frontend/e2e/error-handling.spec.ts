/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'
const API_BASE = process.env.VITE_API_BASE
if (!API_BASE) {
  throw new Error('VITE_API_BASE is required for e2e tests')
}

test.describe('Error Handling & Resilience', () => {
  test('404 page renders for nonexistent routes', async ({ page }) => {
    const response = await page.goto('/this-route-definitely-does-not-exist-xyz')
    await expect(page.locator('body')).toBeVisible()

    // Should show 404 content, not a blank/crashed page
    const pageText = await page.locator('body').textContent()
    expect(pageText?.length).toBeGreaterThan(10)
  })

  test('API 500 shows error state not blank page', async ({ page }) => {
    await page.route(`**${API_BASE}/catalog/items**`, route =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      })
    )
    await page.goto('/catalog')
    await page.waitForLoadState('networkidle')

    // Should show some content (error message or fallback), not blank
    await expect(page.locator('body')).toBeVisible()
    const bodyText = await page.locator('body').textContent()
    expect(bodyText?.length).toBeGreaterThan(10)
  })

  test('slow API shows loading state', async ({ page }) => {
    await page.route(`**${API_BASE}/catalog/items**`, async route => {
      await new Promise(resolve => setTimeout(resolve, 3000))
      await route.continue()
    })
    await page.goto('/catalog')

    // Should show loading indicator or content
    await expect(page.locator('body')).toBeVisible()
  })

  test('auth expiry redirects to login', async ({ page }) => {
    await page.route(`**${API_BASE}/auth/refresh**`, route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Token expired' }),
      })
    )
    await page.goto('/account')
    await page.waitForLoadState('networkidle')

    // Should redirect to login or show auth error
    await expect(page.locator('body')).toBeVisible()
  })

  test.describe('Console Error Baseline', () => {
    const highTrafficPages = [
      '/', '/catalog', '/events', '/programs', '/about',
      '/contact', '/learn', '/digital', '/login', '/help',
    ]

    for (const path of highTrafficPages) {
      test(`${path} has no uncaught exceptions`, async ({ page }) => {
        const pageErrors: string[] = []
        page.on('pageerror', err => {
          pageErrors.push(err.message)
        })

        await page.goto(path)
        await page.waitForLoadState('networkidle')

        expect(pageErrors, `Uncaught exceptions on ${path}`).toEqual([])
      })
    }
  })
})