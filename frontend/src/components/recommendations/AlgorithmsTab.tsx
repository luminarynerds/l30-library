/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Sliders, Info, Save, Loader2 } from 'lucide-react'
import type { SimilarityAlgorithm } from '../../api/recommendations-api'

interface AlgorithmsTabProps {
  algorithms: SimilarityAlgorithm[]
  isLoading: boolean
  hasError: boolean
  onAlgorithmChange: (id: string, updates: Partial<SimilarityAlgorithm>) => void
  onSave: (algorithm: SimilarityAlgorithm) => void
  isSaving: boolean
}

export function AlgorithmsTab({
  algorithms,
  isLoading,
  hasError,
  onAlgorithmChange,
  onSave,
  isSaving,
}: AlgorithmsTabProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {hasError && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 flex items-start gap-3">
          <Info className="h-5 w-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-status-warning-800 dark:text-status-warning-200 font-medium">Using Default Algorithms</p>
            <p className="text-status-warning-700 dark:text-status-warning-300 text-sm mt-1">
              The algorithms API endpoint is not available. Showing default configuration.
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {algorithms.map((algorithm) => (
          <div
            key={algorithm.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`p-2 rounded-lg ${
                    algorithm.enabled
                      ? 'bg-status-success-100 dark:bg-status-success-900/30'
                      : 'bg-earth-100 dark:bg-earth-700'
                  }`}
                >
                  <Sliders
                    className={`h-5 w-5 ${
                      algorithm.enabled
                        ? 'text-status-success-600 dark:text-status-success-400'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70'
                    }`}
                  />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{algorithm.name}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{algorithm.description}</p>
                </div>
              </div>
              <button
                onClick={() => onAlgorithmChange(algorithm.id, { enabled: !algorithm.enabled })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  algorithm.enabled ? 'bg-status-success-500' : 'bg-earth-300 dark:bg-earth-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${
                    algorithm.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {algorithm.enabled && (
              <div className="space-y-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                      Weight
                    </label>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {(algorithm.weight * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={algorithm.weight}
                    onChange={(e) =>
                      onAlgorithmChange(algorithm.id, { weight: parseFloat(e.target.value) })
                    }
                    className="w-full"
                  />
                </div>

                <button
                  onClick={() => onSave(algorithm)}
                  disabled={isSaving}
                  className="w-full px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  Save Changes
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
