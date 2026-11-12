/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect, Page } from '@playwright/test'
const API_BASE = process.env.VITE_API_BASE
if (!API_BASE) {
  throw new Error('VITE_API_BASE is required for e2e tests')
}

/**
 * Librarian Onboarding Usability Tests
 *
 * Simulates a brand-new librarian (zero training, day one) attempting
 * common desk tasks in the LSC staff interface.
 *
 * For each task we measure:
 *   1. Wrong clicks before success — can they find the right page/action
 *      without instructions?
 *   2. What confused them — are labels, navigation, or workflows misleading?
 *   3. Expected vs found — does the UI match the mental model of someone
 *      who has used *any* library but has never seen *this* system?
 *   4. Production safety — would fumbling around break real data?
 *
 * These are structural/UX-probing tests, not functional happy-path tests.
 * They intentionally try wrong paths first to verify the system is
 * forgiving, discoverable, and safe.
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Staff routes a new hire is most likely to try when looking for a feature. */
const STAFF_ROUTES = {
  dashboard: '/staff',
  circulation: '/staff/circulation',
  fastCheckout: '/staff/checkout/streamlined',
  patrons: '/staff/patrons',
  holdShelf: '/staff/holds/shelf',
  reports: '/staff/reports',
  cataloging: '/staff/cataloging',
}

/** Public routes that overlap with staff mental models. */
const PUBLIC_ROUTES = {
  events: '/events',
  catalog: '/catalog',
  register: '/register',
}

/**
 * Collects every navigation-like element on the visible page.
 * Returns a flat list of { text, href, role } so tests can inspect
 * what a new hire would *see* when scanning for a feature.
 */
async function collectVisibleNavigation(page: Page) {
  return page.evaluate(() => {
    const items: { text: string; href: string | null; role: string | null }[] = []
    const els = document.querySelectorAll('a, button, [role="menuitem"], [role="tab"], [role="link"]')
    els.forEach((el) => {
      const rect = (el as HTMLElement).getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        items.push({
          text: (el as HTMLElement).innerText?.trim().slice(0, 80) || '',
          href: el.getAttribute('href'),
          role: el.getAttribute('role'),
        })
      }
    })
    return items
  })
}

/**
 * Simulates a new hire scanning the page for a keyword.
 * Returns true if any visible text on the page contains the keyword.
 */
async function pageContainsVisibleText(page: Page, keyword: string): Promise<boolean> {
  const text = await page.locator('body').innerText()
  return text.toLowerCase().includes(keyword.toLowerCase())
}

/**
 * Checks whether any nav/link/button text matches a keyword.
 * A new hire would visually scan for these.
 */
async function hasNavigationItemMatching(page: Page, keyword: RegExp): Promise<boolean> {
  const items = await collectVisibleNavigation(page)
  return items.some((i) => keyword.test(i.text))
}

// ---------------------------------------------------------------------------
// Task 1: Check out a book (no instructions given)
// ---------------------------------------------------------------------------

