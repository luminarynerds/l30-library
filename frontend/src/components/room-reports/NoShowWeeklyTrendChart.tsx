/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TrendingUp } from "lucide-react"
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { useRoomReservationColors } from "../../hooks/useChartColors"
import type { NoShowWeeklyTrend } from "./types"

interface NoShowWeeklyTrendChartProps {
  weeklyTrend: NoShowWeeklyTrend[]
}

export function NoShowWeeklyTrendChart({
  weeklyTrend,
}: NoShowWeeklyTrendChartProps): React.ReactElement {
  const COLORS = useRoomReservationColors()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
        <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        No-Show Trend by Week
      </h2>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={weeklyTrend}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
            <XAxis
              dataKey="week_start"
              stroke={COLORS.axis}
              fontSize={12}
              tickFormatter={(value) => String(value)}
            />
            <YAxis stroke={COLORS.axis} fontSize={12} />
            <Tooltip
              contentStyle={{
                backgroundColor: COLORS.tooltipBg,
                border: `1px solid ${COLORS.tooltipBorder}`,
                borderRadius: "8px",
              }}
              labelFormatter={(value) => `Week of ${new Date(String(value)).toLocaleDateString()}`}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="no_show_rate"
              name="No-Show Rate (%)"
              stroke={COLORS.danger}
              strokeWidth={2}
              dot={{ fill: COLORS.danger, strokeWidth: 2, r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="total_reservations"
              name="Total Reservations"
              stroke={COLORS.info}
              strokeWidth={2}
              dot={{ fill: COLORS.info, strokeWidth: 2, r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
