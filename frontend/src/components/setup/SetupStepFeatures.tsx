/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import PageContainer from '@/components/layout/PageContainer'

interface SetupConfig {
  library_name: string
  library_short_name: string
  contact_email: string
  phone: string
  address_line1: string
  address_line2: string
  admin_first_name: string
  admin_last_name: string
  admin_email: string
  admin_password: string
  feature_preset: 'barebones' | 'small_library' | 'full'
  feature_overrides: Record<string, boolean>
  primary_color: string
  accent_color: string
  hero_title: string
  hero_subtitle: string
  tagline: string
}

interface Props {
  config: SetupConfig
  onChange: (config: SetupConfig) => void
  onBack: () => void
  onNext: () => void
  embedded?: boolean
}

interface FeatureItem {
  key: string
  label: string
}

interface FeatureGroup {
  label: string
  features: FeatureItem[]
}

const FEATURE_GROUPS: FeatureGroup[] = [
  {
    label: 'Core',
    features: [
      { key: 'events_enabled', label: 'Events' },
      { key: 'meeting_rooms_enabled', label: 'Meeting Rooms' },
      { key: 'printing_enabled', label: 'Printing & Scanning' },
      { key: 'sip2_rfid_enabled', label: 'Self-Checkout (SIP2)' },
    ],
  },
  {
    label: 'Programs',
    features: [
      { key: 'reading_programs_enabled', label: 'Reading Programs' },
      { key: 'reading_programs_booklist_enabled', label: 'Reading Programs: Booklist' },
      { key: 'reading_programs_paper_log_enabled', label: 'Reading Programs: Paper Log' },
      { key: 'book_clubs_enabled', label: 'Book Clubs' },
      { key: 'book_club_history_enabled', label: 'Book Club Discussion Archive' },
      { key: 'storytime_enabled', label: 'Storytime' },
      { key: 'learning_platform_enabled', label: 'Learning Platform' },
      { key: 'for_teachers_enabled', label: 'For Teachers Portal' },
    ],
  },
  {
    label: 'Digital',
    features: [
      { key: 'digital_access_enabled', label: 'Digital Resources' },
      { key: 'free_ebooks_enabled', label: 'Free Ebooks' },
      { key: 'ai_tools_enabled', label: 'AI Tools' },
      { key: 'streaming_enabled', label: 'Streaming' },
    ],
  },
  {
    label: 'Community',
    features: [
      { key: 'makerspace_enabled', label: 'Makerspace' },
      { key: 'genealogy_enabled', label: 'Genealogy' },
      { key: 'legal_services_enabled', label: 'Legal Services' },
      { key: 'volunteers_enabled', label: 'Volunteers' },
      { key: 'home_delivery_enabled', label: 'Home Delivery' },
    ],
  },
  {
    label: 'Staff Tools',
    features: [
      { key: 'staff_scheduling_enabled', label: 'Staff Scheduling' },
      { key: 'training_modules_enabled', label: 'Training' },
      { key: 'collection_management_enabled', label: 'Collection Management' },
      { key: 'board_features_enabled', label: 'Board Features' },
    ],
  },
]

const ALWAYS_ON = [
  'email_notifications_enabled',
  'notifications_enabled',
  'processing_queue_enabled',
  'patron_portal_enabled',
]

const PRESETS: Record<string, string[]> = {
  barebones: [
    'events_enabled',
    ...ALWAYS_ON,
  ],
  small_library: [
    'events_enabled',
    'meeting_rooms_enabled',
    'reading_programs_enabled',
    'book_clubs_enabled',
    'digital_access_enabled',
    'free_ebooks_enabled',
    'makerspace_enabled',
    'genealogy_enabled',
    'legal_services_enabled',
    'volunteers_enabled',
    'learning_platform_enabled',
    'for_teachers_enabled',
    'storytime_enabled',
    'collection_management_enabled',
    'home_delivery_enabled',
    'staff_scheduling_enabled',
    'training_modules_enabled',
    'board_features_enabled',
    'printing_enabled',
    'outreach_enabled',
    'literacy_programs_enabled',
    'compliance_enabled',
    ...ALWAYS_ON,
  ],
  full: [
    ...FEATURE_GROUPS.flatMap((g) => g.features.map((f) => f.key)),
    'outreach_enabled',
    'literacy_programs_enabled',
    'compliance_enabled',
    ...ALWAYS_ON,
  ],
}

function getActiveFeatures(preset: string, overrides: Record<string, boolean>): Record<string, boolean> {
  const base: Record<string, boolean> = {}
  const presetKeys = (PRESETS[preset] ?? PRESETS.small_library) as string[]
  for (const key of presetKeys) base[key] = true
  return { ...base, ...overrides }
}

