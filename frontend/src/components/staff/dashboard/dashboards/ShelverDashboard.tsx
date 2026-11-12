/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getShelverDashboard, ShelverDashboardData } from '@/api/staff-api/shelver-dashboard'
import DutyHero from '../panels/DutyHero'
import ShelverShiftInfo from '../panels/ShelverShiftInfo'
import ShelverTaskList from '../panels/ShelverTaskList'
import ShelverActions from '../panels/ShelverActions'
import MyHoursPanel from '../panels/MyHoursPanel'

export default function ShelverDashboard() {
  const { token, user } = useAuth()
  const [data, setData] = useState<ShelverDashboardData | null>(null)

  useEffect(() => {
    if (!token) return
    getShelverDashboard(token).then(setData).catch(() => {})
  }, [token])

  const firstName = user?.first_name ?? 'there'

  return (
    <div className="space-y-4">
      <div className="motion-safe:animate-dashboard-enter-0">
        {/* eslint-disable-next-line jsx-a11y/aria-role -- role here is a custom component prop, not a DOM ARIA role */}
        <DutyHero role="page_shelver" />
      </div>
      <div className="motion-safe:animate-dashboard-enter-1">
        <ShelverShiftInfo firstName={firstName} shift={data?.shift ?? null} />
      </div>
      <div className="motion-safe:animate-dashboard-enter-2">
        {data && <ShelverTaskList tasks={data.tasks} />}
      </div>
      <div className="motion-safe:animate-dashboard-enter-3">
        <ShelverActions />
      </div>
      <div className="motion-safe:animate-dashboard-enter-4">
        <MyHoursPanel />
      </div>
    </div>
  )
}
