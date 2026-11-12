/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Library } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { CHART_COLORS } from "./BoardReportTypes";
import type { ReportStats } from "./BoardReportTypes";
import { AccessibleChartWrapper } from "../charts/AccessibleChartWrapper";

export function CollectionPieChart({ data }: { data: ReportStats }) {
  const rawChartData = [
    { name: "Available", value: data.collection.available_items },
    { name: "Checked Out", value: data.collection.checked_out_items },
    { name: "Other", value: Math.max(0, data.collection.total_items - data.collection.available_items - data.collection.checked_out_items) },
  ].filter(d => d.value > 0);

  const total = rawChartData.reduce((sum, d) => sum + d.value, 0);
  const chartData = rawChartData.map(d => ({
    ...d,
    percentage: total > 0 ? ((d.value / total) * 100).toFixed(1) : "0.0",
  }));

  const columns = [
    { key: "name", label: "Segment" },
    { key: "value", label: "Items" },
    { key: "percentage", label: "Percentage (%)" },
  ];

  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Library className="w-5 h-5 text-category-600" />
        Collection Status
      </h3>
      <AccessibleChartWrapper
        title="Collection Status"
        description="Pie chart showing distribution of collection items by availability status."
        data={chartData}
        columns={columns}
      >
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={5}
              dataKey="value"
              // Percentage labels provide a non-color channel for differentiation (WCAG 1.4.1)
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              label={({ name, percent }: Record<string, any>) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {chartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]!} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ backgroundColor: "var(--color-earth-50, #f9f7f4)", borderColor: "var(--color-earth-200, #e5dfd8)", borderRadius: "0.5rem", color: "var(--color-earth-900, #1a1612)" }} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </AccessibleChartWrapper>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Total Titles: <span className="font-medium text-lsc-dark dark:text-lsc-cream">{data.collection.total_titles.toLocaleString()}</span>
        </div>
        <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Availability: <span className="font-medium text-lsc-dark dark:text-lsc-cream">{data.collection.availability_rate.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
