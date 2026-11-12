/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Check, Heart, Moon, RotateCcw, Shield, Type } from 'lucide-react'
import { useUnifiedAccessibility } from '../../../features/accessibility'
import { CollapsibleSection, SettingToggle } from './controls'

export function ComfortCalmSection() {
  const { settings, updateSetting } = useUnifiedAccessibility()

  return (
    <CollapsibleSection
      title="Comfort & Calm"
      description="Settings that reduce stress and anxiety"
      icon={<Heart className="w-5 h-5" />}
    >
      <SettingToggle
        label="Muted Colors"
        description="Use softer, less intense colors throughout the page. Bright colors can be overwhelming or distracting."
        checked={settings.mutedColors}
        onChange={(checked) => updateSetting('mutedColors', checked)}
        icon={<Moon className="w-4 h-4" />}
      />

      <SettingToggle
        label="Plain Language"
        description="Use simpler words and shorter sentences. Technical terms will be explained or replaced with everyday language."
        checked={settings.plainLanguage}
        onChange={(checked) => updateSetting('plainLanguage', checked)}
        icon={<Type className="w-4 h-4" />}
      />

      <SettingToggle
        label="Gentle Reminders"
        description="Use soft, encouraging language for reminders instead of urgent or alarming wording."
        checked={settings.noUrgentLanguage}
        onChange={(checked) => updateSetting('noUrgentLanguage', checked)}
        icon={<Heart className="w-4 h-4" />}
      />

      <SettingToggle
        label="Hide Pressure Messages"
        description='Remove messages like "3 others are viewing this" that can create a sense of urgency or FOMO.'
        checked={settings.noFOMO}
        onChange={(checked) => updateSetting('noFOMO', checked)}
        icon={<Shield className="w-4 h-4" />}
      />

      <SettingToggle
        label="Confirm Actions"
        description="Ask for confirmation before important actions like cancelling holds or changing settings. This prevents accidental changes."
        checked={settings.explicitConfirmations}
        onChange={(checked) => updateSetting('explicitConfirmations', checked)}
        icon={<Check className="w-4 h-4" />}
      />

      <SettingToggle
        label="Undo Available"
        description="Show an undo option after actions so you can easily reverse changes if you change your mind."
        checked={settings.undoEnabled}
        onChange={(checked) => updateSetting('undoEnabled', checked)}
        icon={<RotateCcw className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
