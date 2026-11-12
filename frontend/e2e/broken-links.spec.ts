/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"

/**
 * Broken Links Detection Tests
 *
 * Crawls public pages and validates all links:
 * - Internal links should return 200-399 status codes
 * - External links are checked for validity
 * - Anchor links should have matching targets
 * - Images should load successfully
 */

// Pages to crawl for links
const pagesToCheck = [
  "/",
  "/catalog",
  "/events",
  "/programs",
  "/digital",
  "/ai",
  "/ai/how-it-works",
  "/about",
  "/about/our-story",
  "/contact",
  "/privacy",
  "/accessibility",
  "/tech",
  "/makerspace",
  "/learn",
  "/learning-paths",
]

interface LinkResult {
  url: string
  status: number | "error"
  sourceUrl: string
  error?: string
}

test.describe("Broken Links Detection", () => {
  test("should have no broken internal links on home page", async ({ page, request }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Get all internal links
    const links = await page.locator("a[href]").all()
    const brokenLinks: LinkResult[] = []

    for (const link of links) {
      const href = await link.getAttribute("href")
      if (!href) continue

      // Skip external links, mailto, tel, and anchor-only links
      if (
        href.startsWith("http") ||
        href.startsWith("mailto:") ||
        href.startsWith("tel:") ||
        href === "#" ||
        href.startsWith("#")
      ) {
        continue
      }

      // Resolve relative URLs
      const fullUrl = new URL(href, page.url()).href

      try {
        const response = await request.get(fullUrl)
        if (response.status() >= 400) {
          brokenLinks.push({
            url: href,
            status: response.status(),
            sourceUrl: page.url(),
          })
        }
      } catch (error) {
        brokenLinks.push({
          url: href,
          status: "error",
          sourceUrl: page.url(),
          error: String(error),
        })
      }
    }

    // Log broken links for debugging
    if (brokenLinks.length > 0) {
      console.log("Broken links found:")
      brokenLinks.forEach((link) => {
        console.log(`  ${link.url} -> ${link.status}`)
      })
    }

    expect(brokenLinks).toEqual([])
  })

  test("should have no broken links across all main public pages", async ({ page, request }) => {
    const checkedUrls = new Set<string>()
    const brokenLinks: LinkResult[] = []

    for (const pageUrl of pagesToCheck) {
      await page.goto(pageUrl)
      await page.waitForLoadState("networkidle")

      const links = await page.locator("a[href]").all()

      for (const link of links) {
        const href = await link.getAttribute("href")
        if (!href) continue

        // Skip non-internal links
        if (
          href.startsWith("http") ||
          href.startsWith("mailto:") ||
          href.startsWith("tel:") ||
          href === "#"
        ) {
          continue
        }

        // Handle anchor links separately
        if (href.startsWith("#")) {
          const targetId = href.slice(1)
          const target = page.locator(`#${targetId}`)
          if ((await target.count()) === 0) {
            brokenLinks.push({
              url: href,
              status: "error",
              sourceUrl: pageUrl,
              error: "Anchor target not found",
            })
          }
          continue
        }

        // Resolve relative URLs
        const fullUrl = new URL(href, page.url()).href

        // Skip already checked URLs
        if (checkedUrls.has(fullUrl)) continue
        checkedUrls.add(fullUrl)

        try {
          const response = await request.get(fullUrl)
          if (response.status() >= 400) {
            brokenLinks.push({
              url: href,
              status: response.status(),
              sourceUrl: pageUrl,
            })
          }
        } catch (error) {
          brokenLinks.push({
            url: href,
            status: "error",
            sourceUrl: pageUrl,
            error: String(error),
          })
        }
      }
    }

    // Log summary
    console.log(`Checked ${checkedUrls.size} unique URLs across ${pagesToCheck.length} pages`)

    if (brokenLinks.length > 0) {
      console.log("Broken links found:")
      brokenLinks.forEach((link) => {
        console.log(`  [${link.sourceUrl}] ${link.url} -> ${link.status}`)
        if (link.error) console.log(`    Error: ${link.error}`)
      })
    }

    expect(brokenLinks).toEqual([])
  })

  test("should have no broken images on home page", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const images = await page.locator("img").all()
    const brokenImages: { src: string; error: string }[] = []

    for (const img of images) {
      const src = await img.getAttribute("src")
      if (!src) continue

      // Check if image loaded successfully
      const naturalWidth = await img.evaluate(
        (el: HTMLImageElement) => el.naturalWidth
      )

      if (naturalWidth === 0) {
        brokenImages.push({
          src,
          error: "Image failed to load (naturalWidth is 0)",
        })
      }
    }

    if (brokenImages.length > 0) {
      console.log("Broken images found:")
      brokenImages.forEach((img) => {
        console.log(`  ${img.src}: ${img.error}`)
      })
    }

    expect(brokenImages).toEqual([])
  })

  test("should have no broken images across all public pages", async ({ page }) => {
    const brokenImages: { src: string; pageUrl: string }[] = []

    for (const pageUrl of pagesToCheck) {
      await page.goto(pageUrl)
      await page.waitForLoadState("networkidle")

      const images = await page.locator("img").all()

      for (const img of images) {
        const src = await img.getAttribute("src")
        if (!src) continue

        const naturalWidth = await img.evaluate(
          (el: HTMLImageElement) => el.naturalWidth
        )

        if (naturalWidth === 0) {
          brokenImages.push({ src, pageUrl })
        }
      }
    }

    if (brokenImages.length > 0) {
      console.log("Broken images found:")
      brokenImages.forEach((img) => {
        console.log(`  [${img.pageUrl}] ${img.src}`)
      })
    }

    expect(brokenImages).toEqual([])
  })
})