export default function SetupStepFeatures({ config, onChange, onBack, onNext, embedded }: Props): React.ReactElement {
  const [customizeOpen, setCustomizeOpen] = useState(false)

  const activeFeatures = useMemo(
    () => getActiveFeatures(config.feature_preset, config.feature_overrides),
    [config.feature_preset, config.feature_overrides],
  )

  const isCustom = Object.keys(config.feature_overrides).length > 0

  const selectPreset = useCallback(
    (preset: 'barebones' | 'small_library' | 'full') => {
      onChange({ ...config, feature_preset: preset, feature_overrides: {} })
    },
    [config, onChange],
  )

  const toggleFeature = useCallback(
    (key: string) => {
      const presetKeys = (PRESETS[config.feature_preset] ?? PRESETS.small_library) as string[]
      const presetValue = presetKeys.includes(key)
      const currentValue = config.feature_overrides[key] ?? presetValue

      const newOverrides = { ...config.feature_overrides }
      const newValue = !currentValue

      if (newValue === presetValue) {
        delete newOverrides[key]
      } else {
        newOverrides[key] = newValue
      }

      onChange({ ...config, feature_overrides: newOverrides })
    },
    [config, onChange],
  )

  const isFeatureOn = useCallback(
    (key: string): boolean => {
      return activeFeatures[key] ?? false
    },
    [activeFeatures],
  )

  const presetCards: { id: 'barebones' | 'small_library' | 'full'; title: string; desc: string; star?: boolean }[] = [
    { id: 'barebones', title: 'Barebones', desc: 'Catalog, events, and notifications only.' },
    { id: 'small_library', title: 'Small library', desc: 'Rooms, programs, digital, and makerspace on top of the basics.', star: true },
    { id: 'full', title: 'Everything', desc: 'Every feature turned on.' },
  ]

  return (
    <PageContainer width="form" className="py-8">
      {!embedded && (
        <>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            What does your library offer?
          </h1>
          <p className="text-lg text-earth-600 dark:text-earth-400 mb-8">
            Don&apos;t worry, you can change any of these later.
          </p>
        </>
      )}

      {/* Preset cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        {presetCards.map((p) => {
          const selected = !isCustom && config.feature_preset === p.id
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => selectPreset(p.id)}
              className={`relative p-5 rounded-xl border-2 text-left transition-all ${
                selected
                  ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-600'
              }`}
            >
              {p.star && (
                <span className="absolute top-2 right-2 text-xs font-medium text-lsc-rose">
                  Recommended
                </span>
              )}
              <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">{p.title}</h3>
              <p className="text-sm text-earth-600 dark:text-earth-400">{p.desc}</p>
            </button>
          )
        })}
      </div>

      {isCustom && (
        <p className="text-sm text-lsc-rose font-medium mb-4">Custom configuration</p>
      )}

      {/* Customize accordion */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm mb-8">
        <button
          type="button"
          onClick={() => setCustomizeOpen(!customizeOpen)}
          className="w-full flex items-center justify-between px-6 py-4 text-left"
        >
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Customize</span>
          {customizeOpen ? (
            <ChevronUp aria-hidden="true" className="w-5 h-5 text-earth-600" />
          ) : (
            <ChevronDown aria-hidden="true" className="w-5 h-5 text-earth-600" />
          )}
        </button>

        {customizeOpen && (
          <div className="px-6 pb-6 space-y-6">
            {FEATURE_GROUPS.map((group) => (
              <div key={group.label}>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-earth-600 dark:text-earth-400 mb-3">
                  {group.label}
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {group.features.map((feature) => (
                    <label
                      key={feature.key}
                      className="flex items-center gap-3 cursor-pointer select-none"
                    >
                      <button
                        type="button"
                        role="switch"
                        aria-checked={isFeatureOn(feature.key)}
                        onClick={() => toggleFeature(feature.key)}
                        className={`relative w-10 h-6 rounded-full transition-colors flex-shrink-0 ${
                          isFeatureOn(feature.key)
                            ? 'bg-lsc-rose'
                            : 'bg-earth-300 dark:bg-earth-600'
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 left-0.5 w-5 h-5 bg-lsc-white rounded-full shadow transition-transform ${
                            isFeatureOn(feature.key) ? 'translate-x-4' : 'translate-x-0'
                          }`}
                        />
                      </button>
                      <span className="text-sm text-earth-800 dark:text-earth-200">
                        {feature.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {!embedded && (
        <div className="flex justify-between">
          <button
            type="button"
            onClick={onBack}
            className="px-6 py-3 rounded-xl font-medium text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-600 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors"
          >
            Back
          </button>
          <button
            type="button"
            onClick={onNext}
            className="px-6 py-3 rounded-xl font-medium text-white bg-lsc-rose hover:bg-lsc-rose/90 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </PageContainer>
  )
}