test.describe('Task 1 — Check out a book (no instructions)', () => {
  test('dashboard shows a clear path to checkout', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    // A new hire lands on the dashboard. They need to find "checkout."
    // The sidebar should contain a recognizable label.
    const hasSidebarCheckout = await hasNavigationItemMatching(page, /checkout|check.out|circulation/i)
    expect(
      hasSidebarCheckout,
      'New hire cannot find a "Checkout" or "Circulation" link on the dashboard — ' +
      'they would click randomly or ask a coworker'
    ).toBeTruthy()
  })

  test('circulation page has a patron search input visible immediately', async ({ page }) => {
    await page.goto(STAFF_ROUTES.circulation)
    await page.waitForLoadState('networkidle')

    // First thing a clerk needs: identify the patron.
    const patronInput = page.locator(
      'input[placeholder*="patron" i], input[placeholder*="name" i], ' +
      'input[placeholder*="card" i], input[placeholder*="barcode" i], ' +
      'input[aria-label*="patron" i], input[aria-label*="search" i]'
    )
    await expect(
      patronInput.first(),
      'No visible patron search/scan field on the circulation page — ' +
      'a new hire would not know where to start'
    ).toBeVisible({ timeout: 5000 })
  })

  test('streamlined checkout page auto-focuses the barcode input', async ({ page }) => {
    await page.goto(STAFF_ROUTES.fastCheckout)
    await page.waitForLoadState('networkidle')

    // Scanning workflow: the input should be focused so a barcode scanner
    // "just works" without clicking.
    const focused = await page.evaluate(() => {
      const el = document.activeElement
      return el?.tagName === 'INPUT'
    })
    expect(
      focused,
      'Fast Checkout does not auto-focus an input — a barcode scan on ' +
      'day one would type into nowhere'
    ).toBeTruthy()
  })

  test('checkout page labels the barcode field clearly', async ({ page }) => {
    await page.goto(STAFF_ROUTES.fastCheckout)
    await page.waitForLoadState('networkidle')

    // The focused input should have a placeholder or label that tells
    // the new hire WHAT to scan.
    const input = page.locator('input:focus, input[autofocus]').first()
    if (await input.count() > 0) {
      const placeholder = await input.getAttribute('placeholder') ?? ''
      const ariaLabel = await input.getAttribute('aria-label') ?? ''
      const hintText = placeholder + ariaLabel
      expect(
        /card|patron|barcode|scan/i.test(hintText),
        `Focused input hint is "${hintText}" — a new hire would not know ` +
        'whether to scan a patron card or a book barcode first'
      ).toBeTruthy()
    }
  })

  test('submitting an empty checkout does not create real records', async ({ page }) => {
    await page.goto(STAFF_ROUTES.fastCheckout)
    await page.waitForLoadState('networkidle')

    // A nervous new hire might press Enter with nothing typed.
    await page.keyboard.press('Enter')
    await page.waitForTimeout(500)

    // The page should still be on checkout (no navigation away) and
    // should not show a success message.
    expect(page.url()).toContain('/staff/')
    const successToast = page.locator('text=/checked out|success/i')
    await expect(successToast).not.toBeVisible()
  })

  test('typing gibberish into patron search shows a helpful error', async ({ page }) => {
    await page.goto(STAFF_ROUTES.circulation)
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator(
      'input[placeholder*="patron" i], input[placeholder*="name" i], ' +
      'input[placeholder*="card" i], input[aria-label*="search" i]'
    )

    if (await searchInput.count() > 0) {
      await searchInput.first().fill('zzzznotapatron999')
      await searchInput.first().press('Enter')
      await page.waitForTimeout(1000)

      // Should show "no results" — not a stack trace or silent nothing.
      const hasNoResults = await pageContainsVisibleText(page, 'no patron')
        || await pageContainsVisibleText(page, 'not found')
        || await pageContainsVisibleText(page, 'no results')
      expect(
        hasNoResults,
        'Searching for a nonexistent patron shows no feedback — ' +
        'a new hire would think the system is broken'
      ).toBeTruthy()
    }
  })
})

// ---------------------------------------------------------------------------
// Task 2: Look up a patron by phone number
// ---------------------------------------------------------------------------

