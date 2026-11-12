/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Megaphone, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { OutreachDashboard, type SectionId } from '../components/admin/outreach/OutreachDashboard'

const EmailNotificationsSection = lazy(() =>
  import('../components/admin/outreach/EmailNotificationsSection').then(m => ({ default: m.EmailNotificationsSection }))
)
const SMSSection = lazy(() =>
  import('../components/admin/outreach/SMSSection').then(m => ({ default: m.SMSSection }))
)
const EmailMarketingSection = lazy(() =>
  import('../components/admin/outreach/EmailMarketingSection').then(m => ({ default: m.EmailMarketingSection }))
)
const MarketingHubSection = lazy(() =>
  import('../components/admin/outreach/MarketingHubSection').then(m => ({ default: m.MarketingHubSection }))
)
const CampaignsSection = lazy(() =>
  import('../components/admin/outreach/CampaignsSection').then(m => ({ default: m.CampaignsSection }))
)
const EventMarketingSection = lazy(() =>
  import('../components/admin/outreach/EventMarketingSection').then(m => ({ default: m.EventMarketingSection }))
)

const VALID_SECTIONS: SectionId[] = [
  'email-notifications', 'sms', 'email-marketing',
  'marketing-hub', 'campaigns', 'event-marketing',
]

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
  </div>
)

export default function AdminOutreachDashboardPage() {
  const { isAuthorized } = useRequireRole('adminOrDirector')
  const location = useLocation()
  const navigate = useNavigate()
  const [activeSection, setActiveSection] = useState<SectionId | null>(
    parseSectionFromHash(location.hash)
  )

  useEffect(() => {
    if (!isAuthorized) {
      navigate('/')
    }
  }, [isAuthorized, navigate])

  useEffect(() => {
    setActiveSection(parseSectionFromHash(location.hash))
  }, [location.hash])

  const handleSelectSection = useCallback((id: SectionId) => {
    setActiveSection(id)
    navigate(`#${id}`, { replace: false })
  }, [navigate])

  const handleBack = useCallback(() => {
    setActiveSection(null)
    navigate('#', { replace: false })
  }, [navigate])

  const sectionMap: Record<SectionId, React.ReactNode> = {
    'email-notifications': <EmailNotificationsSection onBack={handleBack} />,
    sms: <SMSSection onBack={handleBack} />,
    'email-marketing': <EmailMarketingSection onBack={handleBack} />,
    'marketing-hub': <MarketingHubSection onBack={handleBack} />,
    campaigns: <CampaignsSection onBack={handleBack} />,
    'event-marketing': <EventMarketingSection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="Outreach & Communications"
      {...(!activeSection && { subtitle: 'All patron messaging, campaigns, and promotion tools in one place' })}
      {...(!activeSection && { icon: <Megaphone className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <OutreachDashboard onSelectSection={handleSelectSection} />
      )}
    </AdminShell>
  )
}
