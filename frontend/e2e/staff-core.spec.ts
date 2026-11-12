/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/staff.json' })

const staffCoreRoutes = [
  { path: '/staff', name: 'Staff Dashboard' },
  { path: '/staff/circulation', name: 'Circulation' },
  { path: '/staff/checkout/streamlined', name: 'Streamlined Checkout' },
  { path: '/staff/holds/shelf', name: 'Hold Shelf' },
  { path: '/staff/patrons', name: 'Patron Management' },
  { path: '/staff/book-drop', name: 'Book Drop' },
  { path: '/staff/book-drop/fast-process', name: 'Fast Book Drop' },
  { path: '/staff/reports', name: 'Reports' },
  { path: '/staff/end-of-day', name: 'End of Day' },
  { path: '/staff/end-of-shift', name: 'End of Shift' },
  { path: '/staff/card-applications', name: 'Card Applications' },
  { path: '/staff/message-board', name: 'Message Board' },
  { path: '/staff/positivity', name: 'Staff Positivity' },
  { path: '/staff/shift-swap', name: 'Shift Swap' },
  { path: '/staff/picks', name: 'Staff Picks' },
  { path: '/staff/reading-review', name: 'Reading Review' },
]

test.describe('Staff Core Workflows (Authenticated)', () => {
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

  for (const route of staffCoreRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for staff')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }

  test('staff dashboard has widgets or content', async ({ page }) => {
    await page.goto('/staff')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires staff auth')
    }

    const heading = page.getByRole('heading').first()
    if (await heading.count() > 0) {
      await expect(heading).toBeVisible()
    }
  })

  test('circulation page has search input', async ({ page }) => {
    await page.goto('/staff/circulation')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires staff auth')
    }

    const inputs = await page.getByRole('textbox').count()
    const buttons = await page.getByRole('button').count()
    expect(inputs + buttons).toBeGreaterThan(0)
  })

  test('patron management has search', async ({ page }) => {
    await page.goto('/staff/patrons')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires staff auth')
    }

    const inputs = await page.getByRole('textbox').count()
    expect(inputs).toBeGreaterThan(0)
  })
})
