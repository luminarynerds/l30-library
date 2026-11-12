/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Focus, Volume2, Zap } from 'lucide-react'
import { useUnifiedAccessibility } from '../../../features/accessibility'
import { CollapsibleSection, SettingToggle } from './controls'

export function SoundFeedbackSection() {
  const { settings, updateSetting } = useUnifiedAccessibility()

  return (
    <CollapsibleSection
      title="Sound & Feedback"
      description="Audio and haptic feedback settings"
      icon={<Volume2 className="w-5 h-5" />}
    >
      <SettingToggle
        label="Whisper Mode"
        description="Use subtle, non-intrusive notifications instead of bold or loud alerts."
        checked={settings.whisperMode}
        onChange={(checked) => updateSetting('whisperMode', checked)}
        icon={<Volume2 className="w-4 h-4" />}
      />

      <SettingToggle
        label="Spacious Layout"
        description="Make buttons and interactive elements bigger with more spacing so they are easier to tap or click."
        checked={settings.contentDensity === 'spacious'}
        onChange={(checked) => updateSetting('contentDensity', checked ? 'spacious' : 'comfortable')}
        icon={<Focus className="w-4 h-4" />}
      />

      <SettingToggle
        label="Voice Control"
        description="Enable voice commands for common actions like searching and navigation."
        checked={settings.voiceControlEnabled}
        onChange={(checked) => updateSetting('voiceControlEnabled', checked)}
        icon={<Zap className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
