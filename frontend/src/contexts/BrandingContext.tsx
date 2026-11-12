/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react'
import { fetchApi } from '@/lib/api-client'
import { hexToRgb, hexToHsl, hslToRgbStr, lightenForDarkMode } from '@/lib/colors'

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

export interface DonateTier {
  name: string
  amount: string
  description: string
  benefits: string[]
  icon?: string
}

export interface DonateCard {
  title: string
  description: string
  icon?: string
}

export interface DonateTestimonial {
  initials: string
  name: string
  quote: string
}

export interface DonateConfig {
  intro?: string
  highlights?: string[]
  tiers?: DonateTier[]
  impact_areas?: DonateCard[]
  monthly?: { amounts?: string[]; note?: string }
  ways_to_give?: DonateCard[]
  testimonials?: DonateTestimonial[]
  tax_note?: string
}

export interface Branding {
  library_name: string
  library_short_name: string
  domain: string
  contact_email: string
  privacy_email: string
  indie_email: string
  giving_email: string
  events_email: string
  print_email: string
  makerspace_email: string
  phone: string
  address_line1: string
  address_line2: string
  city: string
  state: string
  zip_code: string
  primary_color: string
  accent_color: string
  logo_url: string
  hero_image_url: string
  display_font: string
  body_font: string
  secondary_color: string
  surface_color: string
  ink_color: string
  nav_style: string
  card_prefix: string
  product_name: string
  product_tagline: string
  hero_title: string
  hero_subtitle: string
  tagline: string
  is_demo: boolean
  bluesky_url: string
  mastodon_url: string
  seasonal_callout_active: boolean
  donate_config?: DonateConfig
  about_story?: AboutStory | null
  quiet_hours?: string | null
  sensory_friendly_times?: string | null
  low_stim_seating?: string | null
}

export interface AboutStoryEvent {
  year: string
  title: string
  description: string
}

export interface AboutStoryDirectorNote {
  paragraphs: string[]
  signature?: string
}

export interface AboutStory {
  intro?: string[]
  timeline?: AboutStoryEvent[]
  /* Tenant-written "A Note From the Director"; absent = stock i18n copy. */
  director_note?: AboutStoryDirectorNote | null
  /* True hides the director-note section entirely (e.g. until a real
     director writes one -- never ship fabricated words for a real person). */
  hide_director_note?: boolean
}

interface BrandingContextType {
  branding: Branding
  loading: boolean
  setupComplete: boolean
  hasAdmin: boolean
  refetch: () => Promise<void>
}

const DEFAULT_BRANDING: Branding = {
  library_name: 'Library',
  library_short_name: '',
  domain: '',
  contact_email: '',
  privacy_email: '',
  indie_email: '',
  giving_email: '',
  events_email: '',
  print_email: '',
  makerspace_email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  zip_code: '',
  primary_color: '#8B5E5E',
  accent_color: '#D49898',
  logo_url: '',
  hero_image_url: '',
  display_font: '',
  body_font: '',
  secondary_color: '',
  surface_color: '',
  ink_color: '',
  nav_style: '',
  card_prefix: '',
  product_name: '',
  product_tagline: '',
  hero_title: '',
  hero_subtitle: 'You belong here.',
  tagline: '',
  is_demo: false,
  bluesky_url: '',
  mastodon_url: '',
  seasonal_callout_active: false,
}

