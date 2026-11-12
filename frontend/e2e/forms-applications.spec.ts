/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.describe('Forms & Applications', () => {
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

  test.describe('Library Card Application', () => {
    test('card application page loads', async ({ page }) => {
      await page.goto('/card-application')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('card application has form fields', async ({ page }) => {
      await page.goto('/card-application')
      await page.waitForLoadState('networkidle')

      const inputs = await page.getByRole('textbox').count()
      const selects = await page.getByRole('combobox').count()
      const buttons = await page.getByRole('button').count()
      expect(inputs + selects + buttons).toBeGreaterThan(0)
    })

    test('card application fields are interactive', async ({ page }) => {
      await page.goto('/card-application')
      await page.waitForLoadState('networkidle')

      const nameField = page.getByLabel(/name/i).first()
      if (await nameField.count() > 0) {
        await nameField.fill('Test Applicant')
        await expect(nameField).toHaveValue('Test Applicant')
      }
    })
  })

  test.describe('Contact Form', () => {
    test('contact page loads with form', async ({ page }) => {
      await page.goto('/contact')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('contact form fields are fillable', async ({ page }) => {
      await page.goto('/contact')
      await page.waitForLoadState('networkidle')

      const nameField = page.getByLabel(/name/i).first()
      if (await nameField.count() > 0) {
        await nameField.fill('Test User')
        await expect(nameField).toHaveValue('Test User')
      }

      const emailField = page.getByLabel(/email/i).first()
      if (await emailField.count() > 0) {
        await emailField.fill('test@example.com')
        await expect(emailField).toHaveValue('test@example.com')
      }
    })
  })

  test.describe('Donation Page', () => {
    test('donate page loads', async ({ page }) => {
      await page.goto('/donate')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })
  })

  test.describe('Ask a Librarian', () => {
    test('ask-librarian page loads', async ({ page }) => {
      await page.goto('/ask-librarian')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('ask-librarian has input interface', async ({ page }) => {
      await page.goto('/ask-librarian')
      await page.waitForLoadState('networkidle')

      const inputs = await page.getByRole('textbox').count()
      const buttons = await page.getByRole('button').count()
      expect(inputs + buttons).toBeGreaterThan(0)
    })
  })

  test.describe('Other Forms', () => {
    test('share experience page loads', async ({ page }) => {
      await page.goto('/share-experience')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })

    test('suggest purchase loads', async ({ page }) => {
      await page.goto('/suggest-purchase')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })

    test('interlibrary loan loads', async ({ page }) => {
      await page.goto('/interlibrary-loan')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })
  })
})
