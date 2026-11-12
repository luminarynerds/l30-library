/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Check, Focus, Heart, Monitor, Moon, Shield, Sparkles } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { PRESETS } from '../../../lib/neurodivergent-presets'
import type { SettingsPreset } from '../../../types/neurodivergent-settings'

const presetIcons: Record<string, React.ReactNode> = {
  standard: <Monitor className="w-5 h-5" />,
  minimal: <Moon className="w-5 h-5" />,
  focus: <Focus className="w-5 h-5" />,
  exploration: <Sparkles className="w-5 h-5" />,
  calm: <Heart className="w-5 h-5" />,
  'minimal-interaction': <Shield className="w-5 h-5" />,
}

interface PresetSelectorProps {
  currentPreset: string | undefined
  onSelect: (presetId: SettingsPreset) => void
}

export function PresetSelector({ currentPreset, onSelect }: PresetSelectorProps) {
  const { t } = useTranslation()

  return (
    <div className="bg-gradient-to-r from-lsc-rose/5 to-sage/5 dark:from-lsc-rose/10 dark:to-sage/10 rounded-xl p-6">
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        Quick Setup
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Choose a preset that matches how you like to browse. You can adjust individual settings after.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {PRESETS.filter(p => p.id !== 'custom').map((preset) => (
          <button
            key={preset.id}
            onClick={() => onSelect(preset.id)}
            className={`
              flex items-start gap-3 p-4 rounded-xl border-2 transition-all text-left
              ${currentPreset === preset.id
                ? 'border-lsc-rose bg-lsc-rose/10 dark:bg-lsc-rose/20'
                : 'border-sage/20 dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
              }
            `}
            aria-pressed={currentPreset === preset.id}
          >
            <div className={`
              flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
              ${currentPreset === preset.id
                ? 'bg-lsc-rose text-white'
                : 'bg-cream dark:bg-lsc-dark text-lsc-dark/70 dark:text-lsc-cream/70'
              }
            `}>
              {presetIcons[preset.id]}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {preset.name}
                </span>
                {currentPreset === preset.id && (
                  <Check className="w-4 h-4 text-lsc-rose" aria-label={t('aria.account.currentlyActive')} />
                )}
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                {preset.description}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
