/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ScrollText, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { CirculationPolicyDashboard, type SectionId } from '../components/admin/circulation-policy/CirculationPolicyDashboard'

const CirculationRulesSection = lazy(() =>
  import('../components/admin/circulation-policy/CirculationRulesSection').then(m => ({ default: m.CirculationRulesSection }))
)
const FinancialSection = lazy(() =>
  import('../components/admin/circulation-policy/FinancialSection').then(m => ({ default: m.FinancialSection }))
)
const PatronSettingsSection = lazy(() =>
  import('../components/admin/circulation-policy/PatronSettingsSection').then(m => ({ default: m.PatronSettingsSection }))
)
const StaffSettingsSection = lazy(() =>
  import('../components/admin/circulation-policy/StaffSettingsSection').then(m => ({ default: m.StaffSettingsSection }))
)
const SystemLimitsSection = lazy(() =>
  import('../components/admin/circulation-policy/SystemLimitsSection').then(m => ({ default: m.SystemLimitsSection }))
)

const VALID_SECTIONS: SectionId[] = ['circulation-rules', 'financial', 'patron-settings', 'staff-settings', 'system-limits']

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
  </div>
)

export default function AdminCirculationPolicyDashboardPage() {
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
    'circulation-rules': <CirculationRulesSection onBack={handleBack} />,
    financial: <FinancialSection onBack={handleBack} />,
    'patron-settings': <PatronSettingsSection onBack={handleBack} />,
    'staff-settings': <StaffSettingsSection onBack={handleBack} />,
    'system-limits': <SystemLimitsSection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="Circulation & Policy"
      {...(!activeSection && { subtitle: 'Borrowing rules, fines, patron and staff policies, limits, and costs' })}
      {...(!activeSection && { icon: <ScrollText className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <CirculationPolicyDashboard onSelectSection={handleSelectSection as (id: string) => void} />
      )}
    </AdminShell>
  )
}
