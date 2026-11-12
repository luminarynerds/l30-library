/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getMarketingDashboard, MarketingDashboardData } from '@/api/staff-api/marketing-dashboard'
import DutyHero from '../panels/DutyHero'
import MarketingInFlight from '../panels/MarketingInFlight'
import MarketingMetrics from '../panels/MarketingMetrics'
import MarketingQuickActions from '../panels/MarketingQuickActions'
import MarketingNeedsPromo from '../panels/MarketingNeedsPromo'

export default function MarketingDashboard() {
  const { token } = useAuth()
  const [data, setData] = useState<MarketingDashboardData | null>(null)

  useEffect(() => {
    if (!token) return
    getMarketingDashboard(token).then(setData).catch(() => {})
  }, [token])

  if (!data) return null

  return (
    <div className="space-y-6">
      <div className="motion-safe:animate-dashboard-enter-0">
        {/* eslint-disable-next-line jsx-a11y/aria-role -- role here is a custom component prop, not a DOM ARIA role */}
        <DutyHero role="marketing" />
      </div>
      <div className="motion-safe:animate-dashboard-enter-1">
        <MarketingQuickActions />
      </div>
      <div className="motion-safe:animate-dashboard-enter-2">
        <MarketingInFlight data={data.in_flight} />
      </div>
      <div className="motion-safe:animate-dashboard-enter-3">
        <MarketingMetrics data={data.last_30_days} />
      </div>
      <div className="motion-safe:animate-dashboard-enter-4">
        <MarketingNeedsPromo programs={data.needs_promo} />
      </div>
    </div>
  )
}
