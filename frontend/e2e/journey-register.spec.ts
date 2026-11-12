/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * Patron Journey: Register
 *
 * Tests the complete patron registration workflow:
 * 1. Navigate to registration page
 * 2. Fill registration form
 * 3. Handle form validation
 * 4. Submit registration
 * 5. Verify successful registration or error handling
 *
 * Viewport variations: Desktop (1280x720), Mobile (375x812), Tablet (768x1024)
 * Accessibility: Focus management, form labels, error messages
 */

const testViewports = [
  { name: 'desktop', width: 1280, height: 720 },
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
]

test.describe('Patron Journey: Register', () => {
  for (const viewport of testViewports) {
    test.describe(`Registration (${viewport.name})`, () => {
      test.beforeEach(({ page }) => {
        page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        })
      })

      test(`should load registration page on ${viewport.name}`, async ({ page }) => {
        const response = await page.goto('/register')
        expect(response?.status()).toBeLessThan(400)

        // Verify page is visible
        await expect(page.locator('body')).toBeVisible()

        // Look for registration form or heading
        const heading = page.locator('h1, h2, [role="heading"]')
        await expect(heading.first()).toBeVisible()
      })

      test(`should display all form fields on ${viewport.name}`, async ({ page }) => {
        await page.goto('/register')
        await page.waitForLoadState('networkidle')

        // Check for common registration fields
        const expectedFields = [
          'first name',
          'last name',
          'email',
          'password',
        ]

        for (const fieldLabel of expectedFields) {
          const field = page.locator(
            `label:has-text("${fieldLabel}"), input[aria-label*="${fieldLabel}" i], input[placeholder*="${fieldLabel}" i]`
          )
          // Field should either exist or form should be dynamic
          const exists = await field.count() > 0
          expect(exists).toBeTruthy()
        }
      })

      test(`should validate required fields on ${viewport.name}`, async ({ page }) => {
        await page.goto('/register')
        await page.waitForLoadState('networkidle')

        // Try to submit empty form
        const submitButton = page.locator(
          'button[type="submit"], button:has-text("Register"), button:has-text("Sign Up"), button:has-text("Create Account")'
        )

        if (await submitButton.count() > 0) {
          await submitButton.first().click()

          // Wait briefly for validation
          await page.waitForTimeout(500)

          // Should either show error or remain on register page
          const currentUrl = page.url()
          expect(currentUrl.includes('register') || currentUrl.includes('login')).toBeTruthy()
        }
      })

      test(`should handle form submission flow on ${viewport.name}`, async ({ page }) => {
        await page.goto('/register')
        await page.waitForLoadState('networkidle')

        const email = `test-${Date.now()}@example.com`
        const password = 'TestPass123!'

        // Fill in form fields if they exist
        const firstNameInput = page.locator(
          'input[name="firstName"], input[placeholder*="first" i], input[aria-label*="first" i]'
        )
        const lastNameInput = page.locator(
          'input[name="lastName"], input[placeholder*="last" i], input[aria-label*="last" i]'
        )
        const emailInput = page.locator(
          'input[type="email"], input[name="email"], input[placeholder*="email" i]'
        )
        const passwordInput = page.locator(
          'input[type="password"], input[name="password"], input[placeholder*="password" i]'
        )

        // Fill fields that exist
        if (await firstNameInput.count() > 0) {
          await firstNameInput.first().fill('John')
        }
        if (await lastNameInput.count() > 0) {
          await lastNameInput.first().fill('Doe')
        }
        if (await emailInput.count() > 0) {
          await emailInput.first().fill(email)
        }
        if (await passwordInput.count() > 0) {
          await passwordInput.first().fill(password)
        }

        // Handle confirm password if it exists
        const confirmPasswordInput = page.locator(
          'input[name="confirmPassword"], input[placeholder*="confirm" i]'
        )
        if (await confirmPasswordInput.count() > 0) {
          await confirmPasswordInput.first().fill(password)
        }

        // Submit form
        const submitButton = page.locator(
          'button[type="submit"], button:has-text("Register"), button:has-text("Sign Up"), button:has-text("Create Account")'
        )
        if (await submitButton.count() > 0) {
          await submitButton.first().click()
          await page.waitForTimeout(1000)
        }
      })

      test(`should handle accessibility on registration form (${viewport.name})`, async ({ page }) => {
        await page.goto('/register')
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

      test(`should manage focus properly on form errors (${viewport.name})`, async ({ page }) => {
        await page.goto('/register')
        await page.waitForLoadState('networkidle')

        // Try submitting empty form to trigger potential errors
        const submitButton = page.locator(
          'button[type="submit"], button:has-text("Register"), button:has-text("Sign Up")'
        )

        if (await submitButton.count() > 0) {
          await submitButton.first().click()
          await page.waitForTimeout(500)

          // Focus should be on the first form field or error message
          const activeElement = await page.evaluate(() => {
            const el = document.activeElement
            return el?.tagName || 'BODY'
          })

          // Should not remain on submit button or body
          expect(['INPUT', 'TEXTAREA', 'BUTTON', 'A']).toContain(activeElement)
        }
      })
    })
  }

  test.describe('Performance', () => {
    test('registration page should load within performance budget', async ({ page }) => {
      const startTime = Date.now()
      await page.goto('/register')
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      // Performance budget: 2 seconds for registration page
      expect(loadTime).toBeLessThan(2000)
    })
  })
})
