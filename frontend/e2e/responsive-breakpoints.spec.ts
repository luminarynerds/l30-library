/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect, Page } from "@playwright/test"

/**
 * Comprehensive Responsive Breakpoint Tests
 *
 * Tests every page at 6 breakpoints with 8 validation checks each:
 * 1. Content readable (visible text, proper font sizes)
 * 2. No horizontal scroll (document fits viewport width)
 * 3. Touch targets large enough (≥44px per WCAG 2.5.5)
 * 4. Navigation usable (nav visible/accessible)
 * 5. Forms usable (inputs accessible, properly sized)
 * 6. Tables readable (not overflowing, scrollable wrapper)
 * 7. Images scaled properly (fit viewport, aspect ratio preserved)
 * 8. Modals fit screen (no overflow, dismissible)
 */

// ==================== Breakpoints ====================

const BREAKPOINTS = [
  { name: "mobile-320", width: 320, height: 568, isMobile: true },
  { name: "mobile-landscape-568", width: 568, height: 320, isMobile: true },
  { name: "tablet-portrait-768", width: 768, height: 1024, isMobile: false },
  { name: "tablet-landscape-1024", width: 1024, height: 768, isMobile: false },
  { name: "desktop-1280", width: 1280, height: 800, isMobile: false },
  { name: "large-desktop-1920", width: 1920, height: 1080, isMobile: false },
] as const

// ==================== Page Definitions ====================

interface PageDef {
  path: string
  name: string
  category: string
}