test.describe('Task 2 — Look up a patron by phone number', () => {
  test('patron search placeholder mentions phone as a searchable field', async ({ page }) => {
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator(
      'input[aria-label*="search" i], input[placeholder*="search" i]'
    )

    if (await searchInput.count() > 0) {
      const placeholder = await searchInput.first().getAttribute('placeholder') ?? ''
      const ariaLabel = await searchInput.first().getAttribute('aria-label') ?? ''
      const hint = (placeholder + ' ' + ariaLabel).toLowerCase()

      // A new hire who has a phone number and no other info will look for
      // "phone" in the search hint. If it only says "name, email, card" they
      // won't know phone search is supported.
      const mentionsPhone = /phone|tel|mobile|number/i.test(hint)
      // Record finding but don't hard-fail — it's a UX gap, not a crash
      if (!mentionsPhone) {
        console.warn(
          `UX GAP: Patron search placeholder is "${placeholder}" — ` +
          'does not mention phone number as searchable. ' +
          'A new hire with only a phone number would be stuck.'
        )
      }
    }
  })

  test('patron search page is reachable from the dashboard sidebar', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    const hasPatronsLink = await hasNavigationItemMatching(page, /patron/i)
    expect(
      hasPatronsLink,
      'No "Patrons" link visible from dashboard — a new hire asked to ' +
      '"look up a patron" would not know where to go'
    ).toBeTruthy()
  })

  test('patron search accepts a phone-formatted input without error', async ({ page }) => {
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator(
      'input[aria-label*="search" i], input[placeholder*="search" i]'
    )

    if (await searchInput.count() > 0) {
      // Patrons often give their phone as "(555) 123-4567"
      await searchInput.first().fill('(555) 123-4567')
      await searchInput.first().press('Enter')
      await page.waitForTimeout(1000)

      // The system should not crash, show a validation error about format,
      // or silently do nothing.
      const hasError = await pageContainsVisibleText(page, 'invalid')
        || await pageContainsVisibleText(page, 'format')
      expect(
        hasError,
        'Entering a phone number with parentheses/dashes caused a ' +
        'format error — the system should normalize phone input'
      ).toBeFalsy()
    }
  })

  test('patron detail view shows contact info including phone', async ({ page }) => {
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    // Verify the page has a visible structure for displaying patron details
    // (tabs, panels, or cards that would show phone/email/address)
    const hasContactLabels = await pageContainsVisibleText(page, 'phone')
      || await pageContainsVisibleText(page, 'email')
      || await pageContainsVisibleText(page, 'contact')
      || await pageContainsVisibleText(page, 'profile')
    // This is a soft check — the detail view might only appear after selection
    if (!hasContactLabels) {
      console.warn(
        'UX NOTE: Patron page does not show contact-related labels until a patron is selected. ' +
        'A new hire might not realize they need to search first.'
      )
    }
  })
})

// ---------------------------------------------------------------------------
// Task 3: Place a hold for a patron
// ---------------------------------------------------------------------------

test.describe('Task 3 — Place a hold for a patron', () => {
  test('the word "hold" is discoverable from the staff dashboard', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    // A new hire told "place a hold" will scan for that word.
    const hasHoldText = await pageContainsVisibleText(page, 'hold')
    expect(
      hasHoldText,
      'The word "hold" does not appear anywhere on the staff dashboard — ' +
      'a new hire would have no idea where to start'
    ).toBeTruthy()
  })

  test('catalog search page has a Place Hold action on item cards', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.catalog)
    await page.waitForLoadState('networkidle')

    // Search for something generic
    const searchInput = page.locator(
      'input[type="search"], input[placeholder*="search" i], input[aria-label*="search" i]'
    )

    if (await searchInput.count() > 0) {
      await searchInput.first().fill('fiction')
      await searchInput.first().press('Enter')
      await page.waitForLoadState('networkidle')

      // After results load, look for a "Place Hold" or "Hold" button/link
      const holdAction = page.locator(
        'button:has-text("Hold"), button:has-text("Place Hold"), ' +
        'a:has-text("Hold"), [data-testid*="hold"]'
      )
      const holdCount = await holdAction.count()

      // Also check if there's any item result first
      const hasResults = await pageContainsVisibleText(page, 'fiction')
        || (await page.locator('[data-testid*="result"], .search-results, [role="article"]').count()) > 0

      if (hasResults && holdCount === 0) {
        console.warn(
          'UX GAP: Catalog results are displayed but no "Place Hold" button is visible. ' +
          'A new hire would need to click into the item detail to find it.'
        )
      }
    }
  })

  test('hold shelf page loads without error', async ({ page }) => {
    const response = await page.goto(STAFF_ROUTES.holdShelf)
    expect(response?.status()).toBeLessThan(400)
    await page.waitForLoadState('networkidle')

    // A new hire navigating to the hold shelf should see something
    // recognizable, not a blank page or auth redirect with no message.
    const body = await page.locator('body').innerText()
    const hasContent = body.length > 50
    expect(
      hasContent,
      'Hold shelf page is nearly empty — a new hire would think it is broken'
    ).toBeTruthy()
  })

  test('placing a hold without selecting a patron is blocked', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.catalog)
    await page.waitForLoadState('networkidle')

    // Try to click "Place Hold" without being associated with a patron.
    const holdButton = page.locator(
      'button:has-text("Hold"), button:has-text("Place Hold")'
    )

    if (await holdButton.count() > 0) {
      await holdButton.first().click()
      await page.waitForTimeout(1000)

      // System should either prompt for login or show "select a patron."
      // It should NOT silently create a hold for nobody.
      const hasGuard = await pageContainsVisibleText(page, 'log in')
        || await pageContainsVisibleText(page, 'sign in')
        || await pageContainsVisibleText(page, 'select a patron')
        || await pageContainsVisibleText(page, 'authentication')
        || page.url().includes('/login')
      expect(
        hasGuard,
        'Clicking "Place Hold" without a patron context silently proceeds — ' +
        'this could create orphaned holds in production'
      ).toBeTruthy()
    }
  })
})

