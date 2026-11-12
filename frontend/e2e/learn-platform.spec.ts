/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.describe('Learning Platform', () => {
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

  test('learning hub loads', async ({ page }) => {
    await page.goto('/learn')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })

  test('course catalog loads', async ({ page }) => {
    await page.goto('/learn/catalog')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })

  test('course catalog has course cards', async ({ page }) => {
    await page.goto('/learn/catalog')
    await page.waitForLoadState('networkidle')

    const links = await page.getByRole('link').count()
    expect(links).toBeGreaterThan(0)
  })

  test('course detail page loads', async ({ page }) => {
    await page.goto('/learn/catalog')
    await page.waitForLoadState('networkidle')

    const courseLinks = page.locator('a[href*="/learn/course/"]')
    if (await courseLinks.count() > 0) {
      await courseLinks.first().click()
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    }
  })

  test('labs hub loads', async ({ page }) => {
    await page.goto('/learn/labs')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })

  test('AI Said What lab loads', async ({ page }) => {
    await page.goto('/learn/labs/ai-said-what')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('Who Wrote This lab loads', async ({ page }) => {
    await page.goto('/learn/labs/who-wrote-this')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('Fix This Prompt lab loads', async ({ page }) => {
    await page.goto('/learn/labs/fix-this-prompt')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('Real or Fake lab loads', async ({ page }) => {
    await page.goto('/learn/labs/real-or-fake')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('learning achievements loads', async ({ page }) => {
    await page.goto('/learn/achievements')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })

  test('learning analytics loads', async ({ page }) => {
    await page.goto('/learn/analytics')
    await page.waitForLoadState('domcontentloaded')
    await expect(page.locator('body')).toBeVisible()
  })
})
