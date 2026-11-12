/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

const genealogyRoutes = [
  { path: '/genealogy', name: 'Genealogy Hub' },
  { path: '/genealogy/training', name: 'Genealogy Training' },
  { path: '/genealogy/inquiry', name: 'Genealogy Inquiry' },
  { path: '/genealogy/ask-genealogist', name: 'Ask Genealogist' },
  { path: '/genealogy/archives', name: 'Community Archives' },
  { path: '/genealogy/archives/submit', name: 'Archive Submission' },
]

const legalRoutes = [
  { path: '/legal', name: 'Legal Resources' },
  { path: '/legal/calculators', name: 'Legal Calculators' },
  { path: '/banned-books', name: 'Banned Books' },
  { path: '/ban-tracker', name: 'Ban Tracker' },
  { path: '/advocacy', name: 'Advocacy' },
]

test.describe('Genealogy & Legal', () => {
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

  test.describe('Genealogy', () => {
    for (const route of genealogyRoutes) {
      test(`${route.name} (${route.path}) loads`, async ({ page }) => {
        const response = await page.goto(route.path)
        expect(response?.status()).toBeLessThan(500)
        await expect(page.locator('body')).toBeVisible()
      })
    }
  })

  test.describe('Legal', () => {
    for (const route of legalRoutes) {
      test(`${route.name} (${route.path}) loads`, async ({ page }) => {
        const response = await page.goto(route.path)
        expect(response?.status()).toBeLessThan(500)
        await expect(page.locator('body')).toBeVisible()
      })
    }

    test('legal calculators has interactive elements', async ({ page }) => {
      await page.goto('/legal/calculators')
      await page.waitForLoadState('networkidle')

      const inputs = await page.getByRole('textbox').count()
      const buttons = await page.getByRole('button').count()
      expect(inputs + buttons).toBeGreaterThan(0)
    })
  })
})