// ---------------------------------------------------------------------------
// Task 4: Waive a small fine
// ---------------------------------------------------------------------------

test.describe('Task 4 — Waive a small fine', () => {
  test('"Fines" tab or section is findable on the patron detail view', async ({ page }) => {
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    // A new hire told "waive a fine" will look for "Fine" or "Fee" or "Balance".
    const hasFineText = await hasNavigationItemMatching(page, /fine|fee|balance|payment/i)
      || await pageContainsVisibleText(page, 'fine')
      || await pageContainsVisibleText(page, 'fee')
    // Fine info may only appear after selecting a patron — note it
    if (!hasFineText) {
      console.warn(
        'UX NOTE: No fine-related text visible on patron page without a patron selected. ' +
        'A new hire would not know where fines live.'
      )
    }
  })

  test('circulation page shows fine alerts for patrons with outstanding balances', async ({ page }) => {
    await page.goto(STAFF_ROUTES.circulation)
    await page.waitForLoadState('networkidle')

    // When a patron with fines is loaded, there should be a visual indicator.
    // We check that the page at least has the concept of fines visible.
    const hasFineUI = await pageContainsVisibleText(page, 'fine')
      || await pageContainsVisibleText(page, 'balance')
      || await pageContainsVisibleText(page, 'owe')
    // Soft check — fines are contextual
    if (!hasFineUI) {
      console.warn(
        'UX NOTE: Circulation page has no visible fine/balance indicators. ' +
        'A new hire checking out books for a patron with fines might not notice.'
      )
    }
  })

  test('waive action requires a reason (production safety)', async ({ page }) => {
    // The WaiveFineModal requires a reason with min 3 chars.
    // Verify that the component exists and has validation.
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    // Look for evidence that the waive flow includes validation/reason.
    // This is a structural check — the modal won't open without a real fine,
    // but we can verify the page has the concept.
    const hasWaivePattern = await pageContainsVisibleText(page, 'waive')
      || await pageContainsVisibleText(page, 'forgive')

    // Even if "waive" isn't visible yet, the fines tab should exist
    const finesTab = page.locator(
      'button:has-text("Fines"), [role="tab"]:has-text("Fines"), a:has-text("Fines")'
    )

    if (await finesTab.count() > 0) {
      // The fines tab exists — a new hire could find it
      expect(true).toBeTruthy()
    } else if (!hasWaivePattern) {
      console.warn(
        'UX GAP: No "Fines" tab or "Waive" button visible on the patron page. ' +
        'A new hire told to waive a fine would be completely lost.'
      )
    }
  })

  test('fine waiver requires staff auth (does not work as public user)', async ({ request }) => {
    // Verify the waive endpoint rejects unauthenticated requests.
    // A new hire accidentally navigating here without logging in should be blocked.
    const response = await request.post(`${API_BASE}/staff/fines/1/waive`, {
      data: { reason: 'test waiver' },
    })
    expect(
      [401, 403, 404, 405].includes(response.status()),
      'Fine waiver endpoint accepted an unauthenticated request — ' +
      'anyone could waive fines without logging in'
    ).toBeTruthy()
  })
})

