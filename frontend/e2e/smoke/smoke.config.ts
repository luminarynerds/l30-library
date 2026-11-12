/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { randomBytes } from "crypto"

/** Unique run ID for this smoke test execution. Used to tag and clean up test data. */
export const RUN_ID = `smoke-${new Date().toISOString().slice(0, 10)}-${randomBytes(4).toString("hex")}`

/** Prefix added to all test-created record titles for identification and cleanup. */
export function testPrefix(): string {
  return `[TEST:${RUN_ID}]`
}

/** Base URL for API calls (backend). */
export const API_BASE = process.env.API_URL || "http://localhost:8081"

/** API path prefix. */
export const API_PREFIX = "/api/v1"

/** Smoke test account credentials. */
export const SMOKE_PASSWORD = process.env.SMOKE_TEST_PASSWORD || "SmokeTest123!"

export const PERSONAS = {
  circulation: { email: "test-circ@l30.org", password: SMOKE_PASSWORD },
  cataloger: { email: "test-cataloger@l30.org", password: SMOKE_PASSWORD },
  youth: { email: "test-youth@l30.org", password: SMOKE_PASSWORD },
  acquisitions: { email: "test-acquisitions@l30.org", password: SMOKE_PASSWORD },
  reference: { email: "test-reference@l30.org", password: SMOKE_PASSWORD },
  director: { email: "test-director@l30.org", password: SMOKE_PASSWORD },
  patron: { email: "test-patron@l30.org", password: SMOKE_PASSWORD },
  child: { email: "test-child@l30.org", password: SMOKE_PASSWORD },
  indie: { email: "test-indie@l30.org", password: SMOKE_PASSWORD },
} as const
