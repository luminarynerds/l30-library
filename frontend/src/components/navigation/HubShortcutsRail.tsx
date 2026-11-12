/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api-client";
import { useAuth } from "@/contexts/AuthContext";
import { buildHubRegistry, type HubItemEntry } from "./hubRegistry";

interface ShortcutEntry {
  item_path: string;
  visit_count: number;
  last_visited_at: string;
}

interface HubShortcutsResponse {
  hub_slug: string;
  shortcuts: ShortcutEntry[];
}

interface HubShortcutsRailProps {
  hubSlug: string;
  className?: string;
}

// Patrons see explicit favorites elsewhere; this rail is staff/admin-only.
const STAFF_ROLES = new Set([
  "staff",
  "admin",
  "super_admin",
  "director",
  "legal",
]);

export default function HubShortcutsRail({ hubSlug, className }: HubShortcutsRailProps) {
  const { user } = useAuth();
  const [shortcuts, setShortcuts] = useState<ShortcutEntry[] | null>(null);

  const isStaff = !!user && STAFF_ROLES.has(user.role);

  useEffect(() => {
    if (!isStaff) return;
    const controller = new AbortController();
    let cancelled = false;
    api
      .get<HubShortcutsResponse>(`/api/v1/hub-shortcuts/${hubSlug}`, {
        params: { limit: 5 },
        signal: controller.signal,
      })
      .then((res) => {
        if (cancelled) return;
        setShortcuts(Array.isArray(res?.shortcuts) ? res.shortcuts : []);
      })
      .catch((err) => {
        if (cancelled) return;
        // Silent failure: this surface is not load-bearing.
        console.debug("HubShortcutsRail: failed to load shortcuts", err);
        setShortcuts(null);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [hubSlug, isStaff]);

  // Index registry entries by item path for label + icon lookup.
  const entriesByPath = useMemo<Map<string, HubItemEntry>>(() => {
    const out = new Map<string, HubItemEntry>();
    for (const entry of buildHubRegistry()) {
      // Last-write wins; paths shared across hubs (e.g. /staff/admin/legal in
      // both Library and Admin Settings) will use whichever hub registers last.
      out.set(entry.itemPath, entry);
    }
    return out;
  }, []);

  if (!isStaff) return null;
  if (shortcuts === null) return null;
  if (shortcuts.length === 0) return null;

  const resolved = shortcuts
    .map((sc) => {
      const entry = entriesByPath.get(sc.item_path);
      if (!entry) return null;
      return { sc, entry };
    })
    .filter((x): x is { sc: ShortcutEntry; entry: HubItemEntry } => x !== null);

  if (resolved.length === 0) return null;

  return (
    <nav
      aria-label="Your most-visited shortcuts in this hub"
      data-testid="hub-shortcuts-rail"
      className={`mb-4 flex flex-wrap items-center gap-2 ${className ?? ""}`.trim()}
    >
      <span className="text-xs font-medium uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">
        Your shortcuts
      </span>
      {resolved.map(({ sc, entry }) => (
        <Link
          key={sc.item_path}
          to={sc.item_path}
          data-testid={`hub-shortcut-${sc.item_path}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-lsc-border bg-lsc-cream/60 px-3 py-1 text-xs font-medium text-lsc-dark transition-colors hover:border-lsc-rose/40 hover:bg-lsc-rose/10 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 dark:border-earth-600 dark:bg-earth-700 dark:text-lsc-cream dark:hover:bg-lsc-rose/20"
        >
          <span>{entry.itemLabel}</span>
          <span
            aria-label={`${sc.visit_count} visits`}
            className="rounded-full bg-lsc-rose/10 px-1.5 text-[10px] font-semibold text-lsc-rose tabular-nums"
          >
            {sc.visit_count}
          </span>
        </Link>
      ))}
    </nav>
  );
}