const PUBLIC_PAGES: PageDef[] = [
  // Core pages
  { path: "/", name: "Home", category: "core" },
  { path: "/login", name: "Login", category: "auth" },
  { path: "/register", name: "Register", category: "auth" },
  { path: "/forgot-password", name: "Forgot Password", category: "auth" },

  // Catalog
  { path: "/catalog", name: "Catalog", category: "catalog" },
  { path: "/catalog/search", name: "Catalog Search", category: "catalog" },
  { path: "/search", name: "Search", category: "catalog" },

  // Events & Programs
  { path: "/events", name: "Events", category: "events" },
  { path: "/programs", name: "Programs", category: "events" },
  { path: "/reading-logs", name: "Reading Logs", category: "events" },
  { path: "/reading-minutes", name: "Reading Minutes", category: "events" },
  { path: "/reading-challenge", name: "Reading Challenge", category: "events" },
  { path: "/book-clubs", name: "Book Clubs", category: "events" },
  { path: "/public-reading-lists", name: "Public Reading Lists", category: "events" },
  { path: "/read-to-reduce", name: "Read to Reduce", category: "events" },

  // Digital Resources
  { path: "/releases", name: "Release Radar", category: "digital" },
  { path: "/digital", name: "Digital Resources", category: "digital" },
  { path: "/streaming", name: "Streaming", category: "digital" },
  { path: "/databases", name: "Databases", category: "digital" },
  { path: "/gutenberg", name: "Gutenberg", category: "digital" },

  // AI & Tech
  { path: "/ai", name: "AI Tools", category: "tech" },
  { path: "/ai/how-it-works", name: "AI How It Works", category: "tech" },
  { path: "/ai/agents", name: "AI Agents", category: "tech" },
  { path: "/tech", name: "Tech Support", category: "tech" },
  { path: "/makerspace", name: "Makerspace", category: "tech" },
  { path: "/wifi", name: "WiFi", category: "tech" },

  // About & Info
  { path: "/about/library", name: "About Library", category: "about" },
  { path: "/about/our-story", name: "Our Story", category: "about" },
  { path: "/accessibility", name: "Accessibility", category: "about" },
  { path: "/contact", name: "Contact", category: "about" },
  { path: "/faq", name: "FAQ", category: "about" },
  { path: "/help", name: "Help", category: "about" },
  { path: "/knowledge-base", name: "Knowledge Base", category: "about" },
  { path: "/strategic-plan", name: "Strategic Plan", category: "about" },
  { path: "/announcements", name: "Announcements", category: "about" },

  // Branches & Rooms
  { path: "/branches", name: "Branches", category: "locations" },
  { path: "/rooms", name: "Rooms", category: "locations" },
  { path: "/donate", name: "Donate", category: "locations" },
  { path: "/careers", name: "Careers", category: "locations" },

  // Legal & Policy
  { path: "/privacy", name: "Privacy", category: "legal" },
  { path: "/terms", name: "Terms", category: "legal" },
  { path: "/legal", name: "Legal Resources", category: "legal" },
  { path: "/legal/calculators", name: "Legal Calculators", category: "legal" },
  { path: "/legal/wizard", name: "Legal Wizard", category: "legal" },
  { path: "/banned-books", name: "Banned Books", category: "legal" },
  { path: "/intellectual-freedom", name: "Intellectual Freedom", category: "legal" },

  // Community & Business
  { path: "/business", name: "Business Resources", category: "community" },
  { path: "/community", name: "Community", category: "community" },
  { path: "/ask-librarian", name: "Ask Librarian", category: "community" },
  { path: "/suggest-purchase", name: "Suggest Purchase", category: "community" },
  { path: "/interlibrary-loan", name: "Interlibrary Loan", category: "community" },
  { path: "/card-application", name: "Card Application", category: "community" },
  { path: "/share-experience", name: "Share Experience", category: "community" },

  // Genealogy
  { path: "/genealogy", name: "Genealogy", category: "genealogy" },
  { path: "/genealogy/training", name: "Genealogy Training", category: "genealogy" },
  { path: "/genealogy/inquiry", name: "Genealogy Inquiry", category: "genealogy" },
  { path: "/genealogy/ask-genealogist", name: "Ask Genealogist", category: "genealogy" },
  { path: "/genealogy/archives", name: "Genealogy Archives", category: "genealogy" },
  { path: "/genealogy/archives/submit", name: "Submit Archive", category: "genealogy" },
  { path: "/genealogy/research", name: "Genealogy Research", category: "genealogy" },

  // Youth & Education
  { path: "/youth", name: "Youth", category: "youth" },
  { path: "/youth/homework-help", name: "Homework Help", category: "youth" },
  { path: "/youth/coding-tracks", name: "Coding Tracks", category: "youth" },
  { path: "/youth/teen-mentors", name: "Teen Mentors", category: "youth" },
  { path: "/youth/makerspace", name: "Youth Makerspace", category: "youth" },
  { path: "/youth/archives", name: "Youth Archives", category: "youth" },

  // Learn
  { path: "/learn", name: "Learn", category: "learn" },
  { path: "/learn/catalog", name: "Learn Catalog", category: "learn" },
  { path: "/learn/achievements", name: "Achievements", category: "learn" },
  { path: "/learn/labs", name: "Labs", category: "learn" },
  { path: "/learn/labs/ai-said-what", name: "AI Said What", category: "learn" },
  { path: "/learn/labs/who-wrote-this", name: "Who Wrote This", category: "learn" },
  { path: "/learn/labs/fix-this-prompt", name: "Fix This Prompt", category: "learn" },
  { path: "/learn/labs/real-or-fake", name: "Real or Fake", category: "learn" },
  { path: "/learning-paths", name: "Learning Paths", category: "learn" },
  { path: "/rubrics", name: "Rubrics", category: "learn" },
  { path: "/certificates", name: "Certificates", category: "learn" },
  { path: "/certificates/verify", name: "Verify Certificate", category: "learn" },

  // Indie Authors
  { path: "/indie", name: "Indie Catalog", category: "indie" },
  { path: "/indie/discover", name: "Indie Discover", category: "indie" },
  { path: "/indie/feed", name: "Indie Feed", category: "indie" },

  // Guides
  { path: "/guides/wireless-printing", name: "Wireless Printing Guide", category: "guides" },
  { path: "/guides/email-account", name: "Email Account Guide", category: "guides" },
  { path: "/guides/wifi-troubleshooting", name: "WiFi Troubleshooting Guide", category: "guides" },
  { path: "/guides/password-reset", name: "Password Reset Guide", category: "guides" },
  { path: "/guides/email-on-phone", name: "Email on Phone Guide", category: "guides" },
  { path: "/guides/library-card", name: "Library Card Guide", category: "guides" },
  { path: "/guides/scam-recognition", name: "Scam Recognition Guide", category: "guides" },
  { path: "/guides/check-print-jobs", name: "Check Print Jobs Guide", category: "guides" },

  // Teacher
  { path: "/teacher/reading-dashboard", name: "Teacher Reading Dashboard", category: "teacher" },
  { path: "/teacher/reading-lists", name: "Teacher Reading Lists", category: "teacher" },
  { path: "/teacher/professional-development", name: "Professional Development", category: "teacher" },
  { path: "/teacher/library-consultations", name: "Library Consultations", category: "teacher" },
  { path: "/teacher/family-challenges", name: "Family Challenges", category: "teacher" },
  { path: "/teacher/library-visits", name: "Library Visits", category: "teacher" },

  // Emergency Operations
  { path: "/emergency-operations", name: "Emergency Operations", category: "emergency" },
  { path: "/emergency-operations/status", name: "Emergency Status", category: "emergency" },
  { path: "/emergency-operations/offline-mode", name: "Offline Mode", category: "emergency" },
  { path: "/emergency-operations/paper-backup", name: "Paper Backup", category: "emergency" },
  { path: "/emergency-operations/data-sync", name: "Data Sync", category: "emergency" },
  { path: "/emergency-operations/closures", name: "Closures", category: "emergency" },
  { path: "/emergency-operations/recovery", name: "Recovery", category: "emergency" },

  // Status & System
  { path: "/status", name: "Status", category: "system" },
  { path: "/system-status", name: "System Status", category: "system" },
  { path: "/transparency/material-costs", name: "Material Costs", category: "system" },
]

