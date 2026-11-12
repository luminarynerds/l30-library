/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test, expect } from "@playwright/test"
import fs from "fs"
import path from "path"
import { fileURLToPath } from "url"
import { API_BASE, API_PREFIX, PERSONAS } from "./smoke.config"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const REPORT_DIR = path.join(__dirname, "../../..", "docs/e2e-reports")
const SCREENSHOTS_DIR = path.join(REPORT_DIR, "screenshots")
const SNAPSHOTS_DIR = path.join(REPORT_DIR, "snapshots")

type PersonaKey = keyof typeof PERSONAS | "public"

interface RouteEntry {
  path: string
  persona: PersonaKey
  label: string
}

const ROUTES: RouteEntry[] = [
  // Public (no auth)
  { path: "/", persona: "public", label: "Home" },
  { path: "/catalog", persona: "public", label: "Catalog" },
  { path: "/events", persona: "public", label: "Events" },
  { path: "/rooms", persona: "public", label: "Rooms" },
  { path: "/about/library", persona: "public", label: "About" },
  { path: "/contact", persona: "public", label: "Contact" },
  { path: "/help", persona: "public", label: "Knowledge Base" },
  { path: "/ask-librarian", persona: "public", label: "Ask a Librarian" },
  { path: "/branches", persona: "public", label: "Branches" },
  { path: "/programs", persona: "public", label: "Reading Programs" },
  { path: "/digital", persona: "public", label: "Digital Resources" },
  { path: "/accessibility", persona: "public", label: "Accessibility" },
  { path: "/privacy", persona: "public", label: "Privacy Policy" },
  { path: "/donate", persona: "public", label: "Donate" },
  { path: "/careers", persona: "public", label: "Careers" },

  // Patron
  { path: "/account", persona: "patron", label: "Patron Account" },
  { path: "/indie", persona: "patron", label: "Indie Catalog" },
  { path: "/notifications", persona: "patron", label: "Notifications" },
  { path: "/suggest-purchase", persona: "patron", label: "Suggest Purchase" },

  // Staff: Circulation
  { path: "/staff", persona: "circulation", label: "Staff Dashboard" },
  { path: "/staff/circulation", persona: "circulation", label: "Circulation" },
  { path: "/staff/book-drop", persona: "circulation", label: "Book Drop" },
  { path: "/staff/patrons", persona: "circulation", label: "Patrons" },
  { path: "/staff/holds/shelf", persona: "circulation", label: "Hold Shelf" },
  { path: "/staff/reports", persona: "circulation", label: "Reports" },

  // Staff: Cataloger
  { path: "/staff/cataloging", persona: "cataloger", label: "Cataloging" },
  { path: "/staff/inventory", persona: "cataloger", label: "Inventory" },

  // Staff: Youth Services
  { path: "/staff/events", persona: "youth", label: "Staff Events" },
  { path: "/staff/attendance", persona: "youth", label: "Attendance" },
  { path: "/staff/program-planning", persona: "youth", label: "Program Planning" },
  { path: "/staff/positivity", persona: "youth", label: "Positivity Hub" },

  // Staff: Acquisitions
  { path: "/staff/acquisition", persona: "acquisitions", label: "Acquisition" },
  { path: "/staff/selection-list", persona: "acquisitions", label: "Selection List" },
  { path: "/staff/funds", persona: "acquisitions", label: "Funds" },
  { path: "/staff/vendors", persona: "acquisitions", label: "Vendors" },
  { path: "/staff/purchase-requests", persona: "acquisitions", label: "Purchase Requests" },

  // Staff: Reference
  { path: "/staff/knowledge-base", persona: "reference", label: "Staff KB" },
  { path: "/staff/analytics", persona: "reference", label: "Analytics" },
  { path: "/staff/message-board", persona: "reference", label: "Message Board" },

  // Indie Author
  { path: "/indie/dashboard", persona: "indie", label: "Indie Dashboard" },
  { path: "/indie/author/register", persona: "indie", label: "Author Register" },
  { path: "/indie/discover", persona: "indie", label: "Indie Discover" },
  { path: "/indie/feed", persona: "indie", label: "Indie Feed" },
]

