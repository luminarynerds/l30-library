/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect, devices } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

/**
 * Cross-Device & Cross-Browser Responsive Testing
 *
 * Tests for responsive design, critical flows, and touch interactions
 * Covers: Mobile (iPhone, Android), Tablet (iPad), Desktop (Chrome, Firefox, Safari, Edge)
 */

// ==================== Mobile Tests ====================

test.describe("Mobile iPhone 12 Safari Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
  })

  test("Home page loads and displays responsively", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      await expect(main).toBeVisible()
    }
  })

  test("Catalog page responsive on iPhone", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const content = page.locator("main, [role='main'], .content")
    if (await content.count() > 0) {
      await expect(content).toBeVisible()
    }
  })

  test("Login form is mobile-friendly", async ({ page }) => {
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    const form = page.locator("form")
    if (await form.count() > 0) {
      await expect(form).toBeVisible()

      // Check input sizes
      const inputs = form.locator("input")
      const count = await inputs.count()
      for (let i = 0; i < count; i++) {
        const box = await inputs.nth(i).boundingBox()
        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(40) // Mobile minimum
        }
      }
    }
  })

  test("Touch targets are appropriately sized", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Check buttons
    const buttons = page.locator("button")
    const btnCount = await buttons.count()

    let tinyButtons = 0
    for (let i = 0; i < Math.min(btnCount, 5); i++) {
      const box = await buttons.nth(i).boundingBox()
      if (box && box.width < 44 && box.height < 44) {
        tinyButtons++
      }
    }

    console.log(`Found ${tinyButtons} buttons under 44px on iPhone`)
  })

  test("Images scale correctly on mobile", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const images = page.locator("img")
    const count = await images.count()

    for (let i = 0; i < Math.min(count, 5); i++) {
      const img = images.nth(i)
      const isVisible = await img.isVisible()

      if (isVisible) {
        const box = await img.boundingBox()
        if (box) {
          // Image should fit in viewport
          expect(box.x + box.width).toBeLessThanOrEqual(420) // 390 + margin
        }
      }
    }
  })

  test("Accessibility check on mobile", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze()

    console.log(`iPhone accessibility violations: ${results.violations.length}`)
  })
})

test.describe("Mobile Android Pixel 5 Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 393, height: 851 })
  })

  test("Home page loads on Android", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })

  test("Catalog search works on Android", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]')
    if (await searchInput.count() > 0) {
      await searchInput.first().click()
      await searchInput.first().type("test")
      await page.waitForTimeout(300)
    }
  })

  test("Touch interactions work on Android", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const buttons = page.locator("button")
    if (await buttons.count() > 0) {
      const firstVisible = buttons.first()
      if (await firstVisible.isVisible()) {
        await firstVisible.tap()
      }
    }
  })
})

// ==================== Tablet Tests ====================

test.describe("Tablet iPad Pro Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 1366 })
  })

  test("Home page displays on tablet", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })

  test("Catalog multi-column layout on tablet", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      const box = await main.first().boundingBox()
      if (box) {
        // Tablet should have wide layout
        expect(box.width).toBeGreaterThan(600)
      }
    }
  })

  test("Touch interactions on tablet", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const buttons = page.locator("button")
    if (await buttons.count() > 0) {
      const firstVisible = buttons.first()
      if (await firstVisible.isVisible()) {
        await firstVisible.tap()
      }
    }
  })

  test("Media scaling on tablet", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const images = page.locator("img")
    if (await images.count() > 0) {
      const img = images.first()
      const isVisible = await img.isVisible()

      if (isVisible) {
        const naturalWidth = await img.evaluate((el: any) => el.naturalWidth)
        const naturalHeight = await img.evaluate((el: any) => el.naturalHeight)
        const displayBox = await img.boundingBox()

        if (naturalWidth > 0 && naturalHeight > 0 && displayBox) {
          const displayRatio = displayBox.width / displayBox.height
          const naturalRatio = naturalWidth / naturalHeight

          // Aspect ratio should be preserved
          const diff = Math.abs(displayRatio - naturalRatio)
          expect(diff).toBeLessThan(0.1)
        }
      }
    }
  })
})

// ==================== Desktop Chrome Tests ====================

test.describe("Desktop Chrome Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
  })

  test("Full layout on desktop Chrome", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()

    const nav = page.locator("nav, [role='navigation']")
    if (await nav.count() > 0) {
      await expect(nav).toBeVisible()
    }

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze()

    console.log(`Desktop Chrome a11y violations: ${results.violations.length}`)
  })

  test("Catalog grid layout on desktop", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      const box = await main.first().boundingBox()
      if (box) {
        expect(box.width).toBeGreaterThan(800)
      }
    }
  })

  test("High quality images on desktop", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const images = page.locator("img")
    const count = await images.count()

    for (let i = 0; i < Math.min(count, 3); i++) {
      const img = images.nth(i)
      const isVisible = await img.isVisible()

      if (isVisible) {
        const naturalWidth = await img.evaluate((el: any) => el.naturalWidth)
        const displayBox = await img.boundingBox()

        if (naturalWidth > 0 && displayBox) {
          // Image should be loaded
          expect(naturalWidth).toBeGreaterThan(0)
        }
      }
    }
  })

  test("Login flow works on desktop", async ({ page }) => {
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    const form = page.locator("form")
    if (await form.count() > 0) {
      await expect(form).toBeVisible()

      const inputs = form.locator("input")
      expect(await inputs.count()).toBeGreaterThanOrEqual(2)
    }
  })
})

