/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Settings, Loader2 } from 'lucide-react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../components/shells'
import { AIDashboard, type SectionId } from '../components/admin/ai-settings/AIDashboard'

const ToolsSection = lazy(() =>
  import('../components/admin/ai-settings/ToolsSection').then(m => ({ default: m.ToolsSection }))
)
const ModelsServerSection = lazy(() =>
  import('../components/admin/ai-settings/ModelsServerSection').then(m => ({ default: m.ModelsServerSection }))
)
const AgentsSection = lazy(() =>
  import('../components/admin/ai-settings/AgentsSection').then(m => ({ default: m.AgentsSection }))
)
const SearchEmbeddingsSection = lazy(() =>
  import('../components/admin/ai-settings/SearchEmbeddingsSection').then(m => ({ default: m.SearchEmbeddingsSection }))
)
const RecommendationsSection = lazy(() =>
  import('../components/admin/ai-settings/RecommendationsSection').then(m => ({ default: m.RecommendationsSection }))
)
const TrainingSection = lazy(() =>
  import('../components/admin/ai-settings/TrainingSection').then(m => ({ default: m.TrainingSection }))
)

const VALID_SECTIONS: SectionId[] = ['tools', 'agents', 'search', 'recommendations', 'models', 'training']

function parseSectionFromHash(hash: string): SectionId | null {
  const id = hash.replace('#', '') as SectionId
  return VALID_SECTIONS.includes(id) ? id : null
}

const SectionFallback = () => (
  <div className="flex items-center justify-center h-48">
    <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
  </div>
)

export default function AdminAISettingsPage() {
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

  // Sync hash changes (browser back/forward)
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
    tools: <ToolsSection onBack={handleBack} />,
    agents: <AgentsSection onBack={handleBack} />,
    search: <SearchEmbeddingsSection onBack={handleBack} />,
    recommendations: <RecommendationsSection onBack={handleBack} />,
    models: <ModelsServerSection onBack={handleBack} />,
    training: <TrainingSection onBack={handleBack} />,
  }

  return (
    <AdminShell
      title="AI Settings"
      {...(!activeSection && { subtitle: 'All AI features, models, and controls in one place' })}
      {...(!activeSection && { icon: <Settings className="h-8 w-8" /> })}
      maxWidth="max-w-6xl"
    >
      {activeSection ? (
        <Suspense fallback={<SectionFallback />}>
          {sectionMap[activeSection]}
        </Suspense>
      ) : (
        <AIDashboard onSelectSection={handleSelectSection} />
      )}
    </AdminShell>
  )
}
