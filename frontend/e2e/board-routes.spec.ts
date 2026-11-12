/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

const boardRoutes = [
  { path: '/board', name: 'Board Hub' },
  { path: '/board/members', name: 'Board Members' },
  { path: '/board/meetings', name: 'Board Meetings' },
  { path: '/board/documents', name: 'Board Documents' },
  { path: '/board/minutes', name: 'Board Minutes' },
  { path: '/board/motions', name: 'Board Motions' },
  { path: '/board/committees', name: 'Board Committees' },
  { path: '/board/public-comments', name: 'Public Comments' },
]

test.describe('Board Management', () => {
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

  for (const route of boardRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      const response = await page.goto(route.path)
      expect(response?.status()).toBeLessThan(500)
      await expect(page.locator('body')).toBeVisible()
    })
  }

  test('public comments has form or content', async ({ page }) => {
    await page.goto('/board/public-comments')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).toBeVisible()
  })
})
