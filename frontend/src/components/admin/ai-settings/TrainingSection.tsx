/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { BarChart3, ClipboardCheck, Settings } from 'lucide-react'
import { SectionShell } from './SectionShell'
import {
  getTrainingStats, getPipelineStats, getReadiness,
} from '@/api/training-pipeline-api'
import type {
  TrainingStats, PipelineStats, ReadinessResult,
} from '@/api/training-pipeline-api'
import { DashboardTab } from '../../training-pipeline/DashboardTab'
import { ReviewQueueTab } from '../../training-pipeline/ReviewQueueTab'
import { SettingsTab } from '../../training-pipeline/SettingsTab'

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'review', label: 'Review Queue', icon: ClipboardCheck },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function TrainingSection({ onBack }: { onBack: () => void }) {
  const [training, setTraining] = useState<TrainingStats | null>(null)
  const [pipeline, setPipeline] = useState<PipelineStats | null>(null)
  const [readiness, setReadiness] = useState<Record<string, ReadinessResult>>({})
  const [loading, setLoading] = useState(true)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const [t, p] = await Promise.all([getTrainingStats(), getPipelineStats()])
      setTraining(t)
      setPipeline(p)

      const domains = Object.keys(t.by_persona)
      const readinessResults: Record<string, ReadinessResult> = {}
      for (const d of domains) {
        try {
          readinessResults[d] = await getReadiness(d)
        } catch { /* skip */ }
      }
      setReadiness(readinessResults)
    } catch (e) {
      console.error('Failed to load dashboard', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadDashboard() }, [loadDashboard])

  return (
    <SectionShell
      title="Training Pipeline"
      description="Review and approve training data before it is used. You control what the AI learns."
      tabs={tabs}
      onBack={onBack}
    >
      {(activeTab) => (
        <>
          {activeTab === 'dashboard' && (
            <DashboardTab
              training={training}
              pipeline={pipeline}
              readiness={readiness}
              loading={loading}
            />
          )}
          {activeTab === 'review' && (
            <ReviewQueueTab onRefresh={loadDashboard} />
          )}
          {activeTab === 'settings' && <SettingsTab />}
        </>
      )}
    </SectionShell>
  )
}
