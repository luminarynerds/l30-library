/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown } from "lucide-react"
import FrontDeskSearchBar from "../panels/FrontDeskSearchBar"
import FrontDeskPatronPin from "../panels/FrontDeskPatronPin"
import FrontDeskStatePanel from "../panels/FrontDeskState"
import FrontDeskStatusLine from "../panels/FrontDeskStatusLine"
import FrontDeskQuickActions from "../panels/FrontDeskQuickActions"
import FrontDeskToday from "../panels/FrontDeskToday"
import FrontDeskHandoff from "../panels/FrontDeskHandoff"
import FrontDeskOfflineChip from "../panels/FrontDeskOfflineChip"
import LibraryHeartbeat from "../panels/LibraryHeartbeat"
import StaffMessages from "../panels/StaffMessages"
import MyCourses from "../panels/MyCourses"
import MyShiftsTile from "../MyShiftsTile"
import MyHoursPanel from "../panels/MyHoursPanel"
import ClockInOutButton from "../panels/ClockInOutButton"
import { fairSchedulingApi } from "@/api/fair-scheduling-api"
import { getTimesheetToday } from "@/api/domains/staff/staff-presence-api"
import { getCurrentLocale } from '@/i18n'

const LIBRARY_TIMEZONE = "America/New_York"
const HANDOFF_WINDOW_MIN = 30

function useNearShiftEnd(): boolean {
  const { data } = useQuery({
    queryKey: ["fair-scheduling", "me", "shifts"],
    queryFn: () => fairSchedulingApi.getMyShifts({ days_ahead: 1, include_today: true }),
    staleTime: 4 * 60 * 1000,
  })

  const [, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 60_000)
    return () => clearInterval(id)
  }, [])

  const todayShift = useMemo(() => {
    if (!data?.shifts?.length) return null
    const todayStr = new Date().toLocaleDateString("en-CA", { timeZone: LIBRARY_TIMEZONE })
    return data.shifts.find(s => s.shift_date === todayStr) ?? null
  }, [data])

  if (!todayShift) return false
  const nowStr = new Date().toLocaleString(getCurrentLocale(), { timeZone: LIBRARY_TIMEZONE })
  const now = new Date(nowStr)
  const [hh, mm, ss] = todayShift.scheduled_end.split(":").map(Number)
  const end = new Date(now)
  end.setHours(hh ?? 0, mm ?? 0, ss ?? 0, 0)
  const diffMin = (end.getTime() - now.getTime()) / 60000
  return diffMin > 0 && diffMin <= HANDOFF_WINDOW_MIN
}

function CollapsibleSection({ label, defaultOpen = false, children }: { label: string; defaultOpen?: boolean; children: React.ReactNode }) {
  return (
    <details
      className="group rounded-xl bg-lsc-white/50 dark:bg-earth-800/50 border border-lsc-border dark:border-earth-700"
      {...(defaultOpen ? { open: true } : {})}
    >
      <summary className="cursor-pointer list-none flex items-center justify-between px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        <span>{label}</span>
        <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="px-4 pb-4 pt-2">{children}</div>
    </details>
  )
}

export default function FrontDeskDashboard() {
  const isNearShiftEnd = useNearShiftEnd()
  const queryClient = useQueryClient()
  const [hoursRefreshKey, setHoursRefreshKey] = useState(0)
  // Timesheet is the source of truth for clock state; presence rows can go
  // stale across days and contradict the ClockInOutButton below.
  const { data: timesheetToday } = useQuery({
    queryKey: ["staff-timesheet", "today"],
    queryFn: getTimesheetToday,
    staleTime: 60_000,
  })
  const isClockedIn = timesheetToday?.status === "in_progress"
  const shiftOpen = isNearShiftEnd || isClockedIn

  const handlePunch = () => {
    queryClient.invalidateQueries({ queryKey: ["staff-timesheet", "today"] })
    setHoursRefreshKey(k => k + 1)
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:gap-6">
      <div className="motion-safe:animate-dashboard-enter-0">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <FrontDeskSearchBar />
          </div>
          <div className="pt-3 shrink-0">
            <FrontDeskOfflineChip />
          </div>
        </div>
      </div>

      <div className="motion-safe:animate-dashboard-enter-1">
        <FrontDeskStatusLine />
      </div>

      <div className="motion-safe:animate-dashboard-enter-1">
        <LibraryHeartbeat />
      </div>

      <div className="motion-safe:animate-dashboard-enter-1">
        <FrontDeskQuickActions />
      </div>

      <div className="motion-safe:animate-dashboard-enter-2">
        <FrontDeskPatronPin />
      </div>

      <div className="motion-safe:animate-dashboard-enter-2">
        <FrontDeskStatePanel />
      </div>

      <details
        className="group motion-safe:animate-dashboard-enter-3 rounded-xl bg-lsc-white/50 dark:bg-earth-800/50 border border-lsc-border dark:border-earth-700"
        open={shiftOpen}
      >
        <summary className="cursor-pointer list-none flex items-center justify-between px-4 py-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          <span>Shift{isNearShiftEnd ? " -- ending soon" : ""}</span>
          <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>
        <div className="px-4 pb-4 pt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <FrontDeskToday />
          </div>
          <div>
            <FrontDeskHandoff />
          </div>
          <div className="md:col-span-2 lg:col-span-3">
            <ClockInOutButton onPunch={handlePunch} />
          </div>
          <div className="md:col-span-2 lg:col-span-3">
            <MyHoursPanel compact key={hoursRefreshKey} />
          </div>
        </div>
      </details>

      <div className="motion-safe:animate-dashboard-enter-3">
        <CollapsibleSection label="My shifts">
          <MyShiftsTile />
        </CollapsibleSection>
      </div>

      <div className="motion-safe:animate-dashboard-enter-3">
        <CollapsibleSection label="Staff messages">
          <StaffMessages />
        </CollapsibleSection>
      </div>

      <div className="motion-safe:animate-dashboard-enter-3">
        <CollapsibleSection label="My courses">
          <MyCourses />
        </CollapsibleSection>
      </div>
    </div>
  )
}
