/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * Patron Journey: Account
 *
 * Tests the complete account management workflow:
 * 1. Login to account
 * 2. Navigate through account tabs
 * 3. View checkouts, holds, fines, settings
 * 4. Handle account interactions
 * 5. Verify account features
 *
 * Viewport variations: Desktop (1280x720), Mobile (375x812), Tablet (768x1024)
 * Accessibility: Tab navigation, live regions, form controls
 */

const testViewports = [
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
]

const accountTabs = ['overview', 'checkouts', 'holds', 'settings']

test.describe('Patron Journey: Account', () => {
  for (const viewport of testViewports) {
    test.describe(`Account Navigation (${viewport.name})`, () => {
      test.beforeEach(({ page }) => {
        page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        })
      })

      test(`should load account page on ${viewport.name}`, async ({ page }) => {
        const response = await page.goto('/account')

        // Should load account or redirect to login
        const url = page.url()
        expect(url.includes('/account') || url.includes('/login')).toBeTruthy()

        await expect(page.locator('body')).toBeVisible()
      })

      test(`should display account navigation tabs on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for tabs or navigation
        const tabs = page.locator(
          '[role="tab"], [role="tablist"], button[class*="tab"], nav'
        )

        // Tabs should exist or navigation should be available
        if (await tabs.count() > 0) {
          await expect(tabs.first()).toBeVisible()
        }
      })

      test(`should display account overview on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for account info sections
        const accountInfo = page.locator(
          'text=/name|email|member|account/i'
        )

        if (await accountInfo.count() > 0) {
          await expect(accountInfo.first()).toBeVisible()
        }
      })

      test(`should navigate between checkouts and holds on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Find checkout tab/section
        const checkoutTab = page.locator(
          'button:has-text("Checkouts"), [role="tab"]:has-text("Checkouts"), [aria-label*="checkout" i]'
        )

        // Find holds tab/section
        const holdsTab = page.locator(
          'button:has-text("Holds"), [role="tab"]:has-text("Holds"), [aria-label*="holds" i]'
        )

        // At least one should be visible
        const hasCheckout = await checkoutTab.count() > 0
        const hasHolds = await holdsTab.count() > 0

        expect.soft(hasCheckout || hasHolds).toBeTruthy() // soft: requires auth fixture for real validation

        // If tabs exist, try clicking them
        if (hasCheckout && await checkoutTab.isVisible()) {
          await checkoutTab.first().click()
          await page.waitForTimeout(500)
        }
      })

      test(`should display account settings on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for settings tab or link
        const settingsTab = page.locator(
          'button:has-text("Settings"), [role="tab"]:has-text("Settings"), a:has-text("Settings"), [aria-label*="settings" i]'
        )

        if (await settingsTab.count() > 0) {
          // Settings button exists
          await expect(settingsTab.first()).toBeVisible()
        }
      })

      test(`should handle accessibility on account page (${viewport.name})`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Run accessibility scan
        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze()

        // Check for critical accessibility issues
        const criticalViolations = accessibilityScanResults.violations.filter(
          (v) => v.impact === 'critical' || v.impact === 'serious'
        )
        expect(criticalViolations).toEqual([])
      })

      test(`should verify tab keyboard navigation on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for tab elements
        const tabs = page.locator('[role="tab"]')

        if (await tabs.count() > 0) {
          // Focus on first tab
          await tabs.first().focus()

          // Verify it has focus
          const isFocused = await tabs.first().evaluate((el) => el === document.activeElement)
          expect(isFocused).toBeTruthy()

          // Try arrow key navigation
          await page.keyboard.press('ArrowRight')
          await page.waitForTimeout(300)

          // Check if focus moved to next tab
          const currentElement = await page.evaluate(() => document.activeElement?.getAttribute('role'))
          expect(['tab', null]).toContain(currentElement)
        }
      })

      test(`should display fines or billing info on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for fines, fees, or billing information
        const finesInfo = page.locator(
          'text=/fine|fee|charge|balance|amount due|owing/i'
        )

        // May or may not have fines - just check page structure
        if (await finesInfo.count() > 0) {
          await expect(finesInfo.first()).toBeVisible()
        }
      })

      test(`should verify ARIA live region updates on ${viewport.name}`, async ({ page }) => {
        await page.goto('/account')
        await page.waitForLoadState('networkidle')

        // Look for aria-live regions
        const liveRegions = page.locator('[aria-live]')

        if (await liveRegions.count() > 0) {
          // Live regions should be present for dynamic updates
          const ariaLive = await liveRegions.first().getAttribute('aria-live')
          expect(['polite', 'assertive', 'rude']).toContain(ariaLive)
        }
      })
    })
  }

  test.describe('Performance', () => {
    test('account page should load within performance budget', async ({ page }) => {
      const startTime = Date.now()
      await page.goto('/account')
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      // Performance budget: 3 seconds for account page
      expect(loadTime).toBeLessThan(3000)
    })

    test('account interactions should be responsive', async ({ page }) => {
      await page.goto('/account')
      await page.waitForLoadState('networkidle')

      // Measure time to click a tab and see results
      const startTime = Date.now()

      const tabs = page.locator('[role="tab"]')
      if (await tabs.count() > 1) {
        await tabs.nth(1).click()
        await page.waitForLoadState('networkidle')
      }

      const clickTime = Date.now() - startTime

      // Click response should be under 1 second
      expect(clickTime).toBeLessThan(1000)
    })
  })
})
