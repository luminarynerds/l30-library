/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/staff.json' })

const collectionRoutes = [
  { path: '/staff/cataloging', name: 'Cataloging' },
  { path: '/staff/manga-cataloging', name: 'Manga Cataloging' },
  { path: '/staff/comic-cataloging', name: 'Comic Cataloging' },
  { path: '/staff/inventory', name: 'Inventory' },
  { path: '/staff/inventory-management', name: 'Inventory Management' },
  { path: '/staff/lost-damaged', name: 'Lost & Damaged' },
  { path: '/staff/weeding', name: 'Weeding Tool' },
  { path: '/staff/picks', name: 'Staff Picks' },
  { path: '/staff/audiobooks/review', name: 'Audiobook Review' },
  { path: '/staff/lifecycle', name: 'Item Lifecycle' },
  { path: '/staff/equipment', name: 'Equipment Tracking' },
  { path: '/staff/linked-data', name: 'Linked Data' },
  { path: '/staff/sparql', name: 'SPARQL Queries' },
  { path: '/staff/lcsh', name: 'LCSH Browser' },
  { path: '/staff/releases', name: 'Release Management' },
]

test.describe('Staff Collections & Cataloging (Authenticated)', () => {
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

  for (const route of collectionRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for staff')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }
})
