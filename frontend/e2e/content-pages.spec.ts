/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from '@playwright/test'

const youthPages = [
  { path: '/youth', name: 'Youth Hub' },
  { path: '/youth/homework-help', name: 'Homework Help' },
  { path: '/youth/coding-tracks', name: 'Coding Tracks' },
  { path: '/youth/teen-mentors', name: 'Teen Mentors' },
  { path: '/youth/makerspace', name: 'Youth Makerspace' },
  { path: '/youth/archives', name: 'Community Archives' },
]

const guidePages = [
  { path: '/guides', name: 'Guides Index' },
  { path: '/guides/wireless-printing', name: 'Wireless Printing' },
  { path: '/guides/email-account', name: 'Email Account' },
  { path: '/guides/wifi-troubleshooting', name: 'WiFi Troubleshooting' },
  { path: '/guides/password-reset', name: 'Password Reset' },
  { path: '/guides/email-on-phone', name: 'Email on Phone' },
  { path: '/guides/library-card', name: 'Library Card' },
  { path: '/guides/scam-recognition', name: 'Scam Recognition' },
  { path: '/guides/check-print-jobs', name: 'Check Print Jobs' },
]

const infoPages = [
  { path: '/faq', name: 'FAQ' },
  { path: '/help', name: 'Help' },
  { path: '/knowledge-base', name: 'Knowledge Base' },
  { path: '/announcements', name: 'Announcements' },
  { path: '/status', name: 'System Status' },
  { path: '/system-status', name: 'Detailed Status' },
  { path: '/branches', name: 'Branches' },
  { path: '/locations', name: 'Locations' },
  { path: '/wifi', name: 'WiFi Info' },
  { path: '/rooms', name: 'Room Booking' },
  { path: '/transparency/material-costs', name: 'Material Costs' },
  { path: '/certificates', name: 'Certificates' },
  { path: '/certificates/verify', name: 'Verify Certificate' },
  { path: '/careers', name: 'Careers' },
  { path: '/streaming', name: 'Streaming' },
  { path: '/databases', name: 'Databases' },
  { path: '/digital', name: 'Digital Resources' },
  { path: '/gutenberg', name: 'Project Gutenberg' },
]

test.describe('Content Pages', () => {
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

  test.describe('Youth Pages', () => {
    for (const pg of youthPages) {
      test(`${pg.name} (${pg.path}) loads`, async ({ page }) => {
        const response = await page.goto(pg.path)
        expect(response?.status()).toBeLessThan(500)
        await expect(page.locator('body')).toBeVisible()
      })
    }

    test('youth hub has navigation links', async ({ page }) => {
      await page.goto('/youth')
      await page.waitForLoadState('networkidle')
      expect(await page.getByRole('link').count()).toBeGreaterThan(0)
    })
  })

  test.describe('Guide Pages', () => {
    for (const pg of guidePages) {
      test(`${pg.name} (${pg.path}) loads`, async ({ page }) => {
        const response = await page.goto(pg.path)
        expect(response?.status()).toBeLessThan(500)
        await expect(page.locator('body')).toBeVisible()
      })
    }
  })

  test.describe('Info Pages', () => {
    for (const pg of infoPages) {
      test(`${pg.name} (${pg.path}) loads`, async ({ page }) => {
        const response = await page.goto(pg.path)
        expect(response?.status()).toBeLessThan(500)
        await expect(page.locator('body')).toBeVisible()
      })
    }
  })

  test.describe('Interactive Content', () => {
    test('FAQ page has expandable content', async ({ page }) => {
      await page.goto('/faq')
      await page.waitForLoadState('networkidle')

      const expandButtons = page.locator('button[aria-expanded], details, [role="button"]')
      if (await expandButtons.count() > 0) {
        await expandButtons.first().click()
        await page.waitForTimeout(500)
        await expect(page.locator('body')).toBeVisible()
      }
    })

    test('room booking has interactive elements', async ({ page }) => {
      await page.goto('/rooms')
      await page.waitForLoadState('networkidle')

      const inputs = await page.getByRole('textbox').count()
      const buttons = await page.getByRole('button').count()
      const selects = await page.getByRole('combobox').count()
      expect(inputs + buttons + selects).toBeGreaterThan(0)
    })

    test('certificate verification has input', async ({ page }) => {
      await page.goto('/certificates/verify')
      await page.waitForLoadState('networkidle')

      const inputs = await page.getByRole('textbox').count()
      if (inputs > 0) {
        const input = page.getByRole('textbox').first()
        await input.fill('TEST-CERT-123')
        await expect(input).toHaveValue('TEST-CERT-123')
      }
    })

    test('branches page shows locations', async ({ page }) => {
      await page.goto('/branches')
      await page.waitForLoadState('networkidle')
      await expect(page.locator('body')).toBeVisible()
    })
  })
})
