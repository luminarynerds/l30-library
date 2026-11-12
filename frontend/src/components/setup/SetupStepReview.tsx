/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { Search, Calendar, BookOpen, Wifi, Users, Rocket } from 'lucide-react'
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
  onBack: () => void
  onSubmit: () => Promise<void>
}

const ALL_FEATURE_KEYS = [
  'events_enabled', 'meeting_rooms_enabled', 'printing_enabled', 'sip2_rfid_enabled',
  'reading_programs_enabled', 'book_clubs_enabled', 'storytime_enabled', 'learning_platform_enabled',
  'digital_access_enabled', 'free_ebooks_enabled', 'ai_tools_enabled', 'streaming_enabled',
  'makerspace_enabled', 'genealogy_enabled', 'legal_services_enabled',
  'volunteers_enabled', 'home_delivery_enabled',
  'staff_scheduling_enabled', 'training_modules_enabled', 'collection_management_enabled', 'board_features_enabled',
]

const ALWAYS_ON = [
  'email_notifications_enabled', 'notifications_enabled', 'processing_queue_enabled', 'patron_portal_enabled',
]

const PRESETS: Record<string, string[]> = {
  barebones: ['events_enabled', ...ALWAYS_ON],
  small_library: [
    'events_enabled', 'meeting_rooms_enabled', 'reading_programs_enabled', 'book_clubs_enabled',
    'digital_access_enabled', 'free_ebooks_enabled', 'makerspace_enabled', 'genealogy_enabled',
    'legal_services_enabled', 'volunteers_enabled', 'learning_platform_enabled', 'storytime_enabled',
    'collection_management_enabled', 'home_delivery_enabled', 'staff_scheduling_enabled',
    'training_modules_enabled', 'board_features_enabled', 'printing_enabled',
    'outreach_enabled', 'literacy_programs_enabled', 'compliance_enabled', ...ALWAYS_ON,
  ],
  full: [
    ...ALL_FEATURE_KEYS,
    'outreach_enabled', 'literacy_programs_enabled', 'compliance_enabled', ...ALWAYS_ON,
  ],
}

const QUICK_LINKS = [
  { icon: Search, label: 'Search Catalog' },
  { icon: Calendar, label: 'Events' },
  { icon: BookOpen, label: 'Digital Resources' },
  { icon: Wifi, label: 'WiFi & Tech' },
  { icon: Users, label: 'Programs' },
]

export default function SetupStepReview({ config, onBack, onSubmit }: Props): React.ReactElement {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const enabledCount = useMemo(() => {
    const base: Record<string, boolean> = {}
    const presetKeys = (PRESETS[config.feature_preset] ?? PRESETS.small_library) as string[]
    for (const key of presetKeys) base[key] = true
    const merged = { ...base, ...config.feature_overrides }
    return ALL_FEATURE_KEYS.filter((k) => merged[k]).length
  }, [config.feature_preset, config.feature_overrides])

  const handleLaunch = async () => {
    setSubmitting(true)
    setError(null)
    try {
      await onSubmit()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <PageContainer width="form" className="py-8">
      <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
        You&apos;re all set!
      </h1>
      <p className="text-lg text-earth-600 dark:text-earth-400 mb-8">
        Here&apos;s a preview of your library. Review everything before launching.
      </p>

      {/* Mock homepage preview */}
      <div className="rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700 mb-6 shadow-sm">
        {/* Header */}
        <div
          className="h-12 flex items-center px-4"
          style={{ backgroundColor: config.primary_color }}
        >
          <span className="text-white font-bold text-sm">
            {config.library_name || 'Your Library'}
          </span>
        </div>

        {/* Hero */}
        <div
          className="px-6 py-8 text-center"
          style={{
            background: `linear-gradient(135deg, ${config.primary_color}, ${config.accent_color})`,
          }}
        >
          <h2 className="font-serif text-xl font-bold text-white mb-1">
            {config.hero_title || `Welcome to ${config.library_name}`}
          </h2>
          <p className="text-white/90 text-sm">
            {config.hero_subtitle || 'You belong here.'}
          </p>
          <div className="mt-4 flex justify-center">
            <div className="bg-lsc-white/20 backdrop-blur rounded-xl px-3 py-1.5 text-white text-xs flex items-center gap-2 w-48">
              <Search aria-hidden="true" className="w-3 h-3 opacity-60" />
              <span className="opacity-60">Search the catalog...</span>
            </div>
          </div>
        </div>

        {/* Quick links */}
        <div className="px-4 py-4 bg-lsc-white dark:bg-earth-800 flex flex-wrap gap-3 justify-center">
          {QUICK_LINKS.map((link) => (
            <div
              key={link.label}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-earth-50 dark:bg-earth-700 text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              <link.icon aria-hidden="true" className="w-3 h-3" />
              {link.label}
            </div>
          ))}
        </div>

        {/* Footer tagline */}
        {config.tagline && (
          <div className="px-4 py-2 bg-earth-50 dark:bg-earth-900 text-center border-t border-lsc-border dark:border-earth-700">
            <p className="text-xs text-earth-600 italic">{config.tagline}</p>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm mb-8">
        <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Summary</h3>
        <dl className="space-y-3">
          <div className="flex justify-between">
            <dt className="text-sm text-earth-600 dark:text-earth-400">Library</dt>
            <dd className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {config.library_name}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-sm text-earth-600 dark:text-earth-400">Admin</dt>
            <dd className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {config.admin_email}
            </dd>
          </div>
          <div className="flex justify-between items-center">
            <dt className="text-sm text-earth-600 dark:text-earth-400">Style</dt>
            <dd className="flex items-center gap-2">
              <span
                className="w-5 h-5 rounded-full border border-lsc-border dark:border-earth-600"
                style={{ backgroundColor: config.primary_color }}
              />
              <span
                className="w-5 h-5 rounded-full border border-lsc-border dark:border-earth-600"
                style={{ backgroundColor: config.accent_color }}
              />
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-sm text-earth-600 dark:text-earth-400">Features</dt>
            <dd className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {enabledCount} of {ALL_FEATURE_KEYS.length} enabled
            </dd>
          </div>
        </dl>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl mb-6">
          <p className="text-status-danger-700 dark:text-status-danger-400 text-sm">{error}</p>
        </div>
      )}

      <div className="flex flex-col sm:flex-row justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          className="px-6 py-3 rounded-xl font-medium text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-600 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors"
        >
          Go back and edit
        </button>
        <button
          type="button"
          onClick={handleLaunch}
          disabled={submitting}
          className="flex-1 sm:flex-none px-8 py-3 rounded-xl font-medium text-white bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-70 transition-colors flex items-center justify-center gap-2"
        >
          {submitting ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full motion-safe:animate-spin" />
              Launching...
            </>
          ) : (
            <>
              <Rocket aria-hidden="true" className="w-5 h-5" />
              Launch your library
            </>
          )}
        </button>
      </div>
    </PageContainer>
  )
}