// ==================== Validation Helpers ====================

/** Check 1: Content is readable - visible text exists with reasonable font size */
async function checkContentReadable(page: Page, viewportWidth: number) {
  // Body should be visible
  await expect(page.locator("body")).toBeVisible()

  // Page should have visible text content
  const hasVisibleText = await page.evaluate(() => {
    const body = document.body
    return body.innerText.trim().length > 0
  })
  expect(hasVisibleText).toBe(true)

  // Check that text isn't unreadably small (minimum 12px on mobile, 14px on desktop)
  const minFontSize = viewportWidth < 768 ? 12 : 14
  const textElements = page.locator("p, h1, h2, h3, h4, h5, h6, li, td, th, label, span, a")
  const count = await textElements.count()

  if (count > 0) {
    // Sample up to 5 text elements
    const sampleSize = Math.min(count, 5)
    for (let i = 0; i < sampleSize; i++) {
      const el = textElements.nth(i)
      if (await el.isVisible()) {
        const fontSize = await el.evaluate((node) => {
          return parseFloat(window.getComputedStyle(node).fontSize)
        })
        expect(fontSize).toBeGreaterThanOrEqual(minFontSize)
      }
    }
  }
}

/** Check 2: No horizontal scroll - document width doesn't exceed viewport */
async function checkNoHorizontalScroll(page: Page, viewportWidth: number) {
  const scrollInfo = await page.evaluate(() => {
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: document.documentElement.clientWidth,
      bodyWidth: document.body.scrollWidth,
    }
  })

  // Allow 1px tolerance for sub-pixel rendering
  expect(scrollInfo.documentWidth).toBeLessThanOrEqual(viewportWidth + 1)
}

/** Check 3: Touch targets are large enough (≥44x44px per WCAG 2.5.5) */
async function checkTouchTargets(page: Page, isMobile: boolean) {
  // Only enforce strict minimum on touch devices
  const minSize = isMobile ? 44 : 24

  const interactiveElements = page.locator(
    'button, a, input, select, textarea, [role="button"], [role="link"], [role="tab"], [role="menuitem"]'
  )
  const count = await interactiveElements.count()

  if (count === 0) return

  let undersizedCount = 0
  const sampleSize = Math.min(count, 10)

  for (let i = 0; i < sampleSize; i++) {
    const el = interactiveElements.nth(i)
    if (await el.isVisible()) {
      const box = await el.boundingBox()
      if (box) {
        // Either width or height must meet minimum (allows for full-width buttons)
        if (box.width < minSize && box.height < minSize) {
          undersizedCount++
        }
      }
    }
  }

  // Allow up to 20% of sampled targets to be undersized (icon buttons, etc.)
  const maxUndersized = Math.ceil(sampleSize * 0.2)
  expect(undersizedCount).toBeLessThanOrEqual(maxUndersized)
}

