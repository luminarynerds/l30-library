/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Clock, Download, TrendingUp } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { useRoomReservationColors } from "../../hooks/useChartColors"
import { useTranslation } from "@/i18n"
import type { PopularTimesResponse } from "./types"

interface PopularTimesChartsProps {
  popularTimes: PopularTimesResponse
  onExport: () => void
}

export function PopularTimesCharts({
  popularTimes,
  onExport,
}: PopularTimesChartsProps): React.ReactElement {
  const { t } = useTranslation()
  const COLORS = useRoomReservationColors()

  const tooltipStyle = {
    backgroundColor: COLORS.tooltipBg,
    border: `1px solid ${COLORS.tooltipBorder}`,
    borderRadius: "8px",
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Clock className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            Popular Hours
          </h2>
          <button
            onClick={onExport}
            className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
            aria-label={t("roomReservationReports.exportPopularTimesReport")}
          >
            <Download aria-hidden="true" className="w-4 h-4" />
            Export
          </button>
        </div>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={popularTimes.by_hour}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="hour_label" stroke={COLORS.axis} fontSize={10} />
              <YAxis stroke={COLORS.axis} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="bookings" name="Bookings" fill={COLORS.secondary} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Popular Days
        </h2>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={popularTimes.by_day}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis dataKey="day_name" stroke={COLORS.axis} fontSize={12} />
              <YAxis stroke={COLORS.axis} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="bookings" name="Bookings" fill={COLORS.info} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
