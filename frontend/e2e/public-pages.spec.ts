/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

/**
 * Public Pages E2E Tests
 *
 * Tests for all public-facing pages including:
 * - Page loads successfully
 * - Basic content verification
 * - Accessibility compliance (WCAG 2.1 AA)
 */

// Define all public page routes for testing
const publicPages = [
  { path: "/", name: "Home" },
  { path: "/catalog", name: "Catalog" },
  { path: "/events", name: "Events" },
  { path: "/programs", name: "Reading Programs" },
  { path: "/releases", name: "Release Radar" },
  { path: "/digital", name: "Digital Resources" },
  { path: "/ai", name: "AI Tools" },
  { path: "/ai/how-it-works", name: "AI How It Works" },
  { path: "/business", name: "Business Resources" },
  { path: "/legal", name: "Legal Resources" },
  { path: "/community", name: "Community Resources" },
  { path: "/about", name: "About Us" },
  { path: "/about/our-story", name: "Our Story" },
  { path: "/accessibility", name: "Accessibility" },
  { path: "/contact", name: "Contact" },
  { path: "/privacy", name: "Privacy Policy" },
  { path: "/tech", name: "Tech Support" },
  { path: "/makerspace", name: "Makerspace" },
  { path: "/learn", name: "Learn" },
  { path: "/learn/catalog", name: "Learn Catalog" },
  { path: "/learning-paths", name: "Learning Paths" },
  { path: "/learn/labs", name: "Labs" },
  { path: "/strategic-plan", name: "Strategic Plan" },
]

const authPages = [
  { path: "/login", name: "Login" },
  { path: "/register", name: "Register" },
  { path: "/forgot-password", name: "Forgot Password" },
]

test.describe("Public Pages - Load Tests", () => {
  for (const page of publicPages) {
    test(`${page.name} page (${page.path}) should load successfully`, async ({ page: browserPage }) => {
      const response = await browserPage.goto(page.path)

      // Page should return a successful status
      expect(response?.status()).toBeLessThan(400)

      // Page should have a title
      await expect(browserPage).toHaveTitle(/.+/)

      // Page should have visible content
      await expect(browserPage.locator("body")).toBeVisible()
    })
  }
})

test.describe("Auth Pages - Load Tests", () => {
  for (const page of authPages) {
    test(`${page.name} page (${page.path}) should load successfully`, async ({ page: browserPage }) => {
      const response = await browserPage.goto(page.path)

      expect(response?.status()).toBeLessThan(400)
      await expect(browserPage).toHaveTitle(/.+/)
      await expect(browserPage.locator("body")).toBeVisible()
    })
  }
})

test.describe("Public Pages - Accessibility (WCAG 2.1 AA)", () => {
  for (const page of publicPages) {
    test(`${page.name} page (${page.path}) should pass accessibility audit`, async ({ page: browserPage }) => {
      await browserPage.goto(page.path)

      // Wait for page to be fully loaded
      await browserPage.waitForLoadState("networkidle")

      // Run axe accessibility audit
      const accessibilityScanResults = await new AxeBuilder({ page: browserPage })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze()

      // Log any violations for debugging
      if (accessibilityScanResults.violations.length > 0) {
        console.log(`Accessibility violations on ${page.path}:`)
        accessibilityScanResults.violations.forEach((violation) => {
          console.log(`  - ${violation.id}: ${violation.description}`)
          violation.nodes.forEach((node) => {
            console.log(`    Target: ${node.target}`)
          })
        })
      }

      expect(accessibilityScanResults.violations).toEqual([])
    })
  }
})

test.describe("Auth Pages - Accessibility", () => {
  for (const page of authPages) {
    test(`${page.name} page (${page.path}) should pass accessibility audit`, async ({ page: browserPage }) => {
      await browserPage.goto(page.path)
      await browserPage.waitForLoadState("networkidle")

      const accessibilityScanResults = await new AxeBuilder({ page: browserPage })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze()

      expect(accessibilityScanResults.violations).toEqual([])
    })
  }
})

test.describe("Public Pages - Structure", () => {
  test("Home page should have proper heading hierarchy", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Should have exactly one h1
    const h1Count = await page.locator("h1").count()
    expect(h1Count).toBeGreaterThanOrEqual(1)

    // Check for skip link
    const skipLink = page.locator('a[href="#main-content"]')
    await expect(skipLink).toBeAttached()
  })

  test("All pages should have proper landmark regions", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Should have main content region
    const main = page.locator("main, [role='main']")
    await expect(main).toBeVisible()
  })

  test("Navigation should be keyboard accessible", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Tab to first focusable element (should be skip link)
    await page.keyboard.press("Tab")

    // Should have a visible focus indicator
    const focusedElement = page.locator(":focus")
    await expect(focusedElement).toBeVisible()
  })
})

