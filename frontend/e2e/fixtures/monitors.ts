/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { test as base, expect } from "@playwright/test"

type ConsoleError = { type: string; text: string; url: string }
type NetworkError = { url: string; status: number; method: string }

type MonitorFixtures = {
  consoleErrors: ConsoleError[]
  networkErrors: NetworkError[]
}

export const test = base.extend<MonitorFixtures>({
  consoleErrors: async ({ page }, use) => {
    const errors: ConsoleError[] = []
    page.on("console", msg => {
      if (msg.type() === "error") {
        const text = msg.text()
        // Ignore known noise
        if (
          text.includes("favicon") ||
          text.includes("ERR_BLOCKED_BY_CLIENT") ||
          text.includes("net::ERR_") ||
          text.includes("Failed to load resource")
        )
          return
        errors.push({ type: msg.type(), text, url: page.url() })
      }
    })
    page.on("pageerror", err => {
      errors.push({ type: "pageerror", text: err.message, url: page.url() })
    })
    await use(errors)
  },

  networkErrors: async ({ page }, use) => {
    const errors: NetworkError[] = []
    page.on("response", response => {
      if (response.status() >= 500) {
        errors.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        })
      }
    })
    await use(errors)
  },
})

export { expect }

export function assertNoErrors(
  consoleErrors: ConsoleError[],
  networkErrors: NetworkError[],
  options?: { ignoreConsolePatterns?: RegExp[] }
) {
  const ignorePatterns = options?.ignoreConsolePatterns || []
  const filteredConsoleErrors = consoleErrors.filter(
    e => !ignorePatterns.some(p => p.test(e.text))
  )

  if (filteredConsoleErrors.length > 0) {
    const details = filteredConsoleErrors
      .map(e => `  [${e.type}] ${e.text} (on ${e.url})`)
      .join("\n")
    throw new Error(`Unexpected console errors:\${details}`)
  }

  if (networkErrors.length > 0) {
    const details = networkErrors
      .map(e => `  ${e.method} ${e.url} -> ${e.status}`)
      .join("\n")
    throw new Error(`HTTP 500+ responses:\${details}`)
  }
}
