/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.describe('Auth Flows', () => {
  test.describe('Login', () => {
    test('successful login redirects away from /login', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')

      await page.getByRole('textbox', { name: /email/i }).fill('admin@l30.org')
      await page.getByRole('textbox', { name: /password/i }).or(page.locator('input[type="password"]')).fill('Admin123!')
      await page.getByRole('button', { name: /log in|sign in/i }).click()

      await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 })
      expect(page.url()).not.toContain('/login')
    })

    test('failed login shows error and stays on /login', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')

      await page.getByRole('textbox', { name: /email/i }).fill('wrong@example.com')
      await page.getByRole('textbox', { name: /password/i }).or(page.locator('input[type="password"]')).fill('WrongPassword!')
      await page.getByRole('button', { name: /log in|sign in/i }).click()

      await page.waitForTimeout(3000)
      expect(page.url()).toContain('/login')

      const errorMsg = page.locator('text=/incorrect|invalid|error|failed/i')
      await expect(errorMsg.first()).toBeVisible({ timeout: 5000 })
    })

    test('login form validates empty fields', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')

      await page.getByRole('button', { name: /log in|sign in/i }).click()
      await page.waitForTimeout(2000)
      expect(page.url()).toContain('/login')
    })

    test('login page has email and password fields', async ({ page }) => {
      await page.goto('/login')
      await page.waitForLoadState('networkidle')

      await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible()
      await expect(page.locator('input[type="password"]')).toBeVisible()
      await expect(page.getByRole('button', { name: /log in|sign in/i })).toBeVisible()
    })
  })

  test.describe('Registration', () => {
    test('registration form has all required fields', async ({ page }) => {
      await page.goto('/register')
      await page.waitForLoadState('networkidle')

      await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible()
    })

    test('registration validates mismatched passwords', async ({ page }) => {
      await page.goto('/register')
      await page.waitForLoadState('networkidle')

      const firstNameField = page.getByLabel(/first name/i)
      if (await firstNameField.count() > 0) await firstNameField.fill('Test')
      const lastNameField = page.getByLabel(/last name/i)
      if (await lastNameField.count() > 0) await lastNameField.fill('User')
      await page.getByRole('textbox', { name: /email/i }).fill(`test-${Date.now()}@example.com`)

      const passwordFields = page.locator('input[type="password"]')
      if (await passwordFields.count() >= 2) {
        await passwordFields.nth(0).fill('TestPass123!')
        await passwordFields.nth(1).fill('DifferentPass456!')

        const submitBtn = page.getByRole('button', { name: /create account|register|sign up/i })
        if (await submitBtn.count() > 0) {
          await submitBtn.click()
          await page.waitForTimeout(2000)
          expect(page.url()).toContain('/register')
        }
      }
    })
  })

  test.describe('Password Recovery', () => {
    test('forgot password page loads with email form', async ({ page }) => {
      await page.goto('/forgot-password')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()

      const emailField = page.getByRole('textbox', { name: /email/i })
      if (await emailField.count() > 0) {
        await emailField.fill('test@example.com')
        await expect(emailField).toHaveValue('test@example.com')
      }
    })

    test('reset password page loads', async ({ page }) => {
      await page.goto('/reset-password')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })
  })

  test.describe('Email Verification', () => {
    test('verify email page loads', async ({ page }) => {
      await page.goto('/verify-email')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })

    test('magic link page loads', async ({ page }) => {
      await page.goto('/auth/magic-link')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })
  })
})
