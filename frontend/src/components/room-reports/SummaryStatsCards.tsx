/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Calendar, CheckCircle, Clock, XCircle } from "lucide-react"
import type { RoomUtilizationSummary } from "./types"

interface SummaryStatsCardsProps {
  summary: RoomUtilizationSummary
}

export function SummaryStatsCards({ summary }: SummaryStatsCardsProps): React.ReactElement {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Total Reservations"
        value={summary.total_reservations}
        icon={<Calendar aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />}
        iconBg="bg-lsc-cream dark:bg-lsc-brown/30"
        valueClassName="text-lsc-dark dark:text-lsc-cream"
      />
      <StatCard
        label="Confirmed"
        value={summary.confirmed_reservations}
        icon={<CheckCircle aria-hidden="true" className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />}
        iconBg="bg-status-success-100 dark:bg-status-success-900/30"
        valueClassName="text-status-success-600 dark:text-status-success-400"
      />
      <StatCard
        label="No-Shows"
        value={summary.no_show_reservations}
        icon={<XCircle aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />}
        iconBg="bg-status-danger-100 dark:bg-status-danger-900/30"
        valueClassName="text-status-danger-600 dark:text-status-danger-400"
      />
      <StatCard
        label="Hours Booked"
        value={summary.total_hours_booked.toFixed(1)}
        icon={<Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />}
        iconBg="bg-earth-100 dark:bg-earth-800/30"
        valueClassName="text-lsc-rose dark:text-lsc-rose-light"
      />
    </div>
  )
}

interface StatCardProps {
  label: string
  value: number | string
  icon: React.ReactNode
  iconBg: string
  valueClassName: string
}

function StatCard({ label, value, icon, iconBg, valueClassName }: StatCardProps): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${iconBg} rounded-xl flex items-center justify-center`}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
          <p className={`text-2xl font-bold ${valueClassName}`}>{value}</p>
        </div>
      </div>
    </div>
  )
}
