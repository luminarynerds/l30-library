/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
export type Language = 'en' | 'es'

const VALID_LANGUAGES: readonly Language[] = ['en', 'es']

export function isValidLanguage(lang: string): lang is Language {
  return (VALID_LANGUAGES as readonly string[]).includes(lang)
}

const STORAGE_KEY = 'lsc-language-preference'

export function getInitialLanguage(): Language {
  if (typeof window === 'undefined') return 'en'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && isValidLanguage(stored)) return stored
  const browserLang = navigator.language.split('-')[0] ?? ''
  if (isValidLanguage(browserLang)) return browserLang
  return 'en'
}

interface LanguageInfo {
  name: string
  nativeName: string
  flag?: string
  rtl?: boolean
}

export const languages: Record<Language, LanguageInfo> = {
  en: { name: 'English', nativeName: 'English', flag: '🇺🇸', rtl: false },
  es: { name: 'Spanish', nativeName: 'Español', flag: '🇲🇽', rtl: false },
}

export const LANGUAGES = languages

// Translation storage
type TranslationObject = Record<string, unknown>

const translations: Partial<Record<Language, TranslationObject>> = {}

const loadedLanguages = new Set<Language>()
const inflight = new Map<Language, Promise<void>>()

export async function loadLanguage(lang: Language): Promise<void> {
  if (loadedLanguages.has(lang)) return
  const existing = inflight.get(lang)
  if (existing) return existing

  const p = (async () => {
    try {
      let mod: { default: TranslationObject }
      switch (lang) {
        case 'en':
          mod = await import('./translations/en.json')
          break
        case 'es':
          mod = await import('./translations/es.json')
          break
        default:
          return
      }
      translations[lang] = mod.default
      loadedLanguages.add(lang)
    } catch (err) {
      Sentry.captureException(err)
    } finally {
      inflight.delete(lang)
    }
  })()
  inflight.set(lang, p)
  return p
}

export function isLanguageLoaded(lang: Language): boolean {
  return loadedLanguages.has(lang)
}

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((current, key) => (current as Record<string, unknown> | undefined)?.[key], obj)
}

