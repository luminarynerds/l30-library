/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Check, Clock, Focus, Heart, Keyboard } from 'lucide-react'
import { useUnifiedAccessibility } from '../../../features/accessibility'
import { CollapsibleSection, SettingToggle } from './controls'

export function FocusConcentrationSection() {
  const { settings, updateSetting } = useUnifiedAccessibility()

  return (
    <CollapsibleSection
      title="Focus & Concentration"
      description="Reduce distractions and help you stay on task"
      icon={<Focus className="w-5 h-5" />}
    >
      <SettingToggle
        label="Focus Mode"
        description="Hide extra elements on the page so you can concentrate on what matters. Only the main content will be shown."
        checked={settings.focusMode}
        onChange={(checked) => updateSetting('focusMode', checked)}
        icon={<Focus className="w-4 h-4" />}
      />

      <SettingToggle
        label="Enhanced Focus"
        description="Highlight the active element and dim the background to help you concentrate on one thing at a time."
        checked={settings.enhancedFocus}
        onChange={(checked) => updateSetting('enhancedFocus', checked)}
        icon={<Focus className="w-4 h-4" />}
      />

      <SettingToggle
        label="Break Reminders"
        description="Get a gentle reminder to take a break every 30 minutes. This helps prevent hyperfocus and eye strain."
        checked={settings.breakReminders}
        onChange={(checked) => updateSetting('breakReminders', checked)}
        icon={<Heart className="w-4 h-4" />}
      />

      <SettingToggle
        label="Show Session Timer"
        description="Show a small clock in the corner with your active time, with no break nudges. Turn it off to hide the clock."
        checked={settings.showSessionTime}
        onChange={(checked) => updateSetting('showSessionTime', checked)}
        icon={<Clock className="w-4 h-4" />}
      />

      <SettingToggle
        label="Keyboard Shortcuts"
        description="Single-key shortcuts on the catalog (/ to search, f for filters, q for quiet mode, s for simplified view). Turn off if you use speech input or press keys accidentally."
        checked={settings.keyboardShortcutsEnabled}
        onChange={(checked) => updateSetting('keyboardShortcutsEnabled', checked)}
        icon={<Keyboard className="w-4 h-4" />}
      />

      <SettingToggle
        label="Reduced Cognitive Load"
        description="Simplify layouts and remove decorative elements to make it easier to process information."
        checked={settings.reducedCognitiveLoad}
        onChange={(checked) => updateSetting('reducedCognitiveLoad', checked)}
        icon={<Check className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