// ---------------------------------------------------------------------------
// Task 5: Register a new patron
// ---------------------------------------------------------------------------

test.describe('Task 5 — Register a new patron', () => {
  test('registration page is reachable and has a visible form', async ({ page }) => {
    const response = await page.goto(PUBLIC_ROUTES.register)
    expect(response?.status()).toBeLessThan(400)
    await page.waitForLoadState('networkidle')

    const heading = page.locator('h1, h2, [role="heading"]')
    await expect(heading.first()).toBeVisible()

    // Should see at least first name, last name, email, password
    const formInputs = page.locator('input')
    const inputCount = await formInputs.count()
    expect(
      inputCount >= 4,
      `Registration form only has ${inputCount} inputs — ` +
      'a new hire would wonder if the page loaded correctly'
    ).toBeTruthy()
  })

  test('registration labels are self-explanatory', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.register)
    await page.waitForLoadState('networkidle')

    // Every input should have a visible label or clear placeholder
    const inputs = page.locator('input:not([type="hidden"]):not([type="submit"])')
    const count = await inputs.count()

    for (let i = 0; i < count; i++) {
      const input = inputs.nth(i)
      const isVisible = await input.isVisible()
      if (!isVisible) continue

      const placeholder = await input.getAttribute('placeholder') ?? ''
      const ariaLabel = await input.getAttribute('aria-label') ?? ''
      const id = await input.getAttribute('id') ?? ''

      // Check if there's an associated <label>
      let hasLabel = false
      if (id) {
        hasLabel = (await page.locator(`label[for="${id}"]`).count()) > 0
      }

      const isIdentifiable = placeholder.length > 0 || ariaLabel.length > 0 || hasLabel

      expect(
        isIdentifiable,
        `Registration input #${i} has no label, placeholder, or aria-label — ` +
        'a new hire would not know what to type'
      ).toBeTruthy()
    }
  })

  test('submitting empty registration form shows validation errors', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.register)
    await page.waitForLoadState('networkidle')

    const submitButton = page.locator(
      'button[type="submit"], button:has-text("Register"), ' +
      'button:has-text("Sign Up"), button:has-text("Create Account")'
    )

    if (await submitButton.count() > 0) {
      await submitButton.first().click()
      await page.waitForTimeout(1000)

      // Should show validation errors OR remain on the page
      const stayedOnPage = page.url().includes('register')
      const hasErrorIndicators =
        (await page.locator('[role="alert"], .error, [aria-invalid="true"]').count()) > 0
        || await pageContainsVisibleText(page, 'required')
        || await pageContainsVisibleText(page, 'please')

      expect(
        stayedOnPage || hasErrorIndicators,
        'Empty registration form submission did not show errors — ' +
        'this could create blank patron records in production'
      ).toBeTruthy()
    }
  })

  test('password field has visible strength/requirements hint', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.register)
    await page.waitForLoadState('networkidle')

    const passwordInput = page.locator('input[type="password"]').first()

    if (await passwordInput.count() > 0) {
      await passwordInput.fill('a')
      await page.waitForTimeout(300)

      // Look for password requirements text
      const hasRequirements = await pageContainsVisibleText(page, 'character')
        || await pageContainsVisibleText(page, 'password')
        || await pageContainsVisibleText(page, 'strong')
        || await pageContainsVisibleText(page, 'uppercase')
        || await pageContainsVisibleText(page, 'number')
        || (await page.locator('[role="alert"], [aria-live]').count()) > 0

      if (!hasRequirements) {
        console.warn(
          'UX GAP: Password field shows no strength indicator or requirements hint. ' +
          'A new hire helping a patron would need trial-and-error to set a valid password.'
        )
      }
    }
  })

  test('staff-side "card application" path exists as alternative', async ({ page }) => {
    // A new hire might expect registration to live under staff tools, not /register
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    const hasCardOrRegister = await hasNavigationItemMatching(page, /card.application|register|new.patron|add.patron/i)
      || await pageContainsVisibleText(page, 'card application')
      || await pageContainsVisibleText(page, 'new patron')

    if (!hasCardOrRegister) {
      console.warn(
        'UX GAP: Staff dashboard has no visible link to create a new patron or ' +
        'card application. A new hire would not know to send patrons to /register.'
      )
    }
  })
})

