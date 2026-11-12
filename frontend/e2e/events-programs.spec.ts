/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.describe('Events & Programs', () => {
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

  test.describe('Events', () => {
    test('events listing loads', async ({ page }) => {
      await page.goto('/events')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('events page has content or empty state', async ({ page }) => {
      await page.goto('/events')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('main, [role="main"]').first()).toBeVisible()
    })

    test('clicking event navigates to detail', async ({ page }) => {
      await page.goto('/events')
      await page.waitForLoadState('networkidle')

      const eventLinks = page.locator('a[href*="/events/"]')
      if (await eventLinks.count() > 0) {
        await eventLinks.first().click()
        await page.waitForLoadState('domcontentloaded')
        await expect(page.locator('body')).toBeVisible()
      }
    })
  })

  test.describe('Programs', () => {
    test('programs page loads', async ({ page }) => {
      await page.goto('/programs')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('reading logs page loads', async ({ page }) => {
      await page.goto('/reading-logs')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })
  })

  test.describe('Book Clubs', () => {
    test('book clubs listing loads', async ({ page }) => {
      await page.goto('/book-clubs')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('book club detail loads if clubs exist', async ({ page }) => {
      await page.goto('/book-clubs')
      await page.waitForLoadState('networkidle')

      const clubLinks = page.locator('a[href*="/book-clubs/"]')
      if (await clubLinks.count() > 0) {
        await clubLinks.first().click()
        await page.waitForLoadState('domcontentloaded')
        await expect(page.locator('body')).toBeVisible()
      }
    })
  })

  test.describe('Reading Challenges', () => {
    test('read-to-reduce page loads', async ({ page }) => {
      await page.goto('/read-to-reduce')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })

    test('learning challenge page loads', async ({ page }) => {
      await page.goto('/learning-challenge')
      await page.waitForLoadState('domcontentloaded')
      await expect(page.locator('body')).toBeVisible()
    })
  })

  test.describe('Learning Paths', () => {
    test('learning paths listing loads', async ({ page }) => {
      await page.goto('/learning-paths')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })

    test('learning path detail loads if paths exist', async ({ page }) => {
      await page.goto('/learning-paths')
      await page.waitForLoadState('networkidle')

      const pathLinks = page.locator('a[href*="/learning-paths/"]')
      if (await pathLinks.count() > 0) {
        await pathLinks.first().click()
        await page.waitForLoadState('domcontentloaded')
        await expect(page.locator('body')).toBeVisible()
      }
    })
  })
})
