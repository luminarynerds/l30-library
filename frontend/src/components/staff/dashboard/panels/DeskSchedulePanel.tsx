/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  getDeskScheduleToday,
  DeskScheduleResponse,
  DeskScheduleStaff,
} from '@/api/domains/staff/staff-presence-api'

function formatTime(raw: string | null): string {
  if (!raw) return ''
  // clock_in_time arrives as a full ISO datetime; schedule fields as HH:MM:SS.
  if (raw.includes('T')) {
    const d = new Date(raw)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
  const [h, m] = raw.split(':').map(Number)
  if (h === undefined || m === undefined || Number.isNaN(h) || Number.isNaN(m)) return ''
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour = h % 12 || 12
  return `${hour}:${String(m).padStart(2, '0')} ${suffix}`
}

function Badge({ variant, children }: { variant: 'available' | 'break' | 'expected' | 'help'; children: React.ReactNode }) {
  const cls =
    variant === 'available'
      ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
      : variant === 'break'
        ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400'
        : variant === 'help'
          ? 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400'
          : 'bg-earth-100 dark:bg-earth-700/30 text-earth-600 dark:text-earth-400'
  return <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${cls}`}>{children}</span>
}

function presenceBadge(staff: DeskScheduleStaff) {
  // Older backends may not surface needs_help; anything else reads Available.
  if (staff.presence_status === 'needs_help') {
    return <Badge variant="help">Needs help</Badge>
  }
  return <Badge variant="available">Available</Badge>
}

function StaffRow({ staff, badge }: { staff: DeskScheduleStaff; badge: React.ReactNode }) {
  const timeRange =
    staff.scheduled_start && staff.scheduled_end
      ? `${formatTime(staff.scheduled_start)} - ${formatTime(staff.scheduled_end)}`
      : null

  return (
    <div className="flex items-center gap-2 py-1">
      <span className="text-sm text-lsc-dark dark:text-lsc-cream">{staff.staff_name}</span>
      {timeRange && (
        <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{timeRange}</span>
      )}
      {badge}
    </div>
  )
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wider text-lsc-dark/40 dark:text-lsc-cream/40 mb-2 mt-4">
      {children}
    </p>
  )
}

export default function DeskSchedulePanel() {
  const [data, setData] = useState<DeskScheduleResponse | null>(null)

  useEffect(() => {
    getDeskScheduleToday().then(setData).catch(() => {})
  }, [])

  if (!data) return null

  const hasAny =
    data.on_duty.length > 0 ||
    data.on_break.length > 0 ||
    data.scheduled_not_present.length > 0 ||
    data.present_unscheduled.length > 0

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        Who&apos;s on desk today
      </p>
      {data.coverage_note && (
        <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">{data.coverage_note}</p>
      )}

      {!hasAny && (
        <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-3">No staff scheduled today</p>
      )}

      {data.on_duty.length > 0 && (
        <>
          <SectionHeader>On duty</SectionHeader>
          {data.on_duty.map(s => (
            <StaffRow key={s.staff_id} staff={s} badge={presenceBadge(s)} />
          ))}
        </>
      )}

      {data.on_break.length > 0 && (
        <>
          <SectionHeader>On break</SectionHeader>
          {data.on_break.map(s => (
            <StaffRow
              key={s.staff_id}
              staff={s}
              badge={
                <>
                  <Badge variant="break">On break</Badge>
                  {s.clock_in_time && (
                    <span className="text-[11px] text-lsc-dark/50 dark:text-lsc-cream/50">
                      (since {formatTime(s.clock_in_time)})
                    </span>
                  )}
                </>
              }
            />
          ))}
        </>
      )}

      {data.scheduled_not_present.length > 0 && (
        <>
          <SectionHeader>Not yet in</SectionHeader>
          {data.scheduled_not_present.map(s => (
            <StaffRow key={s.staff_id} staff={s} badge={<Badge variant="expected">Expected</Badge>} />
          ))}
        </>
      )}

      {data.present_unscheduled.length > 0 && (
        <>
          <SectionHeader>Unscheduled</SectionHeader>
          {data.present_unscheduled.map(s => (
            <StaffRow key={s.staff_id} staff={s} badge={presenceBadge(s)} />
          ))}
        </>
      )}
    </div>
  )
}