/** Log in a persona and return the access token. */
async function getToken(persona: PersonaKey): Promise<string | null> {
  if (persona === "public") return null
  const creds = PERSONAS[persona]
  const res = await fetch(`${API_BASE}${API_PREFIX}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: creds.email, password: creds.password }),
  })
  if (!res.ok) {
    console.warn(`Login failed for ${persona}: ${res.status}`)
    return null
  }
  const data = await res.json()
  return data.access_token || null
}

/** Slugify a route path for use as a filename. */
function slug(routePath: string): string {
  return routePath.replace(/^\//, "").replace(/\//g, "-") || "home"
}

test.describe("Exploratory Sweep", () => {
  const manifest: Array<{
    path: string
    label: string
    persona: string
    slug: string
    status: number | null
    title: string
    consoleErrors: string[]
    brokenImages: number
    screenshotPath: string
    snapshotPath: string
  }> = []

  // Token cache to avoid re-logging in per route
  const tokenCache: Partial<Record<PersonaKey, string | null>> = {}

  test.beforeAll(async () => {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })
    fs.mkdirSync(SNAPSHOTS_DIR, { recursive: true })

    // Pre-authenticate all personas with staggered timing
    const personas = [...new Set(ROUTES.map((r) => r.persona))]
    for (let i = 0; i < personas.length; i++) {
      if (i > 0) await new Promise((r) => setTimeout(r, 1500))
      tokenCache[personas[i]] = await getToken(personas[i])
    }
  })

  test.afterAll(async () => {
    // Write manifest
    fs.writeFileSync(
      path.join(REPORT_DIR, "manifest.json"),
      JSON.stringify(manifest, null, 2),
    )
    console.log(`\nExploratory sweep complete: ${manifest.length} pages captured`)
    console.log(`Manifest: docs/e2e-reports/manifest.json`)
  })

  for (const route of ROUTES) {
    test(`${route.label} (${route.path})`, async ({ page, context }) => {
      const pageSlug = slug(route.path)
      const consoleErrors: string[] = []

      // Collect console errors
      page.on("console", (msg) => {
        if (msg.type() === "error") {
          consoleErrors.push(msg.text())
        }
      })

      // Set auth if needed — must navigate to origin first to access localStorage
      const token = tokenCache[route.persona]
      if (token) {
        await page.goto("/login", { waitUntil: "domcontentloaded", timeout: 10000 })
        await page.evaluate((t) => {
          localStorage.setItem("access_token", t)
        }, token)
      }

      // Navigate to the actual route
      const response = await page.goto(route.path, {
        waitUntil: "domcontentloaded",
        timeout: 15000,
      })
      await page.waitForTimeout(1500) // settle time

      const status = response?.status() ?? null
      const title = await page.title()

      // Screenshot
      const screenshotFile = `screenshots/${pageSlug}.png`
      await page.screenshot({
        path: path.join(REPORT_DIR, screenshotFile),
        fullPage: true,
      })

      // Accessibility snapshot (ARIA tree)
      const snapshotFile = `snapshots/${pageSlug}.md`
      let snapshotText: string
      try {
        snapshotText = await page.locator("body").ariaSnapshot()
      } catch {
        snapshotText = "(snapshot unavailable)"
      }
      fs.writeFileSync(
        path.join(REPORT_DIR, snapshotFile),
        `# ${route.label} (${route.path})\n\n\`\`\`yaml\n${snapshotText}\n\`\`\`\n`,
      )

      // Broken images check
      const brokenImages = await page.evaluate(() => {
        const imgs = document.querySelectorAll("img[src]")
        let broken = 0
        imgs.forEach((img) => {
          const el = img as HTMLImageElement
          if (el.complete && el.naturalWidth === 0) broken++
        })
        return broken
      })

      // Record in manifest
      manifest.push({
        path: route.path,
        label: route.label,
        persona: route.persona,
        slug: pageSlug,
        status,
        title,
        consoleErrors,
        brokenImages,
        screenshotPath: screenshotFile,
        snapshotPath: snapshotFile,
      })

      // Soft assertions — don't fail the sweep, just record
      if (status && status >= 500) {
        console.warn(`[WARN] ${route.path} returned ${status}`)
      }
      if (brokenImages > 0) {
        console.warn(`[WARN] ${route.path} has ${brokenImages} broken image(s)`)
      }
      if (consoleErrors.length > 0) {
        console.warn(`[WARN] ${route.path} has ${consoleErrors.length} console error(s)`)
      }

      // Only fail on 5xx — everything else is recorded for AI review
      expect(status ?? 200).toBeLessThan(500)
    })
  }
})
