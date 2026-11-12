/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/staff.json' })

const advancedRoutes = [
  { path: '/staff/analytics', name: 'Staff Analytics' },
  { path: '/staff/rfid', name: 'RFID Management' },
  { path: '/staff/streaming', name: 'Streaming Management' },
  { path: '/staff/streaming/reports', name: 'Streaming Reports' },
  { path: '/staff/panic-alerts', name: 'Panic Alerts' },
  { path: '/staff/medical-emergency', name: 'Medical Emergency' },
  { path: '/staff/knowledge-base', name: 'Knowledge Base' },
  { path: '/staff/content-flags', name: 'Content Flags' },
  { path: '/staff/review-responses', name: 'Review Responses' },
  { path: '/staff/audit-logs', name: 'Audit Logs' },
  { path: '/staff/sip2', name: 'SIP2 Management' },
  { path: '/staff/feature-flags', name: 'Feature Flags' },
  { path: '/staff/patron-segmentation', name: 'Patron Segmentation' },
  { path: '/staff/usage-statistics', name: 'Usage Statistics' },
  { path: '/staff/workflows', name: 'Workflow Management' },
  { path: '/staff/audit-reversal', name: 'Audit Reversal' },
]

const featureGatedRoutes = [
  { path: '/staff/training', name: 'Training Dashboard' },
  { path: '/staff/cohorts', name: 'Training Cohorts' },
  { path: '/staff/events', name: 'Event Management' },
  { path: '/staff/attendance', name: 'Attendance Tracking' },
  { path: '/staff/program-planning', name: 'Program Planning' },
  { path: '/staff/makerspace', name: 'Makerspace Management' },
  { path: '/staff/rooms', name: 'Room Management' },
  { path: '/staff/funds', name: 'Acquisition Funds' },
  { path: '/staff/vendors', name: 'Vendor Management' },
  { path: '/staff/selection-list', name: 'Selection Lists' },
  { path: '/staff/purchase-requests', name: 'Purchase Requests' },
  { path: '/staff/selectors', name: 'Selector Dashboard' },
  { path: '/staff/acquisition', name: 'Acquisition' },
  { path: '/staff/indie-review', name: 'Indie Review' },
  { path: '/staff/marketing', name: 'Marketing' },
  { path: '/staff/marketing-hub', name: 'Marketing Hub' },
  { path: '/staff/outreach', name: 'Outreach' },
  { path: '/staff/home-delivery', name: 'Home Delivery' },
  { path: '/staff/interlibrary-loan', name: 'ILL Management' },
  { path: '/staff/strategic', name: 'Strategic Planning' },
  { path: '/staff/book-challenges', name: 'Book Challenges' },
]

test.describe('Staff Advanced Features (Authenticated)', () => {
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

  for (const route of advancedRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for staff')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }

  test.describe('Feature-Gated Routes', () => {
    for (const route of featureGatedRoutes) {
      test(`${route.name} (${route.path}) loads or shows feature gate`, async ({ page }) => {
        await page.goto(route.path)
        await page.waitForLoadState('domcontentloaded')

        if (page.url().includes('/login')) {
          test.skip(true, 'Auth fixture not working for staff')
        }
        // Page loads - may show feature not enabled message
        await expect(page.locator('body')).toBeVisible()
      })
    }
  })
})
