/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Lightbulb,
  Check, X, Loader,
  Globe,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'

export default function GuidanceTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [suggestions, setSuggestions] = useState<Array<{
    id: number; title: string; description: string;
    rationale?: string; priority: number;
    suggested_database?: string; suggested_record_type?: string;
    suggested_location?: string;
  }>>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    loadSuggestions()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function loadSuggestions() {
    try {
      setLoading(true)
      const { guidanceApi } = await import('@/api/genealogy-research-api')
      const data = await guidanceApi.list(projectId)
      setSuggestions(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadSuggestions'))
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    try {
      setGenerating(true)
      const { guidanceApi } = await import('@/api/genealogy-research-api')
      const newSuggestions = await guidanceApi.generate(projectId)
      toast.success(t('toast.suggestionsTab.generatedLengthNewSuggestions', { length: newSuggestions.length }))
      loadSuggestions()
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToGenerateSuggestions'))
    } finally {
      setGenerating(false)
    }
  }

  async function handleDismiss(id: number) {
    try {
      const { guidanceApi } = await import('@/api/genealogy-research-api')
      await guidanceApi.dismiss(projectId, id)
      setSuggestions(prev => prev.filter(s => s.id !== id))
    } catch {
      toast.error(t('toast.suggestionsTab.failedToDismiss'))
    }
  }

  async function handleComplete(id: number) {
    try {
      const { guidanceApi } = await import('@/api/genealogy-research-api')
      await guidanceApi.complete(projectId, id)
      setSuggestions(prev => prev.filter(s => s.id !== id))
      toast.success(t('toast.suggestionsTab.markedAsCompleted'))
    } catch {
      toast.error(t('toast.suggestionsTab.failedToComplete'))
    }
  }

  const priorityLabels = ['Low', 'Medium', 'High']
  const priorityColors = ['text-lsc-dark/70 dark:text-lsc-cream/70', 'text-status-warning-500', 'text-status-danger-500']

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Research Guidance</h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.aiPoweredSuggestionsForYour')}</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm disabled:opacity-50"
        >
          {generating ? <Loader className="w-4 h-4 motion-safe:animate-spin" /> : <Lightbulb className="w-4 h-4" />}
          {generating ? 'Generating...' : 'Generate Suggestions'}
        </button>
      </div>

      {suggestions.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Lightbulb className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noActiveSuggestionsClickQuot')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {suggestions.map((s) => (
            <div key={s.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <Lightbulb className="w-5 h-5 text-status-warning-500 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{s.title}</h4>
                      <span className={`text-xs font-medium ${priorityColors[s.priority]}`}>
                        {priorityLabels[s.priority]}
                      </span>
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{s.description}</p>
                    {s.rationale && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic">{s.rationale}</p>
                    )}
                    <div className="flex gap-3 mt-3 text-xs">
                      {s.suggested_database && (
                        <span className="px-2 py-0.5 bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light rounded">
                          {s.suggested_database}
                        </span>
                      )}
                      {s.suggested_record_type && (
                        <span className="px-2 py-0.5 bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 rounded">
                          {s.suggested_record_type.replace(/_/g, ' ')}
                        </span>
                      )}
                      {s.suggested_location && (
                        <span className="px-2 py-0.5 bg-category-50 dark:bg-category-900/20 text-category-600 rounded flex items-center gap-1">
                          <Globe className="w-3 h-3" /> {s.suggested_location}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button onClick={() => handleComplete(s.id)}
                    className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:bg-status-success-900/20 rounded" title="Mark completed">
                    <Check className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDismiss(s.id)}
                    className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 rounded" title="Dismiss">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