test.describe("Navigation Links", () => {
  test("header navigation links should work", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // Test main navigation links
    const headerNav = page.locator('[aria-label="Main navigation"]')

    // Home link
    const homeLink = headerNav.locator('a[href="/"]').first()
    if ((await homeLink.count()) > 0) {
      await expect(homeLink).toBeVisible()
    }
  })

  test("footer links should be valid", async ({ page, request }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    const footer = page.locator("footer")
    const footerLinks = await footer.locator("a[href]").all()
    const brokenLinks: LinkResult[] = []

    for (const link of footerLinks) {
      const href = await link.getAttribute("href")
      if (!href) continue

      // Skip external links and special protocols
      if (
        href.startsWith("http") ||
        href.startsWith("mailto:") ||
        href.startsWith("tel:")
      ) {
        continue
      }

      // Test internal links
      if (!href.startsWith("#")) {
        const fullUrl = new URL(href, page.url()).href
        const response = await request.get(fullUrl)
        if (response.status() >= 400) {
          brokenLinks.push({
            url: href,
            status: response.status(),
            sourceUrl: "footer",
          })
        }
      }
    }

    expect(brokenLinks).toEqual([])
  })
})

test.describe("External Links", () => {
  test("external links should have proper attributes", async ({ page }) => {
    await page.goto("/")
    await page.waitForLoadState("networkidle")

    // External links should have rel="noopener" or "noreferrer" for security
    const externalLinks = await page.locator('a[href^="http"]').all()
    const insecureLinks: string[] = []

    for (const link of externalLinks) {
      const href = await link.getAttribute("href")
      const rel = await link.getAttribute("rel")
      const target = await link.getAttribute("target")

      // If opening in new tab, should have security attributes
      if (target === "_blank" && (!rel || !rel.includes("noopener"))) {
        if (href) insecureLinks.push(href)
      }
    }

    if (insecureLinks.length > 0) {
      console.log("External links without rel='noopener':")
      insecureLinks.forEach((link) => console.log(`  ${link}`))
    }

    // Enforce security attributes on external links
    expect(insecureLinks).toEqual([])
  })

  test("external links should be reachable", async ({ page, request }) => {
    // Only check the digital resources page which has external links
    await page.goto("/digital")
    await page.waitForLoadState("networkidle")

    const externalLinks = await page.locator('a[href^="http"]').all()
    const checkedUrls = new Set<string>()
    const brokenLinks: LinkResult[] = []
    const slowLinks: { url: string; responseTime: number }[] = []

    // Timeout for external requests (10 seconds)
    const EXTERNAL_TIMEOUT = 10000
    // Threshold for slow links (5 seconds)
    const SLOW_THRESHOLD = 5000

    for (const link of externalLinks) {
      const href = await link.getAttribute("href")
      if (!href) continue

      // Skip already checked URLs
      if (checkedUrls.has(href)) continue
      checkedUrls.add(href)

      // Skip known tracking/analytics URLs
      if (
        href.includes("google-analytics") ||
        href.includes("googletagmanager") ||
        href.includes("facebook.com/tr") ||
        href.includes("doubleclick.net")
      ) {
        continue
      }

      const startTime = Date.now()

      try {
        // Use HEAD request first (faster), fall back to GET
        const response = await request.head(href, {
          timeout: EXTERNAL_TIMEOUT,
          ignoreHTTPSErrors: true, // Allow self-signed certs in dev
        }).catch(() =>
          request.get(href, {
            timeout: EXTERNAL_TIMEOUT,
            ignoreHTTPSErrors: true,
          })
        )

        const responseTime = Date.now() - startTime

        if (response.status() >= 400) {
          brokenLinks.push({
            url: href,
            status: response.status(),
            sourceUrl: "/digital",
          })
        } else if (responseTime > SLOW_THRESHOLD) {
          slowLinks.push({ url: href, responseTime })
        }
      } catch (error) {
        brokenLinks.push({
          url: href,
          status: "error",
          sourceUrl: "/digital",
          error: String(error),
        })
      }
    }

    // Log results
    console.log(`Checked ${checkedUrls.size} external URLs`)

    if (slowLinks.length > 0) {
      console.log("Slow external links (>5s):")
      slowLinks.forEach((link) =>
        console.log(`  ${link.url} - ${link.responseTime}ms`)
      )
    }

    if (brokenLinks.length > 0) {
      console.log("Broken external links:")
      brokenLinks.forEach((link) => {
        console.log(`  ${link.url} -> ${link.status}`)
        if (link.error) console.log(`    Error: ${link.error}`)
      })
    }

    // Fail if any critical external links are broken
    expect(brokenLinks).toEqual([])
  })
})

