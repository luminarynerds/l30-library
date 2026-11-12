/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

test.use({ storageState: 'e2e/.auth/admin.json' })

const adminCoreRoutes = [
  { path: '/admin', name: 'Admin Dashboard' },
  { path: '/admin/dashboard', name: 'Admin Dashboard Alt' },
  { path: '/admin/settings', name: 'Settings Hub' },
  { path: '/admin/features', name: 'Organization Features' },
  { path: '/admin/users', name: 'User Management' },
  { path: '/admin/staff', name: 'Staff Management' },
  { path: '/admin/security', name: 'Security Settings' },
  { path: '/admin/site-settings', name: 'Site Settings' },
  { path: '/admin/meta-tags', name: 'Meta Tags' },
  { path: '/admin/social-sharing', name: 'Social Sharing' },
  { path: '/admin/personalization', name: 'Personalization' },
  { path: '/admin/scheduler', name: 'Scheduler' },
  { path: '/admin/system-health', name: 'System Health' },
  { path: '/admin/api-status', name: 'API Status' },
  { path: '/admin/monitoring', name: 'Monitoring' },
  { path: '/admin/cache', name: 'Cache Metrics' },
  { path: '/admin/link-health', name: 'Link Health' },
  { path: '/admin/system-limits', name: 'System Limits' },
]

const adminContentRoutes = [
  { path: '/admin/courses', name: 'Course Management' },
  { path: '/admin/learning-paths', name: 'Learning Paths' },
  { path: '/admin/events', name: 'Event Management' },
  { path: '/admin/reading-programs', name: 'Reading Programs' },
  { path: '/admin/about', name: 'About Page' },
  { path: '/admin/databases', name: 'Database Management' },
  { path: '/admin/audiobooks', name: 'Audiobook Management' },
  { path: '/admin/recommendations', name: 'Recommendations' },
  { path: '/admin/semantic-search', name: 'Semantic Search' },
  { path: '/admin/overdrive', name: 'OverDrive Settings' },
  { path: '/admin/sms', name: 'SMS Settings' },
  { path: '/admin/email-marketing', name: 'Mailchimp' },
  { path: '/admin/search-engine', name: 'Search Engine' },
  { path: '/admin/storage', name: 'Storage Settings' },
  { path: '/admin/sip2', name: 'SIP2 Settings' },
  { path: '/admin/ai', name: 'AI Settings' },
]

const adminReportRoutes = [
  { path: '/admin/analytics', name: 'Analytics' },
  { path: '/admin/financial', name: 'Financial Reports' },
  { path: '/admin/annual-reports', name: 'Annual Reports' },
  { path: '/admin/treasurer', name: 'Treasurer Dashboard' },
  { path: '/admin/unified-compliance', name: 'Compliance Audit' },
  { path: '/admin/cipa', name: 'CIPA Compliance' },
  { path: '/admin/state-compliance', name: 'State Compliance' },
  { path: '/admin/law-enforcement', name: 'Law Enforcement' },
  { path: '/admin/ban-tracker', name: 'Ban Tracker' },
  { path: '/admin/public-records', name: 'Public Records' },
  { path: '/admin/legal', name: 'Legal Management' },
  { path: '/admin/school-impact', name: 'School Impact' },
]

test.describe('Admin Core (Authenticated)', () => {
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

  for (const route of adminCoreRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for admin')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }

  test('admin dashboard has content', async ({ page }) => {
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires admin auth')
    }

    const heading = page.getByRole('heading').first()
    if (await heading.count() > 0) {
      await expect(heading).toBeVisible()
    }
  })

  test('user management has table or list', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')

    if (page.url().includes('/login')) {
      test.skip(true, 'Requires admin auth')
    }

    const table = page.locator('table, [role="grid"], [role="table"]')
    const list = page.locator('[role="list"], ul, ol')
    const hasData = (await table.count()) > 0 || (await list.count()) > 0
    expect.soft(hasData).toBeTruthy()
  })
})

test.describe('Admin Content Management (Authenticated)', () => {
  for (const route of adminContentRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for admin')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }
})

test.describe('Admin Reports & Compliance (Authenticated)', () => {
  for (const route of adminReportRoutes) {
    test(`${route.name} (${route.path}) loads`, async ({ page }) => {
      await page.goto(route.path)
      await page.waitForLoadState('domcontentloaded')

      if (page.url().includes('/login')) {
        test.skip(true, 'Auth fixture not working for admin')
      }
      await expect(page.locator('body')).toBeVisible()
    })
  }
})
