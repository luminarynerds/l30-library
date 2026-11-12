/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { ReportStats } from "./BoardReportTypes";
import { AccessibleChartWrapper } from "../charts/AccessibleChartWrapper";

export function CirculationChart({ data }: { data: ReportStats }) {
  const chartData = [
    { name: "Checkouts", current: data.circulation.total_checkouts, previous: data.comparison?.circulation.total_checkouts || 0 },
    { name: "Completed", current: data.circulation.completed_checkouts, previous: data.comparison?.circulation.completed_checkouts || 0 },
    { name: "Active", current: data.circulation.active_checkouts, previous: data.comparison?.circulation.active_checkouts || 0 },
    { name: "Holds", current: data.holds.new_holds, previous: 0 },
  ];

  const columns = data.comparison
    ? [
        { key: "name", label: "Metric" },
        { key: "current", label: "Current Period" },
        { key: "previous", label: "Previous Period" },
      ]
    : [
        { key: "name", label: "Metric" },
        { key: "current", label: "Current Period" },
      ];

  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        Circulation Metrics
      </h3>
      <AccessibleChartWrapper
        title="Circulation Metrics"
        description="Bar chart comparing current and previous period circulation metrics including checkouts, completed, active, and holds."
        data={chartData}
        columns={columns}
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--color-earth-50, #f9f7f4)",
                borderColor: "var(--color-earth-200, #e5dfd8)",
                borderRadius: "0.5rem",
                color: "var(--color-earth-900, #1a1612)",
              }}
            />
            <Legend />
            {/* Current period — solid fill, no stroke dash */}
            <Bar dataKey="current" name="Current Period" fill="#1F4E79" radius={[4, 4, 0, 0]} />
            {/* Previous period — lighter fill + dashed stroke outline so it's distinguishable without color alone */}
            {data.comparison && (
              <Bar
                dataKey="previous"
                name="Previous Period"
                fill="#E89B44"
                fillOpacity={0.75}
                stroke="#E89B44"
                strokeWidth={2}
                strokeDasharray="6 3"
                radius={[4, 4, 0, 0]}
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </AccessibleChartWrapper>
      <div className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        Avg checkout duration: <span className="font-medium text-lsc-dark dark:text-lsc-cream">{data.circulation.avg_checkout_duration_days.toFixed(1)} days</span>
      </div>
    </div>
  );
}
