/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BarChart3, Download } from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { AccessibleChartWrapper } from "../charts/AccessibleChartWrapper"
import { useRoomReservationColors } from "../../hooks/useChartColors"
import { useTranslation } from "@/i18n"
import type { RoomUtilizationResponse } from "./types"

interface RoomUtilizationChartProps {
  utilization: RoomUtilizationResponse
  onExport: () => void
}

export function RoomUtilizationChart({
  utilization,
  onExport,
}: RoomUtilizationChartProps): React.ReactElement {
  const { t } = useTranslation()
  const COLORS = useRoomReservationColors()

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
          Room Utilization
        </h2>
        <button
          onClick={onExport}
          className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose flex items-center gap-1"
          aria-label={t("aria.roomReservationReports.exportUtilizationReport")}
        >
          <Download aria-hidden="true" className="w-4 h-4" />
          Export
        </button>
      </div>
      <AccessibleChartWrapper
        title="Room Utilization"
        description="Utilization rate by room showing percentage of available time booked"
        data={utilization.by_room}
        columns={[
          { key: "room_name", label: "Room" },
          { key: "room_type", label: "Type" },
          { key: "total_reservations", label: "Total Reservations" },
          {
            key: "utilization_rate",
            label: "Utilization Rate",
            format: (v) => `${Number(v).toFixed(1)}%`,
          },
        ]}
        emptyMessage="No room utilization data available"
        emptyHeight={400}
      >
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={utilization.by_room}>
              <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
              <XAxis
                dataKey="room_name"
                stroke={COLORS.axis}
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={100}
              />
              <YAxis stroke={COLORS.axis} fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: COLORS.tooltipBg,
                  border: `1px solid ${COLORS.tooltipBorder}`,
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Bar dataKey="utilization_rate" name="Utilization Rate (%)" fill={COLORS.primary} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </AccessibleChartWrapper>
    </div>
  )
}
