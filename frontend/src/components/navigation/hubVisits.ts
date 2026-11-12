/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from "@/lib/api-client";

export function logHubVisit(hubSlug: string, itemPath: string): void {
  api.post("/api/v1/hub-visits", { hub_slug: hubSlug, item_path: itemPath }).catch(() => {
    // Silent failure: visit logging is non-critical.
  });
}
