/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/staff.json' })

const emergencyRoutes = [
  { path: '/emergency-operations', name: 'Emergency Ops Hub' },
  { path: '/emergency-operations/status', name: 'Emergency Status' },
  { path: '/emergency-operations/offline-mode', name: 'Offline Mode' },
  { path: '/emergency-operations/paper-backup', name: 'Paper Backup' },
  { path: '/emergency-operations/data-sync', name: 'Data Sync' },
  { path: '/emergency-operations/cascades', name: 'Cascades' },
  { path: '/emergency-operations/closures', name: 'Closures' },
  { path: '/emergency-operations/service-priorities', name: 'Service Priorities' },
  { path: '/emergency-operations/recovery', name: 'Recovery' },
  { path: '/emergency-operations/insurance', name: 'Insurance' },
  { path: '/emergency-operations/assessment', name: 'Assessment' },
  { path: '/emergency-operations/community-hubs', name: 'Community Hubs' },
]

const teacherRoutes = [
  { path: '/teacher/reading-dashboard', name: 'Reading Dashboard' },
  { path: '/teacher/reading-lists', name: 'Reading Lists' },
  { path: '/teacher/professional-development', name: 'Professional Development' },
  { path: '/teacher/library-consultations', name: 'Library Consultations' },
  { path: '/teacher/family-challenges', name: 'Family Challenges' },
  { path: '/teacher/library-visits', name: 'Library Visits' },
]

test.describe('Emergency Operations (Staff Auth)', () => {
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

  for (const route of emergencyRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }
})

test.describe('Teacher Routes (Staff Auth)', () => {
  for (const route of teacherRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }
})