const BrandingContext = createContext<BrandingContextType | undefined>(undefined)

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>(DEFAULT_BRANDING)
  const [loading, setLoading] = useState(true)
  const [setupComplete, setSetupComplete] = useState(true)
  const [hasAdmin, setHasAdmin] = useState(true)
  const isDark = useIsDarkClass()

  const fetchBranding = useCallback(async () => {
    try {
      setLoading(true)
      // /branding sends max-age=3600; bust the browser cache so admin edits show up.
      const response = await fetchApi<Branding>(`/branding?_=${Date.now()}`)
      setBranding({ ...DEFAULT_BRANDING, ...response })
    } catch (_err) {
      // Fall back to defaults -- branding endpoint may not be available yet
      setBranding(DEFAULT_BRANDING)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBranding()
  }, [fetchBranding])

  useEffect(() => {
    fetchApi<{ setup_complete: boolean; has_admin: boolean }>('/branding/setup-status')
      .then(data => {
        setSetupComplete(data.setup_complete)
        setHasAdmin(data.has_admin)
      })
      .catch(() => {
        setSetupComplete(true)
        setHasAdmin(true)
      })
  }, [])

  useEffect(() => {
    if (!branding.primary_color) return
    // The bg/border tokens always use the raw brand color (so `bg-lsc-rose` with
    // white text retains 4.5:1 contrast). Only the text-only tokens get the
    // dark-mode lift, applied via `--accent-rose-text-rgb` and consumed by the
    // `textColor` namespace overrides in tailwind.config.js. See PR #677 regression.
    const rawPrimary = branding.primary_color
    const rawAccent = branding.accent_color
    const textPrimary = isDark ? lightenForDarkMode(rawPrimary) : rawPrimary
    const textAccent = isDark ? lightenForDarkMode(rawAccent) : rawAccent

    const deriveShades = (hex: string): Record<number, string> => {
      const [h, s] = hexToHsl(hex)
      return {
        50: hslToRgbStr(h, Math.max(s * 0.3, 8), 96),
        100: hslToRgbStr(h, Math.max(s * 0.4, 12), 88),
        200: hslToRgbStr(h, Math.max(s * 0.5, 16), 78),
        300: hslToRgbStr(h, s * 0.7, 60),
        400: hslToRgbStr(h, s * 0.8, 50),
        500: hslToRgbStr(h, s, 44),
        600: hslToRgbStr(h, s, 35),
        700: hslToRgbStr(h, s, 28),
        800: hslToRgbStr(h, s, 22),
        900: hslToRgbStr(h, s, 16),
      }
    }
    const root = document.documentElement
    // Bg/border tokens: always raw brand color.
    root.style.setProperty('--accent-rose', rawPrimary)
    root.style.setProperty('--accent-rose-rgb', hexToRgb(rawPrimary))
    root.style.setProperty('--accent-rose-light', rawAccent)
    root.style.setProperty('--accent-rose-light-rgb', hexToRgb(rawAccent))
    // Text-only tokens: lifted in dark mode, raw otherwise.
    root.style.setProperty('--accent-rose-text-rgb', hexToRgb(textPrimary))
    root.style.setProperty('--accent-rose-light-text-rgb', hexToRgb(textAccent))
    // Palette shades stay brand-accurate (used by gradients / bg patterns).
    const shades = deriveShades(rawAccent)
    for (const [shade, rgb] of Object.entries(shades)) {
      root.style.setProperty(`--accent-${shade}-rgb`, rgb)
    }
  }, [branding.primary_color, branding.accent_color, isDark])

  useEffect(() => {
    const root = document.documentElement
    if (branding.surface_color) {
      root.style.setProperty('--brand-surface-rgb', hexToRgb(branding.surface_color))
      // Light-mode border tone: surface nudged ~15% toward ink, so borders
      // share the brand's temperature instead of the stock cool gray. The
      // .light block in index.css consumes this with a stock fallback;
      // dark/high-contrast define their own --border-light and are unaffected.
      const ink = branding.ink_color || '#1E1A24'
      const mix = (a: string, b: string, t: number): string => {
        const pa = hexToRgb(a).split(' ').map(Number)
        const pb = hexToRgb(b).split(' ').map(Number)
        return pa.map((v, i) => Math.round(v + ((pb[i] ?? 0) - v) * t)).join(' ')
      }
      root.style.setProperty('--brand-border-rgb', mix(branding.surface_color, ink, 0.15))
    } else {
      root.style.removeProperty('--brand-surface-rgb')
      root.style.removeProperty('--brand-border-rgb')
    }
    if (branding.secondary_color) {
      root.style.setProperty('--brand-secondary-rgb', hexToRgb(branding.secondary_color))
    } else {
      root.style.removeProperty('--brand-secondary-rgb')
    }
    if (branding.ink_color) {
      root.style.setProperty('--brand-ink-rgb', hexToRgb(branding.ink_color))
    } else {
      root.style.removeProperty('--brand-ink-rgb')
    }
    if (branding.display_font) {
      root.style.setProperty('--display', `'${branding.display_font}', 'DM Serif Display', Georgia, serif`)
    } else {
      root.style.removeProperty('--display')
    }
  }, [branding.surface_color, branding.secondary_color, branding.ink_color, branding.display_font])

  const contextValue = useMemo(() => ({
    branding,
    loading,
    setupComplete,
    hasAdmin,
    refetch: fetchBranding,
  }), [branding, loading, setupComplete, hasAdmin, fetchBranding])

  return (
    <BrandingContext.Provider value={contextValue}>
      {children}
    </BrandingContext.Provider>
  )
}

export function useBranding(): Branding {
  const context = useContext(BrandingContext)
  if (!context) {
    throw new Error('useBranding must be used within BrandingProvider')
  }
  return context.branding
}

export function useBrandingContext(): BrandingContextType {
  const context = useContext(BrandingContext)
  if (!context) {
    throw new Error('useBrandingContext must be used within BrandingProvider')
  }
  return context
}
