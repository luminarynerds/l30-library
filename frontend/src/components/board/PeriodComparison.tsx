/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TrendingUp } from "lucide-react";
import { TrendBadge } from "./TrendBadge";
import type { ReportStats } from "./BoardReportTypes";

export function PeriodComparison({ data }: { data: ReportStats }) {
  if (!data.comparison || !data.trends) {
    return (
      <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-status-warning-600" />
          Period Comparison
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">
          No comparison data available. Generate a report with comparison enabled.
        </p>
      </div>
    );
  }

  const comparisons = [
    {
      label: "Checkouts",
      current: data.circulation.total_checkouts,
      previous: data.comparison.circulation.total_checkouts,
      change: data.trends.checkout_change_percent,
    },
    {
      label: "Revenue",
      current: data.financial.total_revenue,
      previous: data.comparison.financial.total_revenue,
      change: data.trends.revenue_change_percent,
      isCurrency: true,
    },
    {
      label: "Active Patrons",
      current: data.patrons.active_patrons,
      previous: data.comparison.patrons.active_patrons,
      change: data.trends.patron_engagement_change_percent,
    },
    {
      label: "New Patrons",
      current: data.patrons.new_patrons,
      previous: data.comparison.patrons.new_patrons,
    },
  ];

  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-status-warning-600" />
        Period Comparison
      </h3>

      <div className="space-y-3">
        {comparisons.map((item) => {
          const formatVal = (v: number) =>
            item.isCurrency
              ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 0 })}`
              : v.toLocaleString();

          return (
            <div key={item.label} className="flex items-center justify-between py-2 border-b border-earth-100 dark:border-earth-800 last:border-0">
              <div>
                <p className="text-sm font-medium text-earth-800 dark:text-earth-200">{item.label}</p>
                <div className="flex gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                  <span>Current: {formatVal(item.current)}</span>
                  <span>Previous: {formatVal(item.previous)}</span>
                </div>
              </div>
              {item.change !== undefined && <TrendBadge value={item.change} />}
            </div>
          );
        })}
      </div>

      <div className="mt-4 p-3 bg-earth-50 dark:bg-earth-800 rounded-lg text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        Comparison period: {new Date(data.comparison.period.start_date).toLocaleDateString()} - {new Date(data.comparison.period.end_date).toLocaleDateString()}
      </div>
    </div>
  );
}
