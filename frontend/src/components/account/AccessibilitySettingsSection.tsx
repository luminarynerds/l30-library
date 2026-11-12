/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Settings Section
 *
 * Provides neurodivergent-friendly customization options with:
 * - Clear, simple language
 * - Visual previews of changes
 * - Preset profiles for quick setup
 * - Grouped settings by need type
 */
import React from 'react'
import { RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useUnifiedAccessibility } from '../../features/accessibility'
import { PRESETS } from '../../lib/neurodivergent-presets'
import type { SettingsPreset } from '../../types/neurodivergent-settings'
import { ComfortCalmSection } from './accessibility/ComfortCalmSection'
import { FocusConcentrationSection } from './accessibility/FocusConcentrationSection'
import { MotionAnimationSection } from './accessibility/MotionAnimationSection'
import { PresetSelector } from './accessibility/PresetSelector'
import { ReadingPreferencesSection } from './accessibility/ReadingPreferencesSection'
import { ReadingVisionSection } from './accessibility/ReadingVisionSection'
import { SoundFeedbackSection } from './accessibility/SoundFeedbackSection'

export const AccessibilitySettingsSection: React.FC = () => {
  const { t } = useTranslation()
  const {
    applyLegacyPreset,
    resetSettings,
    announceToScreenReader,
    getCurrentPreset,
  } = useUnifiedAccessibility()
  const currentPreset = getCurrentPreset()

  const handlePresetSelect = (presetId: SettingsPreset) => {
    if (presetId === 'standard') {
      resetSettings()
      toast.success(t('toast.settingsReset'))
      announceToScreenReader('All settings reset to standard defaults')
      return
    }
    applyLegacyPreset(presetId)
    const presetName = PRESETS.find(p => p.id === presetId)?.name
    toast.success(t('toast.presetApplied', { presetName }))
    announceToScreenReader(`Applied ${presetName} preset`)
  }

  const handleReset = () => {
    resetSettings()
    toast.success(t('components.account.accessibilitySettingsSection.settingsResetToDefaults'))
    announceToScreenReader('All settings reset to defaults')
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          Accessibility Settings
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
          Make this page work better for you. These settings help with reading, focus, and comfort.
          All changes save automatically.
        </p>
      </div>

      <PresetSelector currentPreset={currentPreset} onSelect={handlePresetSelect} />

      <ReadingVisionSection />

      <MotionAnimationSection />

      <FocusConcentrationSection />

      <ComfortCalmSection />

      <SoundFeedbackSection />

      <ReadingPreferencesSection />

      <div className="pt-6 border-t border-sage/20 dark:border-earth-700">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">Reset All Settings</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Go back to the default settings. This cannot be undone.
            </p>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 text-status-danger-700 dark:text-status-danger-400 border-2 border-status-danger-200 dark:border-status-danger-800 rounded-xl hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset to Defaults
          </button>
        </div>
      </div>
    </div>
  )
}
