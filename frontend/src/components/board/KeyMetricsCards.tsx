/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, DollarSign, Users, Library } from "lucide-react";
import { TrendBadge } from "./TrendBadge";
import type { ReportStats } from "./BoardReportTypes";

export function KeyMetricsCards({ data }: { data: ReportStats }) {
  const metrics = [
    {
      label: "Total Checkouts",
      value: data.circulation.total_checkouts.toLocaleString(),
      icon: BookOpen,
      color: "text-lsc-rose dark:text-lsc-rose-light",
      bgColor: "bg-earth-50 dark:bg-earth-800/30",
      trend: data.trends?.checkout_change_percent,
    },
    {
      label: "Revenue",
      value: `$${data.financial.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`,
      icon: DollarSign,
      color: "text-status-success-600 dark:text-status-success-400",
      bgColor: "bg-status-success-50 dark:bg-status-success-900/30",
      trend: data.trends?.revenue_change_percent,
    },
    {
      label: "Active Patrons",
      value: data.patrons.active_patrons.toLocaleString(),
      icon: Users,
      color: "text-status-warning-600 dark:text-status-warning-400",
      bgColor: "bg-status-warning-50 dark:bg-status-warning-900/30",
      trend: data.trends?.patron_engagement_change_percent,
    },
    {
      label: "Collection Items",
      value: data.collection.total_items.toLocaleString(),
      icon: Library,
      color: "text-category-600 dark:text-category-400",
      bgColor: "bg-category-50 dark:bg-category-900/30",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className={`${metric.bgColor} rounded-lg p-4 border border-lsc-border dark:border-earth-700`}
        >
          <div className="flex items-center justify-between mb-2">
            <metric.icon className={`w-5 h-5 ${metric.color}`} />
            {metric.trend !== undefined && (
              <TrendBadge value={metric.trend} />
            )}
          </div>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{metric.value}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{metric.label}</p>
        </div>
      ))}
    </div>
  );
}
