/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Sliders, BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  getRecommendationSettings,
  updateRecommendationSettings,
  getSimilarityAlgorithms,
  updateSimilarityAlgorithm,
  getRecommendationStats,
  clearRecommendationCache,
  rebuildRecommendationIndex,
  type RecommendationSettings,
  type SimilarityAlgorithm,
} from '@/api/recommendations-api'
import { SettingsTab } from '@/components/recommendations/SettingsTab'
import { AlgorithmsTab } from '@/components/recommendations/AlgorithmsTab'
import { StatisticsTab } from '@/components/recommendations/StatisticsTab'
import { DEFAULT_SETTINGS, DEFAULT_ALGORITHMS, DEFAULT_STATS } from '@/components/recommendations/recommendations-data'
import { SectionShell } from './SectionShell'

interface RecommendationsSectionProps {
  onBack: () => void
}

const TABS = [
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'algorithms', label: 'Algorithms', icon: Sliders },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
]

export function RecommendationsSection({ onBack }: RecommendationsSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [localSettings, setLocalSettings] = useState<RecommendationSettings>(DEFAULT_SETTINGS)
  const [localAlgorithms, setLocalAlgorithms] = useState<SimilarityAlgorithm[]>(DEFAULT_ALGORITHMS)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [expandedSections, setExpandedSections] = useState<string[]>(['general', 'weights'])
  const [visitedTabs, setVisitedTabs] = useState<Set<string>>(new Set(['settings']))
  const currentTabRef = useRef('settings')

  // Fetch settings
  const { data: settings, isLoading: settingsLoading, error: settingsError } = useQuery({
    queryKey: ['recommendation-settings'],
    queryFn: getRecommendationSettings,
    enabled: visitedTabs.has('settings'),
    retry: false,
  })

  // Fetch algorithms
  const { data: algorithms, isLoading: algorithmsLoading, error: algorithmsError } = useQuery({
    queryKey: ['similarity-algorithms'],
    queryFn: getSimilarityAlgorithms,
    enabled: visitedTabs.has('algorithms'),
    retry: false,
  })

  // Fetch statistics
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['recommendation-stats'],
    queryFn: () => getRecommendationStats(30),
    enabled: visitedTabs.has('statistics'),
    retry: false,
  })

  // Update local state when data is fetched
  useEffect(() => {
    if (settings) {
      setLocalSettings(settings)
    }
  }, [settings])

  useEffect(() => {
    if (algorithms) {
      setLocalAlgorithms(algorithms)
    }
  }, [algorithms])

  // Mutations
  const updateSettingsMutation = useMutation({
    mutationFn: updateRecommendationSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendation-settings'] })
      setHasUnsavedChanges(false)
      toast.success(t('toast.adminRecommendations.settingsSavedSuccessfully'))
    },
    onError: () => {
      toast.error(t('admin.adminRecommendations.failedToSaveSettings'))
    },
  })

  const updateAlgorithmMutation = useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: Partial<SimilarityAlgorithm> }) =>
      updateSimilarityAlgorithm(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['similarity-algorithms'] })
      toast.success(t('toast.adminRecommendations.algorithmUpdated'))
    },
    onError: () => {
      toast.error(t('admin.adminRecommendations.failedToUpdateAlgorithm'))
    },
  })

  const clearCacheMutation = useMutation({
    mutationFn: clearRecommendationCache,
    onSuccess: (data) => {
      toast.success(data.message || t('toast.adminRecommendations.cacheClearedSuccessfully'))
    },
    onError: () => {
      toast.error(t('admin.adminRecommendations.failedToClearCache'))
    },
  })

  const rebuildIndexMutation = useMutation({
    mutationFn: rebuildRecommendationIndex,
    onSuccess: (data) => {
      toast.success(data.message || t('toast.adminRecommendations.indexRebuildStarted'))
    },
    onError: () => {
      toast.error(t('admin.adminRecommendations.failedToStartIndexRebuild'))
    },
  })

  const handleSettingChange = <K extends keyof RecommendationSettings>(
    key: K,
    value: RecommendationSettings[K]
  ) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }))
    setHasUnsavedChanges(true)
  }

  const handleAlgorithmChange = (algorithmId: string, updates: Partial<SimilarityAlgorithm>) => {
    setLocalAlgorithms((prev) =>
      prev.map((alg) => (alg.id === algorithmId ? { ...alg, ...updates } : alg))
    )
  }

  const saveAlgorithmChanges = (algorithm: SimilarityAlgorithm) => {
    updateAlgorithmMutation.mutate({ id: algorithm.id, updates: algorithm })
  }

  const toggleSection = (section: string) => {
    setExpandedSections((prev) =>
      prev.includes(section) ? prev.filter((s) => s !== section) : [...prev, section]
    )
  }

  return (
    <SectionShell
      title="Recommendations"
      description="Suggests similar books based on catalog data. Runs locally using your existing embeddings."
      tabs={TABS}
      onBack={onBack}
    >
      {(activeTab) => {
        // Track visited tabs for lazy query enabling
        if (activeTab !== currentTabRef.current) {
          currentTabRef.current = activeTab
          if (!visitedTabs.has(activeTab)) {
            // Schedule state update to avoid setState during render
            queueMicrotask(() => setVisitedTabs((prev) => new Set(prev).add(activeTab)))
          }
        }

        if (activeTab === 'settings') {
          return (
            <SettingsTab
              settings={localSettings}
              isLoading={settingsLoading}
              hasError={!!settingsError}
              hasUnsavedChanges={hasUnsavedChanges}
              expandedSections={expandedSections}
              onToggleSection={toggleSection}
              onSettingChange={handleSettingChange}
              onSave={() => updateSettingsMutation.mutate(localSettings)}
              onClearCache={() => clearCacheMutation.mutate()}
              onRebuildIndex={() => rebuildIndexMutation.mutate()}
              isSaving={updateSettingsMutation.isPending}
              isClearingCache={clearCacheMutation.isPending}
              isRebuildingIndex={rebuildIndexMutation.isPending}
            />
          )
        }

        if (activeTab === 'algorithms') {
          return (
            <AlgorithmsTab
              algorithms={localAlgorithms}
              isLoading={algorithmsLoading}
              hasError={!!algorithmsError}
              onAlgorithmChange={handleAlgorithmChange}
              onSave={saveAlgorithmChanges}
              isSaving={updateAlgorithmMutation.isPending}
            />
          )
        }

        if (activeTab === 'statistics') {
          return (
            <StatisticsTab
              stats={stats || DEFAULT_STATS}
              isLoading={statsLoading}
              hasError={!!statsError}
            />
          )
        }

        return null
      }}
    </SectionShell>
  )
}
