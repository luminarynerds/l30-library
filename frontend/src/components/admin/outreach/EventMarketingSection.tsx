/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CalendarDays } from 'lucide-react'
import { EventMarketingDashboard } from '@/components/EventMarketingDashboard'
import { SectionShell } from '../ai-settings/SectionShell'

interface EventMarketingSectionProps {
  onBack: () => void
}

export function EventMarketingSection({ onBack }: EventMarketingSectionProps) {
  return (
    <SectionShell
      title="Event Marketing"
      description="Promote upcoming events across channels. Track which promotions drive attendance."
      tabs={[{ id: 'dashboard', label: 'Event Campaigns', icon: CalendarDays }]}
      defaultTab="dashboard"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {() => <EventMarketingDashboard />}
    </SectionShell>
  )
}
