/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  BarChart3,
  Tag,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { AnalyticsTab } from '@/components/marketing/AnalyticsTab'
import { InterestsTab } from '@/components/marketing/InterestsTab'
import { SectionShell } from '../ai-settings/SectionShell'

interface CampaignsSectionProps {
  onBack: () => void
}

export function CampaignsSection({ onBack }: CampaignsSectionProps) {
  const { token } = useAuth()

  return (
    <SectionShell
      title="Marketing"
      description="Manage the newsletter interest categories patrons can subscribe to, and see how the mail is performing."
      tabs={[
        { id: 'interests', label: 'Interest Categories', icon: Tag },
        { id: 'analytics', label: 'Analytics', icon: BarChart3 },
      ]}
      defaultTab="interests"
      backLabel="Back to Outreach Dashboard"
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {activeTab === 'interests' && token && <InterestsTab token={token} />}
          {activeTab === 'analytics' && token && <AnalyticsTab token={token} />}
        </>
      )}
    </SectionShell>
  )
}
