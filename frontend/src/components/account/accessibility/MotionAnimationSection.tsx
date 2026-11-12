/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { VolumeX, Zap, ZapOff } from 'lucide-react'
import { useUnifiedAccessibility } from '../../../features/accessibility'
import { CollapsibleSection, SettingToggle } from './controls'

export function MotionAnimationSection() {
  const { settings, updateSetting } = useUnifiedAccessibility()

  return (
    <CollapsibleSection
      title="Motion & Animation"
      description="Control movement and animations on the page"
      icon={settings.reduceMotion ? <ZapOff className="w-5 h-5" /> : <Zap className="w-5 h-5" />}
    >
      <SettingToggle
        label="Reduce Motion"
        description="Turn off or slow down animations and transitions. This helps if motion makes you feel uncomfortable or distracted."
        checked={settings.reduceMotion}
        onChange={(checked) => updateSetting('reduceMotion', checked)}
        icon={<ZapOff className="w-4 h-4" />}
      />

      <SettingToggle
        label="Quiet Mode"
        description="Reduce visual noise by collapsing carousels, hiding animations, and using muted colors."
        checked={settings.quietMode}
        onChange={(checked) => updateSetting('quietMode', checked)}
        icon={<VolumeX className="w-4 h-4" />}
      />

      <SettingToggle
        label="Quiet Mode Lite"
        description="A lighter version of quiet mode that keeps functional animations but reduces visual intensity."
        checked={settings.quietModeLite}
        onChange={(checked) => updateSetting('quietModeLite', checked)}
        icon={<Zap className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