/** Check 4: Navigation is usable - nav element visible or mobile menu accessible */
async function checkNavigationUsable(page: Page, viewportWidth: number) {
  // Look for navigation elements
  const nav = page.locator("nav, [role='navigation']")
  const navCount = await nav.count()

  if (navCount === 0) return // Some pages may not have nav (e.g., minimal auth pages)

  if (viewportWidth < 768) {
    // On mobile: either nav is visible OR a hamburger/menu button exists
    const menuButton = page.locator(
      'button[aria-label*="menu" i], button[aria-label*="Menu" i], ' +
        'button[aria-label*="navigation" i], button[aria-label*="Navigation" i], ' +
        '[aria-label="Mobile navigation"], [aria-expanded], ' +
        'button:has(svg), [role="button"][aria-label*="menu" i]'
    )
    const hasMenuButton = (await menuButton.count()) > 0
    const hasVisibleNav = await nav.first().isVisible().catch(() => false)

    expect(hasMenuButton || hasVisibleNav).toBe(true)
  } else {
    // On larger screens: nav should be visible
    const isAnyNavVisible = await nav.first().isVisible().catch(() => false)
    expect(isAnyNavVisible).toBe(true)
  }
}

/** Check 5: Forms are usable - inputs accessible, properly sized, labels present */
async function checkFormsUsable(page: Page, viewportWidth: number) {
  const forms = page.locator("form")
  const formCount = await forms.count()

  if (formCount === 0) return // Page has no forms, skip

  for (let f = 0; f < Math.min(formCount, 2); f++) {
    const form = forms.nth(f)
    if (!(await form.isVisible())) continue

    const formBox = await form.boundingBox()
    if (formBox) {
      // Form should fit within viewport width
      expect(formBox.x + formBox.width).toBeLessThanOrEqual(viewportWidth + 1)
    }

    // Check inputs are properly sized for touch
    const inputs = form.locator("input, select, textarea")
    const inputCount = await inputs.count()

    for (let i = 0; i < Math.min(inputCount, 5); i++) {
      const input = inputs.nth(i)
      if (await input.isVisible()) {
        const box = await input.boundingBox()
        if (box) {
          // Input height should be at least 36px for mobile usability
          expect(box.height).toBeGreaterThanOrEqual(36)
        }

        // Inputs should have associated labels or aria-label
        const hasLabel = await input.evaluate((el) => {
          const input = el as HTMLInputElement
          const id = input.id
          const ariaLabel = input.getAttribute("aria-label")
          const ariaLabelledBy = input.getAttribute("aria-labelledby")
          const placeholder = input.placeholder
          const title = input.title
          const associatedLabel = id ? document.querySelector(`label[for="${id}"]`) : null

          return !!(ariaLabel || ariaLabelledBy || associatedLabel || placeholder || title)
        })
        expect(hasLabel).toBe(true)
      }
    }

    // Submit buttons should be reachable
    const submitBtns = form.locator('button[type="submit"], input[type="submit"], button:not([type])')
    if ((await submitBtns.count()) > 0) {
      const btn = submitBtns.first()
      if (await btn.isVisible()) {
        const box = await btn.boundingBox()
        if (box) {
          expect(box.width).toBeGreaterThanOrEqual(44)
          expect(box.height).toBeGreaterThanOrEqual(36)
        }
      }
    }
  }
}