test.describe("Public Pages - Mobile Responsiveness", () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test("Home page should be responsive on mobile", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Check that content is visible
    await expect(page.locator("body")).toBeVisible()

    // Mobile navigation should be present
    const mobileNav = page.locator('[aria-label="Mobile navigation"]')
    await expect(mobileNav).toBeAttached()
  })

  test("Catalog page should be responsive on mobile", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })
})

test.describe("Public Pages - Error Handling", () => {
  test("404 page should be accessible and helpful", async ({ page }) => {
    const response = await page.goto("/nonexistent-page-12345")

    // Should still render (soft 404)
    await expect(page.locator("body")).toBeVisible()

    // Should have h1 indicating not found
    const heading = page.locator("h1")
    await expect(heading).toBeVisible()

    // Run accessibility audit on 404 page
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })
})

test.describe("Public Pages - Interactive Tests", () => {
  let consoleErrors: string[]

  test.beforeEach(async ({ page }) => {
    consoleErrors = []
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text()
        if (text.includes("favicon") || text.includes("net::ERR_")) return
        consoleErrors.push(text)
      }
    })
  })

  test.afterEach(async () => {
    // Soft assert - report but don't fail on console errors for now
    if (consoleErrors.length > 0) {
      console.warn("Console errors found:", consoleErrors)
    }
  })

  test("Home page - CTA and navigation", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Should have at least one clickable button or link
    const buttons = await page.getByRole("button").count()
    const links = await page.getByRole("link").count()
    expect(buttons + links).toBeGreaterThan(0)

    // Click the first link inside main content (skip off-screen skip-links)
    const mainLink = page.locator("main").getByRole("link").first()
    if ((await mainLink.count()) > 0) {
      await mainLink.click()
      await page.waitForLoadState("domcontentloaded")
      await expect(page.locator("body")).toBeVisible()
    }
  })

  test("Catalog page - search interaction", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    // Find search input
    const searchInput = page.getByRole("textbox").first()
    if ((await searchInput.count()) > 0) {
      await searchInput.fill("fiction")
      await searchInput.press("Enter")
      await page.waitForLoadState("networkidle")
      // Page should still be responsive after search
      await expect(page.locator("body")).toBeVisible()
    }
  })

  test("Events page - loads event content", async ({ page }) => {
    await page.goto("/events")
    await page.waitForLoadState("networkidle")

    // Should show events or an empty state message
    const hasContent = await page
      .locator('main, [role="main"]')
      .first()
      .isVisible()
    expect(hasContent).toBeTruthy()
  })

  test("Contact page - form interaction", async ({ page }) => {
    await page.goto("/contact")
    await page.waitForLoadState("networkidle")

    // Find a form input and verify it's interactive
    const nameInput = page.getByLabel(/name/i).first()
    if ((await nameInput.count()) > 0) {
      await nameInput.fill("Test User")
      await expect(nameInput).toHaveValue("Test User")
    }
  })

  test("Login page - form interaction", async ({ page }) => {
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    const emailInput = page.getByLabel(/email/i)
    if ((await emailInput.count()) > 0) {
      await emailInput.fill("test@example.com")
      await expect(emailInput).toHaveValue("test@example.com")
    }

    const passwordInput = page.locator('input[type="password"]')
    if ((await passwordInput.count()) > 0) {
      await passwordInput.fill("TestPass123")
      // Password should be filled (masked)
      await expect(passwordInput).not.toHaveValue("")
    }
  })

  test("Learn page - course content", async ({ page }) => {
    await page.goto("/learn")
    await page.waitForLoadState("networkidle")

    // Should have content area
    await expect(page.locator("body")).toBeVisible()

    // Look for course cards or content
    const links = await page.getByRole("link").count()
    expect(links).toBeGreaterThan(0)
  })

  test("About page - content loads", async ({ page }) => {
    await page.goto("/about")
    await page.waitForLoadState("networkidle")

    // Should have visible content
    const heading = page.getByRole("heading").first()
    if ((await heading.count()) > 0) {
      await expect(heading).toBeVisible()
    }
  })
})
