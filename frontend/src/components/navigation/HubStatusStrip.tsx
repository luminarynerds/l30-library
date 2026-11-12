/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/contexts/AuthContext";

export interface HubStat {
  key: string;
  value: number;
  label: string;
  urgent?: boolean;
}

interface HubStatsResponse {
  hub_slug: string;
  stats: HubStat[];
}

interface HubStatusStripProps {
  hubSlug: string;
  className?: string;
}

const ALLOWED_ROLES = new Set(["staff", "admin", "super_admin", "director"]);

const URGENT_CLASSES =
  "bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200 border-status-danger-300 dark:border-status-danger-700";

const NEUTRAL_CLASSES =
  "bg-lsc-cream dark:bg-lsc-dark/40 text-lsc-dark dark:text-lsc-cream border-lsc-dark/15 dark:border-lsc-cream/15";

export default function HubStatusStrip({ hubSlug, className }: HubStatusStripProps) {
  const { user } = useAuth();
  const [stats, setStats] = useState<HubStat[] | null>(null);

  const isAllowed = !!user && ALLOWED_ROLES.has(user.role);

  useEffect(() => {
    if (!isAllowed) return;
    const controller = new AbortController();
    let cancelled = false;
    api
      .get<HubStatsResponse>(`/api/v1/hub-stats/${hubSlug}`, { signal: controller.signal })
      .then((res) => {
        if (cancelled) return;
        setStats(Array.isArray(res?.stats) ? res.stats : []);
      })
      .catch((err) => {
        if (cancelled) return;
        // Silent failure: this surface is not load-bearing.
        console.debug("HubStatusStrip: failed to load hub stats", err);
        setStats(null);
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [hubSlug, isAllowed]);

  if (!isAllowed) return null;
  if (stats === null) return null;
  if (stats.length === 0) return null;

  const ariaLabel = `Hub status: ${stats
    .map((s) => `${s.value} ${s.label.toLowerCase()}`)
    .join(", ")}`;

  return (
    <div
      role="status"
      aria-label={ariaLabel}
      className={`flex flex-wrap items-center gap-2 ${className ?? ""}`.trim()}
      data-testid="hub-status-strip"
    >
      {stats.map((stat) => (
        <span
          key={stat.key}
          data-testid={`hub-status-chip-${stat.key}`}
          data-urgent={stat.urgent ? "true" : "false"}
          className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
            stat.urgent ? URGENT_CLASSES : NEUTRAL_CLASSES
          }`}
        >
          <span className="font-semibold tabular-nums">{stat.value}</span>
          <span>{stat.label}</span>
        </span>
      ))}
    </div>
  );
}
