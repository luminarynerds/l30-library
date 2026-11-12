/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Shield, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { ComplianceDashboard, type SectionId } from '../components/admin/compliance/ComplianceDashboard'

const AuditSection = lazy(() =>
  import('../components/admin/compliance/AuditSection').then(m => ({ default: m.AuditSection }))
)
const CIPASection = lazy(() =>
  import('../components/admin/compliance/CIPASection').then(m => ({ default: m.CIPASection }))
)
const StateComplianceSection = lazy(() =>
  import('../components/admin/compliance/StateComplianceSection').then(m => ({ default: m.StateComplianceSection }))
)
const LawEnforcementSection = lazy(() =>
  import('../components/admin/compliance/LawEnforcementSection').then(m => ({ default: m.LawEnforcementSection }))
)
const BanTrackerSection = lazy(() =>
  import('../components/admin/compliance/BanTrackerSection').then(m => ({ default: m.BanTrackerSection }))
)
const PublicRecordsSection = lazy(() =>
  import('../components/admin/compliance/PublicRecordsSection').then(m => ({ default: m.PublicRecordsSection }))
)
const OpsAuditSection = lazy(() =>
  import('../components/admin/compliance/OpsAuditSection').then(m => ({ default: m.OpsAuditSection }))
)

const VALID_SECTIONS: SectionId[] = ['audit', 'cipa', 'state', 'law-enforcement', 'ban-tracker', 'public-records', 'ops-audit']

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
  </div>
)

export default function AdminComplianceDashboardPage() {
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
    audit: <AuditSection onBack={handleBack} />,
    cipa: <CIPASection onBack={handleBack} />,
    state: <StateComplianceSection onBack={handleBack} />,
    'law-enforcement': <LawEnforcementSection onBack={handleBack} />,
    'ban-tracker': <BanTrackerSection onBack={handleBack} />,
    'public-records': <PublicRecordsSection onBack={handleBack} />,
    'ops-audit': <OpsAuditSection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="Compliance Dashboard"
      {...(!activeSection && { subtitle: 'All compliance requirements, deadlines, and action items in one place' })}
      {...(!activeSection && { icon: <Shield className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <ComplianceDashboard onSelectSection={handleSelectSection} />
      )}
    </AdminShell>
  )
}