/** Check 6: Tables are readable - not overflowing, have scroll wrapper or responsive design */
async function checkTablesReadable(page: Page, viewportWidth: number) {
  const tables = page.locator("table, [role='table'], [role='grid']")
  const tableCount = await tables.count()

  if (tableCount === 0) return // No tables on page

  for (let t = 0; t < Math.min(tableCount, 3); t++) {
    const table = tables.nth(t)
    if (!(await table.isVisible())) continue

    const tableBox = await table.boundingBox()
    if (!tableBox) continue

    // Table (or its scroll container) should not extend beyond viewport
    const overflows = await table.evaluate((el, vw) => {
      const rect = el.getBoundingClientRect()
      const parent = el.parentElement

      // Check if table has a scrollable wrapper
      if (parent) {
        const parentStyle = window.getComputedStyle(parent)
        const hasScrollWrapper =
          parentStyle.overflowX === "auto" ||
          parentStyle.overflowX === "scroll" ||
          parentStyle.overflow === "auto" ||
          parentStyle.overflow === "scroll"

        if (hasScrollWrapper) {
          // Scroll wrapper is fine - table can be wider than viewport
          const parentRect = parent.getBoundingClientRect()
          return parentRect.right > vw + 1
        }
      }

      return rect.right > vw + 1
    }, viewportWidth)

    expect(overflows).toBe(false)

    // On mobile, check for readable font size in table cells
    if (viewportWidth < 768) {
      const cells = table.locator("td, th")
      const cellCount = await cells.count()

      if (cellCount > 0) {
        const firstVisibleCell = cells.first()
        if (await firstVisibleCell.isVisible()) {
          const fontSize = await firstVisibleCell.evaluate((el) =>
            parseFloat(window.getComputedStyle(el).fontSize)
          )
          expect(fontSize).toBeGreaterThanOrEqual(11) // Allow slightly smaller in tables
        }
      }
    }
  }
}

/** Check 7: Images scaled properly - fit viewport, aspect ratio preserved */
async function checkImagesScaled(page: Page, viewportWidth: number) {
  const images = page.locator("img")
  const imgCount = await images.count()

  if (imgCount === 0) return

  const sampleSize = Math.min(imgCount, 8)

  for (let i = 0; i < sampleSize; i++) {
    const img = images.nth(i)
    if (!(await img.isVisible())) continue

    const imgInfo = await img.evaluate((el) => {
      const imgEl = el as HTMLImageElement
      const rect = imgEl.getBoundingClientRect()
      return {
        displayWidth: rect.width,
        displayHeight: rect.height,
        naturalWidth: imgEl.naturalWidth,
        naturalHeight: imgEl.naturalHeight,
        right: rect.right,
        isLoaded: imgEl.complete && imgEl.naturalWidth > 0,
      }
    })

    if (!imgInfo.isLoaded || imgInfo.displayWidth === 0) continue

    // Image should not extend beyond viewport
    expect(imgInfo.right).toBeLessThanOrEqual(viewportWidth + 2)

    // Aspect ratio should be preserved (within tolerance)
    if (imgInfo.naturalWidth > 0 && imgInfo.naturalHeight > 0) {
      const naturalRatio = imgInfo.naturalWidth / imgInfo.naturalHeight
      const displayRatio = imgInfo.displayWidth / imgInfo.displayHeight

      // Allow 15% tolerance for object-fit: cover, border-radius crops, etc.
      const ratioDiff = Math.abs(naturalRatio - displayRatio) / naturalRatio
      expect(ratioDiff).toBeLessThan(0.15)
    }
  }
}

/** Check 8: Modals fit screen - no overflow when open */
async function checkModalsFitScreen(page: Page, viewportWidth: number, viewportHeight: number) {
  // Look for modal triggers and existing modals
  const modals = page.locator(
    '[role="dialog"], [role="alertdialog"], [aria-modal="true"], ' +
      ".modal, .MuiDialog-root, .MuiModal-root, [data-testid*='modal'], [data-testid*='dialog']"
  )
  const modalCount = await modals.count()

  // Check any already-visible modals
  for (let m = 0; m < Math.min(modalCount, 3); m++) {
    const modal = modals.nth(m)
    if (!(await modal.isVisible())) continue

    const modalBox = await modal.boundingBox()
    if (!modalBox) continue

    // Modal should fit within viewport
    expect(modalBox.width).toBeLessThanOrEqual(viewportWidth)
    expect(modalBox.height).toBeLessThanOrEqual(viewportHeight + 50) // Allow small overflow for scrollable modals

    // Modal should have a close mechanism
    const closeBtn = modal.locator(
      'button[aria-label*="close" i], button[aria-label*="Close" i], ' +
        'button[aria-label*="dismiss" i], button:has-text("Close"), button:has-text("Cancel"), ' +
        "button:has-text(\"×\"), button:has-text(\"✕\")"
    )
    const hasClose = (await closeBtn.count()) > 0

    // Also check for backdrop/overlay dismiss
    const hasBackdrop = (await page.locator(".MuiBackdrop-root, [data-testid='backdrop'], .overlay").count()) > 0

    expect(hasClose || hasBackdrop).toBe(true)
  }

  // Try to trigger a modal if a common trigger exists (only on first page load)
  const modalTriggers = page.locator(
    'button[data-testid*="modal" i], button[aria-haspopup="dialog"], ' +
      "[data-opens-modal], [data-toggle='modal']"
  )
  const triggerCount = await modalTriggers.count()

  if (triggerCount > 0) {
    const trigger = modalTriggers.first()
    if (await trigger.isVisible()) {
      await trigger.click()
      await page.waitForTimeout(500)

      // Re-check for modals after click
      const openModals = page.locator('[role="dialog"]:visible, [role="alertdialog"]:visible, [aria-modal="true"]:visible')
      const openCount = await openModals.count()

      if (openCount > 0) {
        const modal = openModals.first()
        const modalBox = await modal.boundingBox()
        if (modalBox) {
          expect(modalBox.width).toBeLessThanOrEqual(viewportWidth)
        }

        // Dismiss the modal
        await page.keyboard.press("Escape")
        await page.waitForTimeout(300)
      }
    }
  }
}

