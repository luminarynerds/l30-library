/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Eye, Sun, Type, Zap } from 'lucide-react'
import { useUnifiedAccessibility } from '../../../features/accessibility'
import { CollapsibleSection, SegmentedControl, SettingToggle } from './controls'

const FONT_SIZES = ['normal', 'large', 'xlarge'] as const
const LINE_SPACINGS = ['normal', 'relaxed', 'loose'] as const
const LETTER_SPACINGS = ['normal', 'wide', 'wider'] as const

export function ReadingVisionSection() {
  const { settings, updateSetting } = useUnifiedAccessibility()

  return (
    <CollapsibleSection
      title="Reading & Vision"
      description="Text size, fonts, and visual preferences"
      icon={<Eye className="w-5 h-5" />}
      defaultOpen={true}
    >
      <SettingToggle
        label="Dyslexia-Friendly Font"
        description="Switches to Atkinson Hyperlegible, a typeface designed for character differentiation (b/d, 1/l/I, 0/O) and recommended by the British Dyslexia Association."
        checked={settings.dyslexiaFont}
        onChange={(checked) => updateSetting('dyslexiaFont', checked)}
        icon={<Type className="w-4 h-4" />}
      />

      <SettingToggle
        label="High Contrast"
        description="Increase the contrast between text and background colors. This makes text easier to read, especially in bright environments."
        checked={settings.highContrast}
        onChange={(checked) => updateSetting('highContrast', checked)}
        icon={<Sun className="w-4 h-4" />}
      />

      <SegmentedControl
        label="Text Size"
        description="Choose a text size that is comfortable for you to read."
        icon={<Type className="w-4 h-4" />}
        options={FONT_SIZES}
        value={settings.fontSize}
        onChange={(size) => updateSetting('fontSize', size)}
        renderLabel={(size) => (
          <span className={size === 'normal' ? '' : size === 'large' ? 'text-lg' : 'text-xl'}>
            {size === 'normal' ? 'Normal' : size === 'large' ? 'Large' : 'Extra Large'}
          </span>
        )}
      />

      <SegmentedControl
        label="Line Spacing"
        description="More space between lines can make reading easier and reduce visual crowding."
        icon={<Type className="w-4 h-4" />}
        options={LINE_SPACINGS}
        value={settings.lineSpacing}
        onChange={(spacing) => updateSetting('lineSpacing', spacing)}
      />

      <SegmentedControl
        label="Letter Spacing"
        description="Add extra space between letters to make words easier to distinguish."
        icon={<Type className="w-4 h-4" />}
        options={LETTER_SPACINGS}
        value={settings.letterSpacing}
        onChange={(spacing) => updateSetting('letterSpacing', spacing)}
      />

      <SettingToggle
        label="Reading Ruler"
        description="Highlight the line you are reading to help you keep your place. The ruler follows your cursor or focus."
        checked={settings.lineFocusGuide}
        onChange={(checked) => updateSetting('lineFocusGuide', checked)}
        icon={<Eye className="w-4 h-4" />}
      />

      <SettingToggle
        label="Bionic Reading"
        description="Bold the first few letters of each word to help guide your eyes through text more quickly."
        checked={settings.bionicReading}
        onChange={(checked) => updateSetting('bionicReading', checked)}
        icon={<Zap className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
