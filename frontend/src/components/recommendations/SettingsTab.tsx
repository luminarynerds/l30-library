/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Settings,
  Sliders,
  Database,
  Info,
  AlertCircle,
  Save,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react'
import type { RecommendationSettings, SimilarityStrategy } from '../../api/recommendations-api'
import { getStrategyDisplayName, getStrategyDescription } from '../../api/recommendations-api'

interface WeightSliderProps {
  label: string
  value: number
  onChange: (value: number) => void
}

function WeightSlider({ label, value, onChange }: WeightSliderProps): React.ReactElement {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{label}</label>
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{(value * 100).toFixed(0)}%</span>
      </div>
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full"
      />
    </div>
  )
}

interface SettingsTabProps {
  settings: RecommendationSettings
  isLoading: boolean
  hasError: boolean
  hasUnsavedChanges: boolean
  expandedSections: string[]
  onToggleSection: (section: string) => void
  onSettingChange: <K extends keyof RecommendationSettings>(
    key: K,
    value: RecommendationSettings[K]
  ) => void
  onSave: () => void
  onClearCache: () => void
  onRebuildIndex: () => void
  isSaving: boolean
  isClearingCache: boolean
  isRebuildingIndex: boolean
}

export function SettingsTab({
  settings,
  isLoading,
  hasError,
  hasUnsavedChanges,
  expandedSections,
  onToggleSection,
  onSettingChange,
  onSave,
  onClearCache,
  onRebuildIndex,
  isSaving,
  isClearingCache,
  isRebuildingIndex,
}: SettingsTabProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  const strategies: SimilarityStrategy[] = ['mixed', 'subject', 'author', 'type', 'collaborative', 'content_based']

  return (
    <div className="space-y-6">
      {hasError && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 flex items-start gap-3">
          <Info className="h-5 w-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-status-warning-800 dark:text-status-warning-200 font-medium">Using Default Settings</p>
            <p className="text-status-warning-700 dark:text-status-warning-300 text-sm mt-1">
              The recommendations API endpoint is not available. Showing default configuration values.
              Changes made here will be saved when the API becomes available.
            </p>
          </div>
        </div>
      )}

      {/* General Settings Section */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <button
          onClick={() => onToggleSection('general')}
          className="w-full px-6 py-4 flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-3">
            <Settings className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">General Settings</span>
          </div>
          {expandedSections.includes('general') ? (
            <ChevronUp className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          ) : (
            <ChevronDown className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          )}
        </button>

        {expandedSections.includes('general') && (
          <div className="px-6 pb-6 border-t border-lsc-border dark:border-earth-700 pt-4 space-y-4">
            {/* Enable Recommendations */}
            <div className="flex items-center justify-between">
              <div>
                <label className="font-medium text-lsc-dark dark:text-lsc-cream">
                  Enable Recommendations
                </label>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Show similar items and personalized suggestions throughout the site
                </p>
              </div>
              <button
                onClick={() => onSettingChange('enabled', !settings.enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.enabled ? 'bg-lsc-rose' : 'bg-earth-300 dark:bg-earth-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white dark:bg-earth-800 transition-transform ${
                    settings.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Default Strategy */}
            <div>
              <label className="block font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Default Strategy
              </label>
              <select
                value={settings.default_strategy}
                onChange={(e) => onSettingChange('default_strategy', e.target.value as SimilarityStrategy)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                {strategies.map((strategy) => (
                  <option key={strategy} value={strategy}>
                    {getStrategyDisplayName(strategy)}
                  </option>
                ))}
              </select>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {getStrategyDescription(settings.default_strategy)}
              </p>
            </div>

            {/* Default Count */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Default Count
                </label>
                <input
                  type="number"
                  min={1}
                  max={settings.max_count}
                  value={settings.default_count}
                  onChange={(e) => onSettingChange('default_count', parseInt(e.target.value) || 6)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Maximum Count
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={settings.max_count}
                  onChange={(e) => onSettingChange('max_count', parseInt(e.target.value) || 12)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            {/* Cache TTL */}
            <div>
              <label className="block font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Cache Duration (minutes)
              </label>
              <input
                type="number"
                min={1}
                max={1440}
                value={settings.cache_ttl_minutes}
                onChange={(e) => onSettingChange('cache_ttl_minutes', parseInt(e.target.value) || 60)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                How long to cache recommendation results before recalculating
              </p>
            </div>

            {/* Include Options */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="include-indie"
                  checked={settings.include_indie_books}
                  onChange={(e) => onSettingChange('include_indie_books', e.target.checked)}
                  className="h-4 w-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
                />
                <label htmlFor="include-indie" className="text-lsc-dark dark:text-lsc-cream">
                  Include Indie Author books in recommendations
                </label>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="include-events"
                  checked={settings.include_events}
                  onChange={(e) => onSettingChange('include_events', e.target.checked)}
                  className="h-4 w-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
                />
                <label htmlFor="include-events" className="text-lsc-dark dark:text-lsc-cream">
                  Include related events in recommendations
                </label>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="personalization"
                  checked={settings.personalization_enabled}
                  onChange={(e) => onSettingChange('personalization_enabled', e.target.checked)}
                  className="h-4 w-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
                />
                <label htmlFor="personalization" className="text-lsc-dark dark:text-lsc-cream">
                  Enable personalization based on user history
                </label>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="exclude-mature"
                  checked={settings.exclude_mature_content}
                  onChange={(e) => onSettingChange('exclude_mature_content', e.target.checked)}
                  className="h-4 w-4 text-lsc-rose border-lsc-border dark:border-earth-700 rounded focus:ring-lsc-rose"
                />
                <label htmlFor="exclude-mature" className="text-lsc-dark dark:text-lsc-cream">
                  Exclude mature content by default
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Algorithm Weights Section */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <button
          onClick={() => onToggleSection('weights')}
          className="w-full px-6 py-4 flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-3">
            <Sliders className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Algorithm Weights</span>
          </div>
          {expandedSections.includes('weights') ? (
            <ChevronUp className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          ) : (
            <ChevronDown className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          )}
        </button>

        {expandedSections.includes('weights') && (
          <div className="px-6 pb-6 border-t border-lsc-border dark:border-earth-700 pt-4 space-y-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Adjust how much each factor contributes to similarity scoring. Weights should sum to 1.0.
            </p>

            <WeightSlider
              label="Subject Match"
              value={settings.weight_subject}
              onChange={(v) => onSettingChange('weight_subject', v)}
            />
            <WeightSlider
              label="Author Match"
              value={settings.weight_author}
              onChange={(v) => onSettingChange('weight_author', v)}
            />
            <WeightSlider
              label="Format/Type Match"
              value={settings.weight_type}
              onChange={(v) => onSettingChange('weight_type', v)}
            />
            <WeightSlider
              label="Popularity"
              value={settings.weight_popularity}
              onChange={(v) => onSettingChange('weight_popularity', v)}
            />
            <WeightSlider
              label="Recency"
              value={settings.weight_recency}
              onChange={(v) => onSettingChange('weight_recency', v)}
            />

            <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Weight:</span>
                <span
                  className={`text-sm font-bold ${
                    Math.abs(
                      settings.weight_subject +
                        settings.weight_author +
                        settings.weight_type +
                        settings.weight_popularity +
                        settings.weight_recency -
                        1
                    ) < 0.01
                      ? 'text-status-success-600'
                      : 'text-status-danger-600'
                  }`}
                >
                  {(
                    settings.weight_subject +
                    settings.weight_author +
                    settings.weight_type +
                    settings.weight_popularity +
                    settings.weight_recency
                  ).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Minimum Similarity Score */}
            <div className="pt-4">
              <label className="block font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Minimum Similarity Score: {settings.min_similarity_score.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.min_similarity_score}
                onChange={(e) => onSettingChange('min_similarity_score', parseFloat(e.target.value))}
                className="w-full"
              />
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Items below this threshold won't be shown as recommendations
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Actions Section */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <button
          onClick={() => onToggleSection('actions')}
          className="w-full px-6 py-4 flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">Cache & Index Management</span>
          </div>
          {expandedSections.includes('actions') ? (
            <ChevronUp className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          ) : (
            <ChevronDown className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          )}
        </button>

        {expandedSections.includes('actions') && (
          <div className="px-6 pb-6 border-t border-lsc-border dark:border-earth-700 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-earth-50 dark:bg-earth-700/50 rounded-lg p-4">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Clear Cache</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Remove all cached recommendations. New requests will be recalculated.
                </p>
                <button
                  onClick={onClearCache}
                  disabled={isClearingCache}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2 disabled:opacity-50"
                >
                  {isClearingCache ? (
                    <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                  Clear Cache
                </button>
              </div>

              <div className="bg-earth-50 dark:bg-earth-700/50 rounded-lg p-4">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">Rebuild Index</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  Rebuild the similarity index. This may take several minutes.
                </p>
                <button
                  onClick={onRebuildIndex}
                  disabled={isRebuildingIndex}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2 disabled:opacity-50"
                >
                  {isRebuildingIndex ? (
                    <Loader2 className="h-4 w-4 motion-safe:animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Rebuild Index
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        {hasUnsavedChanges && (
          <span className="flex items-center text-status-warning-600 dark:text-status-warning-400 text-sm">
            <AlertCircle className="h-4 w-4 mr-1" />
            You have unsaved changes
          </span>
        )}
        <button
          onClick={onSave}
          disabled={isSaving || !hasUnsavedChanges}
          className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2 disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
          Save Settings
        </button>
      </div>
    </div>
  )
}
