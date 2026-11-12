/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Check } from 'lucide-react'
import { hexToRgb, lightenForDarkMode } from '@/lib/colors'
import PageContainer from '@/components/layout/PageContainer'

function useIsDarkClass(): boolean {
  const [isDark, setIsDark] = useState(
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
  )
  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    const update = () => setIsDark(root.classList.contains('dark'))
    update()
    const observer = new MutationObserver(update)
    observer.observe(root, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])
  return isDark
}

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

interface ColorPreset {
  id: string
  name: string
  primary: string
  accent: string
}

const COLOR_PRESETS: ColorPreset[] = [
  { id: 'terracotta', name: 'Warm Terracotta', primary: '#C4704B', accent: '#8B5E5E' },
  { id: 'ocean', name: 'Ocean Blue', primary: '#2E86AB', accent: '#1B4965' },
  { id: 'forest', name: 'Forest Green', primary: '#4A7C59', accent: '#2D4A3E' },
  { id: 'berry', name: 'Berry Purple', primary: '#7B4B8A', accent: '#5C2D5C' },
  { id: 'sunset', name: 'Sunset Orange', primary: '#D4613E', accent: '#8B3A2A' },
  { id: 'navy', name: 'Classic Navy', primary: '#34495E', accent: '#2C3E50' },
]

