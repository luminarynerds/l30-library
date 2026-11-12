/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { RUN_ID } from "../smoke.config"
import { SmokeApiClient } from "./api"

/**
 * Run bidirectional cleanup: call before AND after each spec.
 * Logs warnings on failure but never throws.
 */
export async function cleanupTestData(client: SmokeApiClient): Promise<void> {
  await client.cleanup(RUN_ID)
}
