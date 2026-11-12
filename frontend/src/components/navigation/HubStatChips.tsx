/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react";
import { AlertTriangle, Info } from "lucide-react";
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

interface HubStatChipsProps {
  hubSlug: string;
  className?: string;
}

const ALLOWED_ROLES = new Set(["staff", "admin", "super_admin", "director"]);

const URGENT_CLASSES =
  "bg-status-danger-100 dark:bg-status-danger-900 text-status-danger-800 dark:text-status-danger-200 border-status-danger-300 dark:border-status-danger-700";

const NEUTRAL_CLASSES =
  "bg-lsc-cream dark:bg-lsc-dark/40 text-lsc-dark dark:text-lsc-cream border-lsc-dark/15 dark:border-lsc-cream/15";

export default function HubStatChips({ hubSlug, className }: HubStatChipsProps) {
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
        console.debug("HubStatChips: failed to load hub stats", err);
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

  return (
    <div
      className={`flex flex-wrap items-center gap-1.5 ${className ?? ""}`.trim()}
      data-testid="hub-stat-chips"
    >
      {stats.map((stat) => {
        const Icon = stat.urgent ? AlertTriangle : Info;
        const ariaLabel = stat.urgent
          ? `${stat.value} ${stat.label} (urgent)`
          : `${stat.value} ${stat.label}`;
        return (
          <span
            key={stat.key}
            aria-label={ariaLabel}
            data-testid={`hub-stat-chip-${stat.key}`}
            data-urgent={stat.urgent ? "true" : "false"}
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium leading-5 ${
              stat.urgent ? URGENT_CLASSES : NEUTRAL_CLASSES
            }`}
          >
            <Icon className="w-3 h-3" aria-hidden="true" />
            <span className="font-semibold tabular-nums">{stat.value}</span>
            <span>{stat.label}</span>
          </span>
        );
      })}
    </div>
  );
}