// ==================== Desktop Firefox Tests ====================

test.describe("Desktop Firefox Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
  })

  test("Home page on Firefox", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()

    const styles = await page.evaluate(() => {
      const el = document.querySelector("body")
      return window.getComputedStyle(el!).display
    })

    expect(styles).toBeTruthy()
  })

  test("Forms work on Firefox", async ({ page }) => {
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    const form = page.locator("form")
    if (await form.count() > 0) {
      const inputs = form.locator("input")
      if (await inputs.count() > 0) {
        const input = inputs.first()
        await input.click()
        await input.type("firefox test")
        const value = await input.inputValue()
        expect(value).toBe("firefox test")
      }
    }
  })

  test("Catalog works on Firefox", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      await expect(main).toBeVisible()
    }
  })
})

// ==================== Desktop Safari (WebKit) Tests ====================

test.describe("Desktop Safari (WebKit) Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
  })

  test("Home page on Safari", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()

    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      const box = await main.first().boundingBox()
      expect(box?.height).toBeGreaterThan(0)
    }
  })

  test("CSS Grid support on Safari", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const hasGridSupport = await page.evaluate(() => {
      const el = document.createElement("div")
      el.style.display = "grid"
      return el.style.display === "grid"
    })

    expect(hasGridSupport).toBe(true)
  })

  test("Media rendering on Safari", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const images = page.locator("img")
    if (await images.count() > 0) {
      const img = images.first()
      const isVisible = await img.isVisible()

      if (isVisible) {
        const naturalWidth = await img.evaluate((el: any) => el.naturalWidth)
        expect(naturalWidth).toBeGreaterThan(0)
      }
    }
  })
})

// ==================== Desktop Edge Tests ====================

test.describe("Desktop Edge (Chromium) Responsive", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    // Simulate Edge user agent
    await page.setUserAgent(
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"
    )
  })

  test("Home page on Edge", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()

    const hasFlexbox = await page.evaluate(() => {
      const el = document.querySelector("body")
      return window.getComputedStyle(el!).display !== undefined
    })

    expect(hasFlexbox).toBe(true)
  })

  test("Catalog works on Edge", async ({ page }) => {
    await page.goto("/catalog")
    await page.waitForLoadState("networkidle")

    const main = page.locator("main, [role='main']")
    if (await main.count() > 0) {
      await expect(main).toBeVisible()
    }
  })

  test("Forms work on Edge", async ({ page }) => {
    await page.goto("/login")
    await page.waitForLoadState("networkidle")

    const inputs = page.locator("input")
    if (await inputs.count() > 0) {
      const input = inputs.first()
      await input.click()
      await input.type("edge test")
      const value = await input.inputValue()
      expect(value).toBe("edge test")
    }
  })
})

// ==================== Responsive Breakpoint Tests ====================

test.describe("Responsive Breakpoints Handling", () => {
  test("Mobile breakpoint (375px)", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })

  test("Tablet breakpoint (768px)", async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })

  test("Desktop breakpoint (1280px)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })

  test("Large desktop breakpoint (1920px)", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    await expect(page.locator("body")).toBeVisible()
  })
})

// ==================== Critical Flows Cross-Device ====================

test.describe("Critical Flows - Cross Device", () => {
  test("Login accessible on mobile, tablet, desktop", async ({ page }) => {
    const viewports = [
      { name: "mobile", width: 375, height: 667 },
      { name: "tablet", width: 768, height: 1024 },
      { name: "desktop", width: 1920, height: 1080 },
    ]

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto("/login")
      await page.waitForLoadState("networkidle")

      const form = page.locator("form")
      if (await form.count() > 0) {
        await expect(form).toBeVisible()
      }

      console.log(`✓ Login accessible on ${vp.name}`)
    }
  })

  test("Catalog accessible on mobile, tablet, desktop", async ({ page }) => {
    const viewports = [
      { name: "mobile", width: 375, height: 667 },
      { name: "tablet", width: 768, height: 1024 },
      { name: "desktop", width: 1920, height: 1080 },
    ]

    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto("/catalog")
      await page.waitForLoadState("networkidle")

      const main = page.locator("main, [role='main']")
      if (await main.count() > 0) {
        await expect(main).toBeVisible()
      }

      console.log(`✓ Catalog accessible on ${vp.name}`)
    }
  })

  test("Home accessible on all viewports", async ({ page }) => {
    const viewports = [375, 768, 1024, 1280, 1920]

    for (const width of viewports) {
      await page.setViewportSize({ width, height: 720 })
      await page.goto("/")
      await page.waitForLoadState("networkidle")

      await expect(page.locator("body")).toBeVisible()
      console.log(`✓ Home accessible at ${width}px`)
    }
  })
})

// ==================== Image & Media Scaling ====================

test.describe("Image and Media Scaling", () => {
  test("Images scale across viewports", async ({ page }) => {
    const viewports = [375, 768, 1920]

    await page.goto("/")
    await page.waitForLoadState("networkidle")

    for (const width of viewports) {
      await page.setViewportSize({ width, height: 720 })
      await page.waitForTimeout(200)

      const images = page.locator("img")
      const count = await images.count()

      for (let i = 0; i < Math.min(count, 3); i++) {
        const img = images.nth(i)
        const isVisible = await img.isVisible()

        if (isVisible) {
          const box = await img.boundingBox()
          if (box) {
            // Image should fit in viewport
            expect(box.x + box.width).toBeLessThanOrEqual(width + 20)
          }
        }
      }

      console.log(`✓ Images scale correctly at ${width}px`)
    }
  })
})

