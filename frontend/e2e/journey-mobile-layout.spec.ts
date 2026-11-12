/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect, type Page } from '@playwright/test'

/**
 * Mobile Layout Integrity Regression
 *
 * Guards the class of mobile-responsive fixes made in the
 * `claude/mobile-responsive-pages-V477L` branch. Instead of pixel-perfect
 * screenshot diffs (high maintenance, brittle), it asserts a small set of
 * layout invariants at each mobile viewport for each main patron page:
 *
 *  1. No horizontal page scroll -- `documentElement.scrollWidth` must fit
 *     within the viewport (plus a 1px tolerance for sub-pixel rounding).
 *  2. No element sticks out beyond the right edge of the viewport (skipping
 *     off-screen drawers, tooltips, modals, and sr-only helpers).
 *  3. The primary h1 is visible and doesn't exceed the viewport width.
 *
 * If any of these fail, someone reintroduced a fixed-width container, a
 * non-responsive `text-5xl`+ headline, a table without an overflow wrapper,
 * or a grid that skipped the mobile breakpoint.
 */

const MAIN_PAGES = [
  { path: '/', label: 'HomePage' },
  { path: '/discover', label: 'DiscoverPage' },
  { path: '/catalog', label: 'CatalogPage' },
  { path: '/catalog/series', label: 'BrowseSeriesPage' },
  { path: '/events', label: 'EventsPage' },
  { path: '/blog', label: 'BlogListPage' },
  { path: '/about', label: 'AboutPage' },
  { path: '/branches', label: 'BranchesPage' },
  { path: '/contact', label: 'ContactPage' },
  { path: '/login', label: 'LoginPage' },
] as const

const MOBILE_VIEWPORTS = [
  { name: '320px', width: 320, height: 720 },  // small phone / accessibility zoom
  { name: '375px', width: 375, height: 812 },  // iPhone SE / mini
  { name: '390px', width: 390, height: 844 },  // iPhone 13/14
  { name: '768px', width: 768, height: 1024 }, // iPad portrait
] as const

async function assertNoHorizontalOverflow(page: Page, viewportWidth: number): Promise<void> {
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
  // 1px tolerance for sub-pixel rounding in the browser.
  expect(
    scrollWidth,
    `Page scrolls horizontally: scrollWidth ${scrollWidth}px > viewport ${viewportWidth}px`,
  ).toBeLessThanOrEqual(viewportWidth + 1)
}

async function assertNoElementOverflowsRightEdge(page: Page, viewportWidth: number): Promise<void> {
  // Any element whose right edge exceeds the viewport is a mobile bug --
  // except for genuinely off-screen affordances (mobile drawer, tooltip,
  // toast, sr-only text). Skip those explicitly so this stays a signal
  // and not a nuisance.
  const overflowing = await page.evaluate((width: number) => {
    const results: { tag: string; selector: string; right: number; classes: string }[] = []
    const nodes = Array.from(document.body.querySelectorAll<HTMLElement>('*'))
    for (const el of nodes) {
      // Skip explicitly hidden, off-canvas, or utility elements.
      const style = window.getComputedStyle(el)
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue
      if (el.getAttribute('aria-hidden') === 'true') continue
      if (el.classList.contains('sr-only')) continue
      // Skip fixed-position overlays (drawers, modals, toasts) -- they can legitimately
      // sit off-screen when closed. Their opened state has its own tests.
      if (style.position === 'fixed' || style.position === 'absolute') continue

      const rect = el.getBoundingClientRect()
      if (rect.width === 0 || rect.height === 0) continue
      if (rect.right > width + 1) {
        results.push({
          tag: el.tagName.toLowerCase(),
          selector: el.id ? `#${el.id}` : el.className.toString().slice(0, 60),
          right: Math.round(rect.right),
          classes: el.className.toString().slice(0, 80),
        })
      }
    }
    // De-dup by (tag, selector) so nested descendants collapse into one report.
    const seen = new Set<string>()
    return results.filter((r) => {
      const key = `${r.tag}|${r.selector}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }).slice(0, 5)
  }, viewportWidth)

  expect(
    overflowing,
    `Elements exceed viewport width ${viewportWidth}px: ${JSON.stringify(overflowing, null, 2)}`,
  ).toEqual([])
}

async function assertHeadingFitsViewport(page: Page, viewportWidth: number): Promise<void> {
  const h1 = page.locator('h1').first()
  if ((await h1.count()) === 0) return
  // sr-only h1s (e.g. CatalogPage's screen-reader-only title) don't render visibly.
  const isSrOnly = await h1.evaluate((el) => el.classList.contains('sr-only'))
  if (isSrOnly) return
  const box = await h1.boundingBox()
  if (!box) return
  expect(
    box.width,
    `<h1> width ${Math.round(box.width)}px exceeds viewport ${viewportWidth}px`,
  ).toBeLessThanOrEqual(viewportWidth + 1)
}

test.describe('Mobile layout integrity', () => {
  for (const viewport of MOBILE_VIEWPORTS) {
    test.describe(`@ ${viewport.name}`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height })
      })

      for (const { path, label } of MAIN_PAGES) {
        test(`${label} fits ${viewport.name} without horizontal overflow`, async ({ page }) => {
          const response = await page.goto(path, { waitUntil: 'domcontentloaded' })
          // A page that redirects or 4xxs still runs the assertions on the
          // landing page, which is what we want -- broken redirects are their
          // own test, not this one.
          if (response && response.status() >= 500) {
            test.skip(true, `Skipping ${path} — server returned ${response.status()}`)
          }
          // Let async data-fetching finish rendering (blog cards, catalog items,
          // etc.) so overflow checks measure the real DOM, not a skeleton.
          await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {
            // networkidle can hang on pages with long-polling queries; a short
            // timeout + best-effort continue is fine for layout checks.
          })

          await assertNoHorizontalOverflow(page, viewport.width)
          await assertHeadingFitsViewport(page, viewport.width)
          await assertNoElementOverflowsRightEdge(page, viewport.width)
        })
      }
    })
  }
})
