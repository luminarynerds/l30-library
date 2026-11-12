/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { DollarSign } from "lucide-react";
import { CHART_COLORS } from "./BoardReportTypes";
import type { ReportStats } from "./BoardReportTypes";

export function FinancialSummary({ data }: { data: ReportStats }) {
  const revenueByType = data.financial.revenue_by_type || {};
  const chartData = Object.entries(revenueByType).map(([type, info]) => ({
    name: type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    value: info.total,
    count: info.count,
  }));

  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <DollarSign className="w-5 h-5 text-status-success-600" />
        Financial Summary
      </h3>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-lg p-3">
            <p className="text-xs text-status-success-700 dark:text-status-success-400">Total Revenue</p>
            <p className="text-xl font-bold text-status-success-800 dark:text-status-success-300">
              ${data.financial.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg p-3">
            <p className="text-xs text-status-danger-700 dark:text-status-danger-400">Outstanding Balance</p>
            <p className="text-xl font-bold text-status-danger-800 dark:text-status-danger-300">
              ${data.financial.outstanding_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        <div className="bg-earth-50 dark:bg-earth-800 rounded-lg p-3">
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Outstanding Fines</p>
          <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
            {data.financial.outstanding_fines_count.toLocaleString()} accounts
          </p>
        </div>

        {chartData.length > 0 && (
          <div>
            <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Revenue by Type</p>
            <div className="space-y-2">
              {chartData.map((item, idx) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                    />
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{item.name}</span>
                  </div>
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                    ${item.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