test.describe("Digital Platform Links", () => {
  // Critical digital platform URLs that must be reachable
  const digitalPlatformUrls = [
    {
      name: "OverDrive",
      url: "https://www.overdrive.com",
      critical: true,
    },
    {
      name: "Libby App",
      url: "https://www.overdrive.com/apps/libby",
      critical: true,
    },
    {
      name: "Hoopla",
      url: "https://www.hoopladigital.com",
      critical: true,
    },
    {
      name: "Kanopy",
      url: "https://www.kanopy.com",
      critical: true,
    },
  ]

  test("critical digital platform URLs should be reachable", async ({
    request,
  }) => {
    const results: {
      name: string
      url: string
      status: number | "error"
      responseTime: number
      error?: string
    }[] = []

    for (const platform of digitalPlatformUrls) {
      const startTime = Date.now()

      try {
        const response = await request.head(platform.url, {
          timeout: 15000,
          ignoreHTTPSErrors: true,
        }).catch(() =>
          request.get(platform.url, {
            timeout: 15000,
            ignoreHTTPSErrors: true,
          })
        )

        results.push({
          name: platform.name,
          url: platform.url,
          status: response.status(),
          responseTime: Date.now() - startTime,
        })
      } catch (error) {
        results.push({
          name: platform.name,
          url: platform.url,
          status: "error",
          responseTime: Date.now() - startTime,
          error: String(error),
        })
      }
    }

    // Log all results
    console.log("\nDigital Platform Health Check:")
    console.log("================================")
    results.forEach((result) => {
      const statusIcon =
        result.status === 200 || result.status === 301 || result.status === 302
          ? "✓"
          : "✗"
      console.log(
        `${statusIcon} ${result.name}: ${result.status} (${result.responseTime}ms)`
      )
      if (result.error) {
        console.log(`  Error: ${result.error}`)
      }
    })

    // Check critical platforms
    const failedCritical = results.filter(
      (r) =>
        digitalPlatformUrls.find((p) => p.url === r.url)?.critical &&
        (r.status === "error" ||
          (typeof r.status === "number" && r.status >= 400))
    )

    if (failedCritical.length > 0) {
      console.log("\nCritical platforms failed:")
      failedCritical.forEach((r) => console.log(`  - ${r.name}: ${r.status}`))
    }

    // Only fail on critical platform errors
    expect(failedCritical).toEqual([])
  })

  test("digital resources page should load without console errors", async ({
    page,
  }) => {
    const consoleErrors: string[] = []

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text())
      }
    })

    await page.goto("/digital")
    await page.waitForLoadState("networkidle")

    // Filter out known third-party errors
    const relevantErrors = consoleErrors.filter(
      (error) =>
        !error.includes("Failed to load resource") && // Network errors for optional resources
        !error.includes("favicon") && // Favicon errors
        !error.includes("third-party") // Third-party script errors
    )

    if (relevantErrors.length > 0) {
      console.log("Console errors on /digital page:")
      relevantErrors.forEach((error) => console.log(`  ${error}`))
    }

    expect(relevantErrors).toEqual([])
  })
})