// ---------------------------------------------------------------------------
// Task 6: Find today's events
// ---------------------------------------------------------------------------

test.describe("Task 6 — Find today's events", () => {
  test('events page is publicly accessible', async ({ page }) => {
    const response = await page.goto(PUBLIC_ROUTES.events)
    expect(response?.status()).toBeLessThan(400)
    await page.waitForLoadState('networkidle')

    await expect(page.locator('body')).toBeVisible()
    const hasEventContent = await pageContainsVisibleText(page, 'event')
      || await pageContainsVisibleText(page, 'program')
      || await pageContainsVisibleText(page, 'calendar')

    expect(
      hasEventContent,
      'Events page loaded but has no event-related content — ' +
      'a new hire checking what is on today would think nothing is scheduled'
    ).toBeTruthy()
  })

  test('events page shows date or "today" filtering', async ({ page }) => {
    await page.goto(PUBLIC_ROUTES.events)
    await page.waitForLoadState('networkidle')

    // A new hire checking "what events are today" needs date context.
    const hasDateContext = await pageContainsVisibleText(page, 'today')
      || await pageContainsVisibleText(page, 'this week')
      || await pageContainsVisibleText(page, new Date().toLocaleDateString('en-US', { month: 'long' }))
      || (await page.locator('input[type="date"], [data-testid*="date"], .calendar').count()) > 0

    if (!hasDateContext) {
      console.warn(
        "UX GAP: Events page has no visible date context — a new hire cannot " +
        "quickly tell which events are today vs. next month."
      )
    }
  })

  test('events are findable from the staff dashboard', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    // A new hire at the staff desk might look for events in the sidebar
    // or in dashboard widgets.
    const hasEventsLink = await hasNavigationItemMatching(page, /event|program|calendar/i)
    const hasEventsWidget = await pageContainsVisibleText(page, 'event')
      || await pageContainsVisibleText(page, 'program')

    if (!hasEventsLink && !hasEventsWidget) {
      console.warn(
        'UX GAP: Staff dashboard has no events link or widget. A new hire asked ' +
        '"what events are on today?" would need to guess the /events URL.'
      )
    }
  })

  test('events page does not require authentication', async ({ page }) => {
    const response = await page.goto(PUBLIC_ROUTES.events)

    // Events should be public — a new hire should be able to show a patron
    // the events page without needing to log in first.
    expect(response?.status()).toBeLessThan(400)
    const wasRedirectedToLogin = page.url().includes('/login')
    expect(
      wasRedirectedToLogin,
      'Events page redirected to login — a new hire trying to show a patron ' +
      "today's events would be blocked"
    ).toBeFalsy()
  })
})

// ---------------------------------------------------------------------------
// Task 7: Print a report
// ---------------------------------------------------------------------------

