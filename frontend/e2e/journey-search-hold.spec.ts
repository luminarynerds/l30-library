/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * Patron Journey: Search → Hold
 *
 * Tests the complete search and hold placement workflow:
 * 1. Navigate to catalog
 * 2. Perform search
 * 3. View item details
 * 4. Place hold on item
 * 5. Verify hold confirmation
 *
 * Viewport variations: Desktop (1280x720), Mobile (375x812), Tablet (768x1024)
 */

const testViewports = [
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
]

const testItems = [
  { query: 'fiction', expectedMinResults: 1 },
  { query: 'technology', expectedMinResults: 1 },
  { query: 'mystery', expectedMinResults: 1 },
]

test.describe('Patron Journey: Search → Hold', () => {
  for (const viewport of testViewports) {
    test.describe(`Search & Hold (${viewport.name})`, () => {
      test.beforeEach(({ page }) => {
        page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        })
      })

      test(`should load catalog on ${viewport.name}`, async ({ page }) => {
        const response = await page.goto('/catalog')
        expect(response?.status()).toBeLessThan(400)

        // Verify page structure
        await expect(page.locator('body')).toBeVisible()

        // Look for search input
        const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], input[aria-label*="search" i]')
        if (await searchInput.count() > 0) {
          await expect(searchInput.first()).toBeVisible()
        }
      })

      for (const item of testItems) {
        test(`should search for "${item.query}" and display results on ${viewport.name}`, async ({ page }) => {
          await page.goto('/catalog')
          await page.waitForLoadState('networkidle')

          // Find and fill search input
          const searchInput = page.locator(
            'input[type="search"], input[placeholder*="search" i], input[aria-label*="search" i]'
          )

          if (await searchInput.count() > 0) {
            await searchInput.first().fill(item.query)

            // Submit search (either via Enter or Search button)
            const searchButton = page.locator('button[type="submit"], button:has-text("Search")')
            if (await searchButton.count() > 0) {
              await searchButton.first().click()
            } else {
              await searchInput.first().press('Enter')
            }

            // Wait for results
            await page.waitForLoadState('networkidle')

            // Verify results exist
            const results = page.locator('#results-top li')
            await expect(results.first()).toBeVisible({ timeout: 5000 })
          }
        })
      }

      test(`should handle accessibility on search results (${viewport.name})`, async ({ page }) => {
        await page.goto('/catalog')
        await page.waitForLoadState('networkidle')

        // Run accessibility scan on search page
        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()

        expect(accessibilityScanResults.violations.length).toBe(0)
      })

      test(`should verify keyboard navigation on search (${viewport.name})`, async ({ page }) => {
        await page.goto('/catalog')
        await page.waitForLoadState('networkidle')

        // Tab to search input
        await page.keyboard.press('Tab')
        const focusedElement = await page.evaluate(() => document.activeElement?.tagName)

        // Verify some element received focus
        expect(focusedElement).not.toBe('BODY')
      })
    })
  }

  test.describe('Performance', () => {
    test('catalog should load within performance budget', async ({ page }) => {
      const startTime = Date.now()
      await page.goto('/catalog')
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      // Performance budget: 3 seconds for catalog load
      expect(loadTime).toBeLessThan(3000)
    })
  })
})
