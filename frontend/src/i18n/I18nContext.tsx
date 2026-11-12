/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * i18n Context for React components
 * Provides translation functionality throughout the app
 */

import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react'
import {
  Language,
  getTranslation,
  isRTL,
  loadLanguage,
  isLanguageLoaded,
  setCurrentLanguage,
  getInitialLanguage,
  isValidLanguage,
} from './translations'
import { fetchApi } from '@/lib/api-client'
import { useBrandingContext } from '@/contexts/BrandingContext'
import { getAccessToken } from '@/utils/tokenStore'

interface I18nContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string
  isRTL: boolean
}

const I18nContext = createContext<I18nContextType | undefined>(undefined)

const STORAGE_KEY = 'lsc-language-preference'

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage)
  const [rtl, setRtl] = useState<boolean>(isRTL(getInitialLanguage()))
  // Version counter to force re-render after async translation loads
  const [, setVersion] = useState(0)

  // On mount, load the initial language if it's not English
  useEffect(() => {
    const initial = getInitialLanguage()
    if (initial !== 'en' && !isLanguageLoaded(initial)) {
      loadLanguage(initial).then(() => {
        // Force re-render so translations are picked up
        setVersion(v => v + 1)
      })
    }
  }, [])

  const setLanguage = useCallback((lang: Language) => {
    // Save to localStorage immediately
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, lang)
    }

    // Update document properties
    document.documentElement.lang = lang
    document.documentElement.dir = isRTL(lang) ? 'rtl' : 'ltr'

    // If authenticated, sync to API
    const token = getAccessToken()
    if (token) {
      fetchApi('/learning/preferences', {
        method: 'PUT',
        token,
        body: { language_preference: lang },
      }).catch(() => {
        // Silent fail -- localStorage is the primary source
      })
    }

    // Load translations on demand, then switch language
    if (!isLanguageLoaded(lang)) {
      loadLanguage(lang).then(() => {
        setLanguageState(lang)
        setRtl(isRTL(lang))
      })
    } else {
      setLanguageState(lang)
      setRtl(isRTL(lang))
    }
  }, [])

  // Inject branding values as default interpolation params for all translations
  const { branding } = useBrandingContext()
  const brandingDefaults = useMemo<Record<string, unknown>>(
    () => ({
      libraryName: branding.library_name,
      libraryShortName: branding.library_short_name,
      contactEmail: branding.contact_email,
      privacyEmail: branding.privacy_email,
      givingEmail: branding.giving_email,
      phone: branding.phone,
      addressLine1: branding.address_line1,
      cityState: branding.address_line2,
      cityStateZip: branding.address_line2,
      cityName: branding.address_line2.split(',')[0]?.trim() || '',
      streetName: branding.address_line1,
      cardPrefix: branding.card_prefix,
    }),
    [
      branding.library_name,
      branding.library_short_name,
      branding.contact_email,
      branding.privacy_email,
      branding.giving_email,
      branding.phone,
      branding.address_line1,
      branding.address_line2,
      branding.card_prefix,
    ]
  )

  // Translation function - supports params object or string fallback.
  // String form passes the fallback as defaultValue so getTranslation can
  // suppress the Sentry "missing key" warning (caller has accepted the miss).
  // Branding values are always available as default interpolation params.
  const t = useCallback(
    (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      if (typeof paramsOrFallback === 'string') {
        return getTranslation(key, language, brandingDefaults, paramsOrFallback)
      }
      return getTranslation(key, language, { ...brandingDefaults, ...paramsOrFallback })
    },
    [language, brandingDefaults]
  )

  // Set initial document properties and sync module-level language
  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = rtl ? 'rtl' : 'ltr'
    setCurrentLanguage(language)
  }, [language, rtl])

  return (
    <I18nContext.Provider value={{ language, setLanguage, t, isRTL: rtl }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useTranslation() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useTranslation must be used within I18nProvider')
  }
  return context
}

export function useLanguage() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error('useLanguage must be used within I18nProvider')
  }
  return { language: context.language, setLanguage: context.setLanguage, isRTL: context.isRTL }
}

/**
 * Applies the account's saved language once per login.
 *
 * Mounted inside AuthProvider (I18nProvider itself renders above it and can't
 * see auth state — at provider mount the access token isn't restored yet, so
 * a mount-time fetch would silently never run). When auth becomes ready this
 * fetches the saved preference and applies it if it differs, so a patron's
 * language follows them to a fresh device. localStorage remains the source of
 * truth between logins.
 */
export function LanguagePreferenceSync({ isAuthenticated }: { isAuthenticated: boolean }) {
  const { language, setLanguage } = useTranslation()

  useEffect(() => {
    if (!isAuthenticated) return
    const token = getAccessToken()
    if (!token) return

    let cancelled = false
    fetchApi<{ language_preference?: string | null }>('/learning/preferences', { token })
      .then((data) => {
        const apiLang = data?.language_preference
        if (!cancelled && apiLang && isValidLanguage(apiLang) && apiLang !== language) {
          setLanguage(apiLang as Language)
        }
      })
      .catch(() => {
        // Silent fail -- localStorage value is fine as fallback
      })
    return () => { cancelled = true }
  // Apply once per auth transition, not on every language change.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  return null
}
