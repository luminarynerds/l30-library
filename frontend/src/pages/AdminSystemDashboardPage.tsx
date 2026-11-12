/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Activity, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { SystemDashboard, type SectionId } from '../components/admin/system-monitoring/SystemDashboard'

const SystemHealthSection = lazy(() =>
  import('../components/admin/system-monitoring/SystemHealthSection').then(m => ({ default: m.SystemHealthSection }))
)
const MonitoringSection = lazy(() =>
  import('../components/admin/system-monitoring/MonitoringSection').then(m => ({ default: m.MonitoringSection }))
)
const ApiStatusSection = lazy(() =>
  import('../components/admin/system-monitoring/ApiStatusSection').then(m => ({ default: m.ApiStatusSection }))
)
const CacheMetricsSection = lazy(() =>
  import('../components/admin/system-monitoring/CacheMetricsSection').then(m => ({ default: m.CacheMetricsSection }))
)
const StorageSection = lazy(() =>
  import('../components/admin/system-monitoring/StorageSection').then(m => ({ default: m.StorageSection }))
)
const SecuritySection = lazy(() =>
  import('../components/admin/system-monitoring/SecuritySection').then(m => ({ default: m.SecuritySection }))
)
const SchedulerSection = lazy(() =>
  import('../components/admin/system-monitoring/SchedulerSection').then(m => ({ default: m.SchedulerSection }))
)
const VirusScanSection = lazy(() =>
  import('../components/admin/system-monitoring/VirusScanSection').then(m => ({ default: m.VirusScanSection }))
)

const VALID_SECTIONS: SectionId[] = [
  'system-health', 'monitoring', 'api-status', 'cache',
  'storage', 'security', 'scheduler', 'virus-scan',
]

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div role="status" aria-live="polite" className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
    <span className="sr-only">Loading section…</span>
  </div>
)

export default function AdminSystemDashboardPage() {
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
    'system-health': <SystemHealthSection onBack={handleBack} />,
    monitoring: <MonitoringSection onBack={handleBack} />,
    'api-status': <ApiStatusSection onBack={handleBack} />,
    cache: <CacheMetricsSection onBack={handleBack} />,
    storage: <StorageSection onBack={handleBack} />,
    security: <SecuritySection onBack={handleBack} />,
    scheduler: <SchedulerSection onBack={handleBack} />,
    'virus-scan': <VirusScanSection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="System Monitoring"
      {...(!activeSection && { subtitle: 'System health, performance, cache, security, and background jobs' })}
      {...(!activeSection && { icon: <Activity className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <SystemDashboard onSelectSection={handleSelectSection} />
      )}
    </AdminShell>
  )
}