function parseICUMessage(message: string, params: Record<string, unknown> = {}): string {
  // Handle plurals with improved regex that properly handles nested content
  const pluralRegex = /\{(\w+),\s*plural,\s*(.+)\}/
  const pluralMatch = pluralRegex.exec(message)

  if (pluralMatch) {
    const [fullMatch, variable, cases] = pluralMatch
    if (!variable || !cases) return message
    const count = params[variable!]

    if (count != null) {
      // Parse plural cases with better brace matching
      const parsedCases: Array<{ type: 'exact' | 'keyword', value: string | number, text: string }> = []
      let i = 0

      while (i < cases.length) {
        // Skip whitespace
        while (i < cases.length && /\s/.test(cases[i] as string)) i++
        if (i >= cases.length) break

        // Parse case selector (=0, =1, one, other, etc.)
        let selector = ''
        if (cases[i] === '=') {
          // Exact match like =0 or =1
          i++
          while (i < cases.length && /\d/.test(cases[i] as string)) {
            selector += cases[i]
            i++
          }
          parsedCases.push({ type: 'exact', value: parseInt(selector), text: '' })
        } else {
          // Keyword like 'one', 'other', etc.
          while (i < cases.length && /\w/.test(cases[i] as string)) {
            selector += cases[i]
            i++
          }
          parsedCases.push({ type: 'keyword', value: selector, text: '' })
        }

        // Skip whitespace before opening brace
        while (i < cases.length && /\s/.test(cases[i] as string)) i++

        // Find the matching closing brace for this case
        if (i < cases.length && cases[i] === '{') {
          i++ // Skip opening brace
          let braceCount = 1
          let caseText = ''

          while (i < cases.length && braceCount > 0) {
            if (cases[i] === '{') {
              braceCount++
              caseText += cases[i]
            } else if (cases[i] === '}') {
              braceCount--
              if (braceCount > 0) caseText += cases[i]
            } else {
              caseText += cases[i]
            }
            i++
          }

          const lastCase = parsedCases[parsedCases.length - 1]
          if (lastCase) {
            lastCase.text = caseText.trim()
          }
        }
      }

      // Find matching case. Precedence per ICU: exact (=N) wins, then the
      // locale's plural category (Intl.PluralRules: 'one' for 1 in en/es),
      // then 'other' as the required fallback.
      const category = typeof count === 'number'
        ? new Intl.PluralRules(getCurrentLanguage()).select(count)
        : 'other'
      let result = ''
      let categoryText: string | null = null
      let otherText: string | null = null
      for (const { type, value, text } of parsedCases) {
        if (type === 'exact' && value === count) {
          result = text.replace(/#/g, count.toString())
          break
        } else if (type === 'keyword' && value === category && categoryText === null) {
          categoryText = text
        } else if (type === 'keyword' && value === 'other' && otherText === null) {
          otherText = text
        }
      }
      if (!result) {
        const fallback = categoryText ?? otherText
        if (fallback !== null) result = fallback.replace(/#/g, count.toString())
      }

      if (result) {
        message = message.replace(fullMatch, result)
      }
    }
  }

  // Handle simple variables
  Object.entries(params).forEach(([key, value]) => {
    message = message.split("{{" + key + "}}").join(String(value)).split("{" + key + "}").join(String(value))
  })

  return message
}

export function getTranslation(
  key: string,
  lang: string = 'en',
  params?: Record<string, unknown>,
  defaultValue?: string,
): string {
  const language = lang as Language

  // Get translations for language, fallback to English
  const langTranslations = translations[language] || translations.en

  // Pre-mount window: language not loaded yet. main.tsx awaits loadLanguage()
  // before mounting React, so this only fires from non-render paths called
  // too early. Use defaultValue if provided rather than leaking the raw key.
  if (!langTranslations) return defaultValue ?? key

  // Get the translation value
  let value = getNestedValue(langTranslations, key)

  // Fallback to English if not found
  if (value === undefined && language !== 'en' && translations.en) {
    value = getNestedValue(translations.en, key)
  }

  // If still not found: defaultValue if caller provided one (silent), else
  // leak the key and warn so the missing translation gets noticed.
  if (value === undefined) {
    if (defaultValue === undefined) {
      Sentry.captureMessage(`Translation missing for key: ${key} (language: ${language})`, 'warning')
    }
    return defaultValue ?? key
  }

  // Value present but not a string — schema bug, always warn.
  if (typeof value !== 'string') {
    Sentry.captureMessage(`Translation value is not a string for key: ${key}`, 'warning')
    return defaultValue ?? key
  }

  // Parse ICU message format if params provided
  if (params) {
    return parseICUMessage(value, params)
  }

  return value
}

export function createTranslator(lang: Language) {
  return (key: string, params?: Record<string, unknown>) => getTranslation(key, lang, params)
}

export function getLanguageTranslations(lang: Language): TranslationObject {
  return translations[lang] || translations.en || {}
}

export function isRTL(lang: Language): boolean {
  return languages[lang]?.rtl || false
}

// Module-level current language, updated by I18nProvider via setCurrentLanguage()
let currentLanguage: Language = 'en'

export function setCurrentLanguage(lang: Language): void {
  currentLanguage = lang
}

export function getCurrentLanguage(): Language {
  return currentLanguage
}

export function t(
  key: string,
  paramsOrFallback?: Record<string, unknown> | string,
): string {
  if (typeof paramsOrFallback === 'string') {
    return getTranslation(key, currentLanguage, undefined, paramsOrFallback)
  }
  return getTranslation(key, currentLanguage, paramsOrFallback)
}

export default {
  languages,
  getTranslation,
  createTranslator,
  getLanguageTranslations,
  isRTL,
  t,
}
