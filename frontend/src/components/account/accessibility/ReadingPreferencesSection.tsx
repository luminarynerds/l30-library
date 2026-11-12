/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Eye, Shield } from 'lucide-react'
import { usePersistedState } from '@/hooks/usePersistedState'
import { CollapsibleSection, SegmentedControl, SettingToggle } from './controls'

const FORMAT_OPTIONS = ['Book', 'Audiobook', 'DVD', 'Game', 'Ebook'] as const
const VIEW_MODES = ['grid', 'list'] as const
const FORMATS_KEY = 'lsc-reading-preferred-formats'
const VIEW_MODE_KEY = 'lsc-catalog-view-mode'
const CONTENT_NOTES_KEY = 'lsc-show-content-notes'

export function ReadingPreferencesSection() {
  const [preferredFormats, setPreferredFormats] = usePersistedState<string[]>(FORMATS_KEY, [])
  const [defaultView, setDefaultView] = usePersistedState<'grid' | 'list'>(VIEW_MODE_KEY, 'list')
  const [showContentNotes, setShowContentNotes] = usePersistedState<boolean>(CONTENT_NOTES_KEY, true)

  const toggleFormat = (format: string) => {
    setPreferredFormats(prev =>
      prev.includes(format) ? prev.filter(f => f !== format) : [...prev, format]
    )
  }

  return (
    <CollapsibleSection
      title="Reading Preferences"
      description="Preferred formats, catalog view, and content notes"
      icon={<BookOpen className="w-5 h-5" />}
    >
      <div className="p-4 rounded-xl bg-lsc-white dark:bg-lsc-brown">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Preferred Formats</span>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          Select the formats you are most interested in. These can be used to filter your catalog results.
        </p>
        <div className="flex flex-wrap gap-2">
          {FORMAT_OPTIONS.map((format) => (
            <button
              key={format}
              onClick={() => toggleFormat(format)}
              className={`
                px-4 py-2 rounded-xl font-medium transition-colors
                ${preferredFormats.includes(format)
                  ? 'bg-lsc-rose text-white'
                  : 'bg-cream dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream hover:bg-sage/20'
                }
              `}
              aria-pressed={preferredFormats.includes(format)}
            >
              {format}
            </button>
          ))}
        </div>
      </div>

      <SegmentedControl
        label="Default Catalog View"
        description="Choose how catalog items are displayed by default."
        icon={<Eye className="w-4 h-4" />}
        options={VIEW_MODES}
        value={defaultView}
        onChange={setDefaultView}
      />

      <SettingToggle
        label="Show Content & Sensory Notes"
        description="Display content warnings and sensory information on catalog items. This helps you find materials that match your comfort level."
        checked={showContentNotes}
        onChange={setShowContentNotes}
        icon={<Shield className="w-4 h-4" />}
      />
    </CollapsibleSection>
  )
}