export default function SetupStepColors({ config, onChange, onBack, onNext, embedded }: Props): React.ReactElement {
  const [customOpen, setCustomOpen] = useState(false)
  const [primaryText, setPrimaryText] = useState(config.primary_color)
  const [accentText, setAccentText] = useState(config.accent_color)
  const isDark = useIsDarkClass()

  // Resync local text when config changes externally (preset swatch / color picker)
  useEffect(() => {
    setPrimaryText(config.primary_color)
  }, [config.primary_color])
  useEffect(() => {
    setAccentText(config.accent_color)
  }, [config.accent_color])

  const selectedPreset = COLOR_PRESETS.find(
    (p) => p.primary === config.primary_color && p.accent === config.accent_color,
  )

  useEffect(() => {
    // Match BrandingContext: bg/border tokens use raw brand colors; text-only
    // tokens get the dark-mode lift so `bg-lsc-rose` retains 4.5:1 contrast
    // with white text while `text-lsc-rose` stays legible on dark surfaces.
    const rawPrimary = config.primary_color
    const rawAccent = config.accent_color
    const textPrimary = isDark ? lightenForDarkMode(rawPrimary) : rawPrimary
    const textAccent = isDark ? lightenForDarkMode(rawAccent) : rawAccent
    const root = document.documentElement
    root.style.setProperty('--accent-rose', rawPrimary)
    root.style.setProperty('--accent-rose-rgb', hexToRgb(rawPrimary))
    root.style.setProperty('--accent-rose-light', rawAccent)
    root.style.setProperty('--accent-rose-light-rgb', hexToRgb(rawAccent))
    root.style.setProperty('--accent-rose-text-rgb', hexToRgb(textPrimary))
    root.style.setProperty('--accent-rose-light-text-rgb', hexToRgb(textAccent))
  }, [config.primary_color, config.accent_color, isDark])

  const selectPreset = useCallback(
    (preset: ColorPreset) => {
      onChange({ ...config, primary_color: preset.primary, accent_color: preset.accent })
    },
    [config, onChange],
  )

  return (
    <PageContainer width="form" className="py-8">
      {!embedded && (
        <>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
            Pick your style
          </h1>
          <p className="text-lg text-earth-600 dark:text-earth-400 mb-8">
            Choose colors that represent your library.
          </p>
        </>
      )}

      {/* Preset grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {COLOR_PRESETS.map((preset) => {
          const selected = selectedPreset?.id === preset.id
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => selectPreset(preset)}
              className={`relative rounded-xl border-2 overflow-hidden transition-all ${
                selected
                  ? 'border-earth-900 dark:border-white ring-2 ring-earth-900/20 dark:ring-white/20'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-border dark:hover:border-earth-600'
              }`}
            >
              {selected && (
                <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-earth-900 dark:bg-lsc-white flex items-center justify-center z-10">
                  <Check aria-hidden="true" className="w-4 h-4 text-white dark:text-earth-900" />
                </div>
              )}
              {/* Mini preview */}
              <div
                className="h-10 flex items-center px-3"
                style={{ backgroundColor: preset.primary }}
              >
                <span className="text-xs font-medium text-white truncate">Your Library</span>
              </div>
              <div className="p-3 bg-lsc-white dark:bg-earth-800">
                <div
                  className="w-16 h-6 rounded-lg text-xs text-white flex items-center justify-center font-medium"
                  style={{ backgroundColor: preset.accent }}
                >
                  Button
                </div>
              </div>
              <div className="px-3 pb-3 bg-lsc-white dark:bg-earth-800">
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{preset.name}</p>
                <p className="text-xs text-earth-600">
                  {preset.primary} / {preset.accent}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      {/* Custom colors accordion */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm mb-6">
        <button
          type="button"
          onClick={() => setCustomOpen(!customOpen)}
          className="w-full flex items-center justify-between px-6 py-4 text-left"
        >
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Custom Colors</span>
          <span className="text-sm text-earth-600">{customOpen ? 'Close' : 'Open'}</span>
        </button>

        {customOpen && (
          <div className="px-6 pb-6 space-y-4">
            <div className="flex items-center gap-4">
              <label htmlFor="primary_color" className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 w-28">
                Primary color
              </label>
              <input
                id="primary_color"
                type="color"
                value={config.primary_color}
                onChange={(e) => onChange({ ...config, primary_color: e.target.value })}
                className="w-10 h-10 rounded-lg border border-lsc-border dark:border-earth-700 cursor-pointer"
              />
              <input
                type="text"
                data-testid="primary-hex-input"
                value={primaryText}
                onChange={(e) => {
                  const v = e.target.value
                  setPrimaryText(v)
                  if (/^#[0-9A-Fa-f]{6}$/.test(v)) onChange({ ...config, primary_color: v })
                }}
                onBlur={() => {
                  if (!/^#[0-9A-Fa-f]{6}$/.test(primaryText)) setPrimaryText(config.primary_color)
                }}
                className="w-28 px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm font-mono"
              />
            </div>
            <div className="flex items-center gap-4">
              <label htmlFor="accent_color" className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 w-28">
                Accent color
              </label>
              <input
                id="accent_color"
                type="color"
                value={config.accent_color}
                onChange={(e) => onChange({ ...config, accent_color: e.target.value })}
                className="w-10 h-10 rounded-lg border border-lsc-border dark:border-earth-700 cursor-pointer"
              />
              <input
                type="text"
                data-testid="accent-hex-input"
                value={accentText}
                onChange={(e) => {
                  const v = e.target.value
                  setAccentText(v)
                  if (/^#[0-9A-Fa-f]{6}$/.test(v)) onChange({ ...config, accent_color: v })
                }}
                onBlur={() => {
                  if (!/^#[0-9A-Fa-f]{6}$/.test(accentText)) setAccentText(config.accent_color)
                }}
                className="w-28 px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm font-mono"
              />
            </div>
          </div>
        )}
      </div>

      {/* Live preview */}
      <div className="rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700 mb-8">
        <div
          className="h-12 flex items-center px-4"
          style={{ backgroundColor: config.primary_color }}
        >
          <span className="text-white font-bold text-sm">
            {config.library_name || 'Your Library'}
          </span>
        </div>
        <div className="p-6 bg-lsc-white dark:bg-earth-800 flex items-center gap-4">
          <span className="text-sm text-earth-600 dark:text-earth-400">Preview</span>
          <span
            className="px-4 py-2 rounded-xl text-sm font-medium text-white"
            style={{ backgroundColor: config.accent_color }}
          >
            Action Button
          </span>
          <span
            className="text-sm font-medium"
            style={{ color: config.primary_color }}
          >
            Link Text
          </span>
        </div>
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
