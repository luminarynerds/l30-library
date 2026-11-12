/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getKidsDashboard, KidsDashboardData } from '@/api/staff-api/kids-dashboard'
import DutyHero from '../panels/DutyHero'
import KidsNextProgram from '../panels/KidsNextProgram'
import KidsReadingStats from '../panels/KidsReadingStats'
import KidsUpcomingPrograms from '../panels/KidsUpcomingPrograms'
import KidsQuickActions from '../panels/KidsQuickActions'

export default function KidsDashboard() {
  const { token } = useAuth()
  const [data, setData] = useState<KidsDashboardData | null>(null)

  useEffect(() => {
    if (!token) return
    getKidsDashboard(token).then(setData).catch(() => {})
  }, [token])

  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="motion-safe:animate-dashboard-enter-0">
        {/* eslint-disable-next-line jsx-a11y/aria-role -- role here is a custom component prop, not a DOM ARIA role */}
        <DutyHero role="kids_services" />
      </div>
      <div className="motion-safe:animate-dashboard-enter-1">
        <KidsNextProgram program={data.next_program} />
      </div>
      <div className="motion-safe:animate-dashboard-enter-2">
        <KidsReadingStats stats={data.reading_stats} />
      </div>
      <div className="motion-safe:animate-dashboard-enter-3">
        <KidsQuickActions />
      </div>
      <div className="motion-safe:animate-dashboard-enter-4">
        <KidsUpcomingPrograms programs={data.upcoming_programs} />
      </div>
    </div>
  )
}
