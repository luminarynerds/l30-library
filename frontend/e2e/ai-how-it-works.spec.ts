/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

/**
 * E2E coverage for /ai/how-it-works — the philosophy + receipts route split
 * out from /ai in PR #816.
 *
 * Tests target structure/semantics (section ids, ARIA roles, hrefs) rather
 * than copy verbatim, so minor wording edits to the page don't break them.
 *
 * The /ai/how-it-works route is feature-gated behind `ai_tools_enabled`, but
 * RequireFeature renders children optimistically while flags load, so a fresh
 * page load reliably renders the page contents.
 */

const ROUTE = "/ai/how-it-works"

test.describe("AI How It Works — Load & Console", () => {
  test("page loads with success status and a title", async ({ page }) => {
    const response = await page.goto(ROUTE)
    expect(response?.status()).toBeLessThan(400)
    await expect(page).toHaveTitle(/.+/)
    await expect(page.locator("body")).toBeVisible()
  })

  test("page emits no console errors above warn level", async ({ page }) => {
    const consoleErrors: string[] = []
    page.on("console", (msg) => {
      if (msg.type() !== "error") return
      const text = msg.text()
      // Ignore noise unrelated to the page: favicon, network-level errors,
      // missing optional assets.
      if (text.includes("favicon") || text.includes("net::ERR_")) return
      consoleErrors.push(text)
    })

    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    expect(consoleErrors).toEqual([])
  })
})

test.describe("AI How It Works — Structure", () => {
  test("renders exactly one h1 with the page title", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    const h1 = page.getByRole("heading", { level: 1 })
    await expect(h1).toHaveCount(1)
    // Tolerant match — the i18n default is "How AI works at L30".
    await expect(h1).toHaveText(/How AI works/i)
  })

  test("Back-to-/ai link is present and points to /ai", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    const backLink = page.getByRole("link", { name: /Back to AI tools/i })
    await expect(backLink).toBeVisible()

    const href = await backLink.getAttribute("href")
    // SPA link — react-router renders /ai without query/hash.
    expect(href).toBe("/ai")
  })

  test("Back-to-/ai link navigates to /ai", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    await page.getByRole("link", { name: /Back to AI tools/i }).click()
    await page.waitForURL("**/ai")
    expect(new URL(page.url()).pathname).toBe("/ai")
  })

  test("global skip-to-content link is the first focusable element", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    // Skip link is rendered globally by Layout.tsx; assert it exists and is
    // the first thing keyboard users land on.
    const skipLink = page.locator('a[href="#main-content"]')
    await expect(skipLink).toBeAttached()

    await page.keyboard.press("Tab")
    const focused = page.locator(":focus")
    await expect(focused).toBeVisible()
    const focusedHref = await focused.getAttribute("href")
    expect(focusedHref).toBe("#main-content")
  })

  test("Sensory Quiet Mode entry button is present", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    // SensoryQuietEntry returns null when already in Essentials/Quiet mode;
    // a fresh load on a clean storage state should show the entry button.
    const sensoryButton = page.getByRole("button", { name: /Sensory Quiet Mode/i })
    await expect(sensoryButton).toBeVisible()
  })
})

test.describe("AI How It Works — Key Sections", () => {
  test("DataFlowMatrix renders patron + staff tool groupings", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    // Per-tool data flow has two grouping headings; both must render.
    await expect(
      page.getByRole("heading", { name: /Tools you can use/i }),
    ).toBeVisible()
    await expect(
      page.getByRole("heading", { name: /Tools staff use/i }),
    ).toBeVisible()
  })

  test("WrongnessLog section renders with H2 + reviewed date", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    // Section id is "wrongness"; label is the H2 inside.
    const wrongnessSection = page.locator("section#wrongness")
    await expect(wrongnessSection).toBeVisible()

    const wrongnessHeading = page.getByRole("heading", {
      level: 2,
      name: /When the AI was wrong/i,
    })
    await expect(wrongnessHeading).toBeVisible()

    // "Page reviewed:" line lives in the WrongnessLog footer, not LegalNote.
    await expect(wrongnessSection).toContainText(/Page reviewed:/i)
  })

  test("LegalNote renders with a link to /ai/legal", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    const legalLink = page.getByRole("link", { name: /Full legal disclaimers/i })
    await expect(legalLink).toBeVisible()
    expect(await legalLink.getAttribute("href")).toBe("/ai/legal")
  })

  test("Table of Contents lists the in-page section anchors", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    // TOC entries are anchor links to the section ids defined in
    // AIToolsHowItWorksPage.tsx. Spot-check the rubric anchor — it's also
    // linked from /about with #rubric, so a regression would break that
    // cross-page deep link.
    const rubricAnchor = page.locator('a[href="#rubric"]').first()
    await expect(rubricAnchor).toBeVisible()
  })
})

test.describe("AI How It Works — Accessibility (WCAG 2.1 AA)", () => {
  test("page passes axe accessibility audit", async ({ page }) => {
    await page.goto(ROUTE)
    await page.waitForLoadState("networkidle")

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze()

    if (accessibilityScanResults.violations.length > 0) {
      console.log(`Accessibility violations on ${ROUTE}:`)
      accessibilityScanResults.violations.forEach((violation) => {
        console.log(`  - ${violation.id}: ${violation.description}`)
        violation.nodes.forEach((node) => {
          console.log(`    Target: ${node.target}`)
        })
      })
    }

    expect(accessibilityScanResults.violations).toEqual([])
  })
})
