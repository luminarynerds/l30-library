/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Building2, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { LibraryConfigDashboard, type SectionId } from '../components/admin/library-config/LibraryConfigDashboard'

const SiteSettingsSection = lazy(() =>
  import('../components/admin/library-config/SiteSettingsSection').then(m => ({ default: m.SiteSettingsSection }))
)
const OrganizationFeaturesSection = lazy(() =>
  import('../components/admin/library-config/OrganizationFeaturesSection').then(m => ({ default: m.OrganizationFeaturesSection }))
)
const CommunityResourcesSection = lazy(() =>
  import('../components/admin/library-config/CommunityResourcesSection').then(m => ({ default: m.CommunityResourcesSection }))
)
const CirculationPolicySection = lazy(() =>
  import('../components/admin/library-config/CirculationPolicySection').then(m => ({ default: m.CirculationPolicySection }))
)

const VALID_SECTIONS: SectionId[] = ['site-settings', 'features', 'community-resources', 'circulation-policies']

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
  </div>
)

export default function AdminLibraryConfigDashboardPage() {
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
    'site-settings': <SiteSettingsSection onBack={handleBack} />,
    features: <OrganizationFeaturesSection onBack={handleBack} />,
    'community-resources': <CommunityResourcesSection onBack={handleBack} />,
    'circulation-policies': <CirculationPolicySection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="Library Configuration"
      {...(!activeSection && { subtitle: 'Site settings, feature toggles, and community resources' })}
      {...(!activeSection && { icon: <Building2 className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <LibraryConfigDashboard onSelectSection={handleSelectSection as (id: string) => void} />
      )}
    </AdminShell>
  )
}