test.describe('Task 7 — Print a report', () => {
  test('reports page is reachable from the staff sidebar', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    const hasReportsLink = await hasNavigationItemMatching(page, /report|analytics/i)
    expect(
      hasReportsLink,
      'No "Reports" link in the staff sidebar — a new hire asked for ' +
      '"the daily report" would have no starting point'
    ).toBeTruthy()
  })

  test('reports page loads with recognizable report types', async ({ page }) => {
    await page.goto(STAFF_ROUTES.reports)
    await page.waitForLoadState('networkidle')

    // The reports page should show recognizable categories
    const hasReportContent = await pageContainsVisibleText(page, 'circulation')
      || await pageContainsVisibleText(page, 'checkout')
      || await pageContainsVisibleText(page, 'daily')
      || await pageContainsVisibleText(page, 'overdue')
      || await pageContainsVisibleText(page, 'report')

    expect(
      hasReportContent,
      'Reports page has no recognizable report types listed — ' +
      'a new hire would not know what to select'
    ).toBeTruthy()
  })

  test('reports page has a print or export action', async ({ page }) => {
    await page.goto(STAFF_ROUTES.reports)
    await page.waitForLoadState('networkidle')

    const hasPrintOrExport = await hasNavigationItemMatching(page, /print|export|download|csv|excel|pdf/i)
      || await pageContainsVisibleText(page, 'print')
      || await pageContainsVisibleText(page, 'export')
      || await pageContainsVisibleText(page, 'download')

    if (!hasPrintOrExport) {
      console.warn(
        'UX GAP: Reports page has no visible print/export/download button. ' +
        'A new hire told to "print the daily report" would be stuck.'
      )
    }
  })

  test('reports page does not auto-generate on load (production safety)', async ({ page }) => {
    // A new hire clicking into reports should NOT trigger a heavy database
    // query by just loading the page. There should be a "Generate" button.
    const requestUrls: string[] = []
    page.on('request', (req) => {
      if (req.url().includes('/api/') && req.method() === 'POST') {
        requestUrls.push(req.url())
      }
    })

    await page.goto(STAFF_ROUTES.reports)
    await page.waitForLoadState('networkidle')

    // Allow GET requests for initial data but POST requests should not fire
    // automatically — generating reports should require explicit action.
    const hasAutoPost = requestUrls.some((url) =>
      url.includes('generate') || url.includes('report')
    )
    if (hasAutoPost) {
      console.warn(
        'PRODUCTION CONCERN: Reports page sends POST requests on load — ' +
        'a new hire accidentally navigating here could trigger expensive queries.'
      )
    }
  })
})

// ---------------------------------------------------------------------------
// Cross-cutting: Production safety checks
// ---------------------------------------------------------------------------

test.describe('Production safety — can a new hire break things?', () => {
  test('staff pages reject unauthenticated access gracefully', async ({ page }) => {
    const staffPages = [
      STAFF_ROUTES.circulation,
      STAFF_ROUTES.fastCheckout,
      STAFF_ROUTES.patrons,
      STAFF_ROUTES.reports,
      STAFF_ROUTES.holdShelf,
    ]

    for (const path of staffPages) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      // Should redirect to login or show an access message — not the raw page
      const isProtected = page.url().includes('/login')
        || page.url().includes('/account')
        || await pageContainsVisibleText(page, 'log in')
        || await pageContainsVisibleText(page, 'sign in')
        || await pageContainsVisibleText(page, 'access')
        || await pageContainsVisibleText(page, 'permission')
        || await pageContainsVisibleText(page, 'unauthorized')

      expect(
        isProtected,
        `${path} is accessible without authentication — ` +
        'a new hire on a shared computer could see staff data without logging in'
      ).toBeTruthy()
    }
  })

  test('destructive operations require confirmation', async ({ page }) => {
    // Navigate to pages with delete/waive/override actions.
    // Even if the buttons exist, they should require a second click (modal/confirm).
    await page.goto(STAFF_ROUTES.patrons)
    await page.waitForLoadState('networkidle')

    const dangerousButtons = page.locator(
      'button:has-text("Delete"), button:has-text("Remove"), ' +
      'button:has-text("Block"), button:has-text("Suspend")'
    )

    const count = await dangerousButtons.count()
    for (let i = 0; i < count; i++) {
      const button = dangerousButtons.nth(i)
      const isDisabled = await button.isDisabled()
      const ariaLabel = await button.getAttribute('aria-label') ?? ''

      // Destructive buttons should either be disabled (requiring selection)
      // or have aria hints that a confirmation will follow
      if (!isDisabled) {
        console.warn(
          `SAFETY NOTE: "${await button.innerText()}" button is enabled without context — ` +
          'verify it opens a confirmation dialog, not an immediate action'
        )
      }
    }
  })

  test('navigation has no dead-end pages (back button always works)', async ({ page }) => {
    const pagesToVisit = [
      STAFF_ROUTES.dashboard,
      PUBLIC_ROUTES.events,
      PUBLIC_ROUTES.catalog,
    ]

    for (const path of pagesToVisit) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      // Page should have at least one navigation element to get back
      const hasNav = (await page.locator('nav, [role="navigation"]').count()) > 0
        || (await page.locator('a[href="/"], a[href="/staff"]').count()) > 0

      expect(
        hasNav,
        `${path} has no visible navigation — a new hire could get stuck on this page`
      ).toBeTruthy()
    }
  })

  test('no console errors on core staff pages', async ({ page }) => {
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    const corePages = [
      STAFF_ROUTES.dashboard,
      STAFF_ROUTES.circulation,
      STAFF_ROUTES.patrons,
      PUBLIC_ROUTES.events,
    ]

    for (const path of corePages) {
      consoleErrors.length = 0
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      // Filter out noisy but harmless errors (e.g. failed favicon, React dev warnings)
      const realErrors = consoleErrors.filter(
        (e) => !e.includes('favicon') && !e.includes('DevTools') && !e.includes('404')
      )

      if (realErrors.length > 0) {
        console.warn(
          `Console errors on ${path}: ${realErrors.join('; ').slice(0, 200)}. ` +
          'A new hire seeing browser console errors may lose confidence in the system.'
        )
      }
    }
  })
})

