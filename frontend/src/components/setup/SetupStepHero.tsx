/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { Type } from 'lucide-react'
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

export default function SetupStepHero({ config, onChange, onBack, onNext, embedded }: Props): React.ReactElement {
  useEffect(() => {
    if (!config.hero_title && config.library_name) {
      onChange({ ...config, hero_title: `Welcome to ${config.library_name}` })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent transition-colors'
  const labelClass = 'block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1'

  return (
    <PageContainer width="form" className="py-8">
      {!embedded && (
        <>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Welcome your community
          </h1>
          <p className="text-lg text-earth-600 dark:text-earth-400 mb-8">
            This is what people see when they visit your site.
          </p>
        </>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-earth-700 flex items-center justify-center">
            <Type aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </div>
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Hero Section</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="hero_title" className={labelClass}>
              Headline
            </label>
            <input
              id="hero_title"
              type="text"
              className={inputClass}
              placeholder={`Welcome to ${config.library_name || 'Your Library'}`}
              value={config.hero_title}
              onChange={(e) => onChange({ ...config, hero_title: e.target.value })}
            />
            <p className="text-xs text-earth-600 dark:text-earth-400 mt-1">Keep it short and welcoming</p>
          </div>

          <div>
            <label htmlFor="hero_subtitle" className={labelClass}>
              Subtitle
            </label>
            <input
              id="hero_subtitle"
              type="text"
              className={inputClass}
              placeholder="You belong here."
              value={config.hero_subtitle}
              onChange={(e) => onChange({ ...config, hero_subtitle: e.target.value })}
            />
          </div>

          <div>
            <label htmlFor="tagline" className={labelClass}>
              Footer tagline (optional)
            </label>
            <input
              id="tagline"
              type="text"
              className={inputClass}
              placeholder="Free for everyone. Open to all."
              value={config.tagline}
              onChange={(e) => onChange({ ...config, tagline: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* Live preview */}
      <div className="rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700 mb-8">
        <div
          className="px-6 py-10 text-center"
          style={{
            background: `linear-gradient(135deg, ${config.primary_color}, ${config.accent_color})`,
          }}
        >
          <h3 className="text-2xl font-serif font-bold text-white mb-2">
            {config.hero_title || `Welcome to ${config.library_name || 'Your Library'}`}
          </h3>
          <p className="text-white/90 text-lg">
            {config.hero_subtitle || 'You belong here.'}
          </p>
          <div className="mt-6 flex justify-center">
            <div className="bg-lsc-white/20 backdrop-blur rounded-xl px-4 py-2 text-white text-sm flex items-center gap-2 w-64">
              <span className="opacity-60">Search the catalog...</span>
            </div>
          </div>
        </div>
        {config.tagline && (
          <div className="px-4 py-3 bg-earth-50 dark:bg-earth-900 text-center">
            <p className="text-sm text-earth-600 dark:text-earth-400 italic">{config.tagline}</p>
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