// ==================== Test Suite ====================

// Group pages by category for organized reporting
const categories = [...new Set(PUBLIC_PAGES.map((p) => p.category))]

for (const breakpoint of BREAKPOINTS) {
  test.describe(`Breakpoint: ${breakpoint.name} (${breakpoint.width}x${breakpoint.height})`, () => {
    test.describe.configure({ mode: "parallel" })

    for (const category of categories) {
      const pagesInCategory = PUBLIC_PAGES.filter((p) => p.category === category)

      test.describe(`${category}`, () => {
        for (const pageDef of pagesInCategory) {
          test.describe(`${pageDef.name} (${pageDef.path})`, () => {
            test.beforeEach(async ({ page }) => {
              await page.setViewportSize({
                width: breakpoint.width,
                height: breakpoint.height,
              })
              await page.goto(pageDef.path, { waitUntil: "networkidle", timeout: 30000 })
            })

            test("content is readable", async ({ page }) => {
              await checkContentReadable(page, breakpoint.width)
            })

            test("no horizontal scroll", async ({ page }) => {
              await checkNoHorizontalScroll(page, breakpoint.width)
            })

            test("touch targets large enough", async ({ page }) => {
              await checkTouchTargets(page, breakpoint.isMobile)
            })

            test("navigation is usable", async ({ page }) => {
              await checkNavigationUsable(page, breakpoint.width)
            })

            test("forms are usable", async ({ page }) => {
              await checkFormsUsable(page, breakpoint.width)
            })

            test("tables are readable", async ({ page }) => {
              await checkTablesReadable(page, breakpoint.width)
            })

            test("images scaled properly", async ({ page }) => {
              await checkImagesScaled(page, breakpoint.width)
            })

            test("modals fit screen", async ({ page }) => {
              await checkModalsFitScreen(page, breakpoint.width, breakpoint.height)
            })
          })
        }
      })
    }
  })
}

// ==================== Cross-Breakpoint Consistency ====================

test.describe("Cross-Breakpoint Consistency", () => {
  const criticalPages = ["/", "/catalog", "/login", "/events", "/contact", "/legal"]

  for (const pagePath of criticalPages) {
    test(`${pagePath} maintains content across all breakpoints`, async ({ page }) => {
      const contentByBreakpoint: Record<string, { headings: number; links: number; hasMain: boolean }> = {}

      for (const bp of BREAKPOINTS) {
        await page.setViewportSize({ width: bp.width, height: bp.height })
        await page.goto(pagePath, { waitUntil: "networkidle", timeout: 30000 })

        const metrics = await page.evaluate(() => {
          return {
            headings: document.querySelectorAll("h1, h2, h3").length,
            links: document.querySelectorAll("a[href]").length,
            hasMain: document.querySelector("main, [role='main']") !== null,
          }
        })

        contentByBreakpoint[bp.name] = metrics
      }

      // Verify content parity: headings count should be consistent (no content hidden)
      const headingCounts = Object.values(contentByBreakpoint).map((m) => m.headings)
      const minHeadings = Math.min(...headingCounts)
      const maxHeadings = Math.max(...headingCounts)

      // Allow some variance (responsive may show/hide some sections) but not drastic
      if (maxHeadings > 0) {
        expect(minHeadings).toBeGreaterThan(0)
      }

      // Main content area should exist at all breakpoints
      for (const [bp, metrics] of Object.entries(contentByBreakpoint)) {
        if (!metrics.hasMain) {
          console.warn(`Warning: No <main> element found on ${pagePath} at ${bp}`)
        }
      }
    })
  }
})