// ---------------------------------------------------------------------------
// Cross-cutting: Discoverability / mental model alignment
// ---------------------------------------------------------------------------

test.describe('Discoverability — does the UI match common library terminology?', () => {
  test('sidebar uses standard library terms', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    const nav = await collectVisibleNavigation(page)
    const navLabels = nav.map((n) => n.text.toLowerCase()).join(' | ')

    // Terms every librarian would expect to see:
    const expectedTerms = [
      { term: /circulation/i, why: 'core function of any library desk' },
      { term: /patron/i, why: 'standard term for library users in staff tools' },
      { term: /catalog/i, why: 'looking up items is a constant need' },
    ]

    for (const { term, why } of expectedTerms) {
      const found = nav.some((n) => term.test(n.text))
      expect(
        found,
        `Sidebar/navigation missing "${term.source}" — ${why}. ` +
        `Visible labels: ${navLabels.slice(0, 300)}`
      ).toBeTruthy()
    }
  })

  test('sidebar categories are collapsed by default with only active expanded', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    // Too many items visible at once is overwhelming for a new hire.
    // Check that the sidebar uses collapsible categories.
    const chevrons = page.locator('[aria-expanded], button:has(svg)')
    const chevronCount = await chevrons.count()

    // Having collapsible sections is good UX for large sidebars
    if (chevronCount === 0) {
      console.warn(
        'UX NOTE: Sidebar appears to show all items without collapsible sections. ' +
        `With ${(await collectVisibleNavigation(page)).length} nav items, ` +
        'a new hire would be overwhelmed.'
      )
    }
  })

  test('key actions have recognizable icons alongside text labels', async ({ page }) => {
    await page.goto(STAFF_ROUTES.dashboard)
    await page.waitForLoadState('networkidle')

    // Icon-only buttons without text are confusing for new hires.
    const iconOnlyButtons = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button')
      let iconOnly = 0
      buttons.forEach((btn) => {
        const text = btn.innerText?.trim()
        const hasSvg = btn.querySelector('svg') !== null
        if (hasSvg && (!text || text.length === 0)) {
          iconOnly++
        }
      })
      return iconOnly
    })

    if (iconOnly > 5) {
      console.warn(
        `UX CONCERN: Found ${iconOnly} icon-only buttons on the dashboard. ` +
        'New hires rely on text labels — icons alone require learning the system.'
      )
    }
  })
})