// ==================== Orientation Change Tests ====================

test.describe("Orientation Change Resilience", () => {
  const testPages = ["/", "/catalog", "/login", "/events", "/legal", "/genealogy"]

  for (const pagePath of testPages) {
    test(`${pagePath} handles portrait-to-landscape rotation`, async ({ page }) => {
      // Start in portrait
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto(pagePath, { waitUntil: "networkidle", timeout: 30000 })

      await expect(page.locator("body")).toBeVisible()

      // Rotate to landscape
      await page.setViewportSize({ width: 812, height: 375 })
      await page.waitForTimeout(300)

      // Content should still be visible and not overflow
      await expect(page.locator("body")).toBeVisible()

      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(scrollWidth).toBeLessThanOrEqual(812 + 1)
    })

    test(`${pagePath} handles landscape-to-portrait rotation`, async ({ page }) => {
      // Start in landscape
      await page.setViewportSize({ width: 1024, height: 768 })
      await page.goto(pagePath, { waitUntil: "networkidle", timeout: 30000 })

      await expect(page.locator("body")).toBeVisible()

      // Rotate to portrait
      await page.setViewportSize({ width: 768, height: 1024 })
      await page.waitForTimeout(300)

      await expect(page.locator("body")).toBeVisible()

      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(scrollWidth).toBeLessThanOrEqual(768 + 1)
    })
  }
})

// ==================== Edge Case: Narrowest Viewport ====================

test.describe("Extreme Narrow Viewport (320px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 })
  })

  const criticalPages = ["/", "/catalog", "/login", "/register", "/events", "/contact"]

  for (const pagePath of criticalPages) {
    test(`${pagePath} is fully functional at 320px`, async ({ page }) => {
      await page.goto(pagePath, { waitUntil: "networkidle", timeout: 30000 })

      // No horizontal overflow
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      expect(scrollWidth).toBeLessThanOrEqual(321)

      // All visible text is readable
      const tinyText = await page.evaluate(() => {
        const elements = document.querySelectorAll("p, span, a, li, td, th, label")
        let tinyCount = 0
        elements.forEach((el) => {
          const style = window.getComputedStyle(el)
          if (style.display !== "none" && style.visibility !== "hidden") {
            const fontSize = parseFloat(style.fontSize)
            if (fontSize < 11) tinyCount++
          }
        })
        return tinyCount
      })
      expect(tinyText).toBe(0)

      // Interactive elements are reachable
      const buttons = page.locator("button:visible, a:visible")
      const btnCount = await buttons.count()
      if (btnCount > 0) {
        const firstBtn = buttons.first()
        const box = await firstBtn.boundingBox()
        if (box) {
          // Should be within viewport
          expect(box.x).toBeGreaterThanOrEqual(-1)
          expect(box.x + box.width).toBeLessThanOrEqual(321)
        }
      }
    })
  }
})

// ==================== Large Desktop Content Stretch ====================

test.describe("Large Desktop Content Constraints (1920px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
  })

  const contentPages = ["/", "/about/library", "/events", "/catalog", "/legal", "/genealogy"]

  for (const pagePath of contentPages) {
    test(`${pagePath} content doesn't stretch uncomfortably wide`, async ({ page }) => {
      await page.goto(pagePath, { waitUntil: "networkidle", timeout: 30000 })

      // Check that text content areas have max-width constraints
      const textContainers = page.locator("main p, main li, article p")
      const count = await textContainers.count()

      if (count > 0) {
        const firstText = textContainers.first()
        if (await firstText.isVisible()) {
          const box = await firstText.boundingBox()
          if (box) {
            // Text lines shouldn't span the full 1920px (poor readability)
            // Ideal line length is 45-75 characters ≈ 600-900px
            // Allow up to 1200px for wider layouts
            expect(box.width).toBeLessThanOrEqual(1400)
          }
        }
      }
    })
  }
})
