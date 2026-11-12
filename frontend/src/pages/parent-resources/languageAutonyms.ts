/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Language autonym lookup for the parent-resource directory chips +
 * filter. Autonyms (a language's name in its own script) are used so a
 * speaker can recognize their own language even when the chrome is in
 * a different one.
 *
 * Codes not present here fall back to the uppercase code (KAR, HMN).
 * That fallback is intentional -- silence would be worse, and the
 * library can hand-curate this map as it adds new languages without
 * shipping a 200kB CLDR dataset for one feature.
 */
export const LANGUAGE_AUTONYMS: Readonly<Record<string, string>> = {
  // L30 chrome languages (en/es/fr/de/ru/ar/zh).
  en: 'English',
  es: 'Español',
  fr: 'Français',
  de: 'Deutsch',
  ru: 'Русский',
  ar: 'العربية',
  zh: '中文',
  // Common community languages -- expand as the library serves them.
  so: 'Soomaali',
  vi: 'Tiếng Việt',
  hmn: 'Hmoob',
  kar: 'Karen', // No native script form in unicode; fallback to romanized.
  am: 'አማርኛ',
  bn: 'বাংলা',
  fa: 'فارسی',
  hi: 'हिन्दी',
  ja: '日本語',
  ko: '한국어',
  my: 'မြန်မာ',
  ne: 'नेपाली',
  pa: 'ਪੰਜਾਬੀ',
  pl: 'Polski',
  pt: 'Português',
  ro: 'Română',
  sw: 'Kiswahili',
  ta: 'தமிழ்',
  ti: 'ትግርኛ',
  tl: 'Tagalog',
  tr: 'Türkçe',
  uk: 'Українська',
  ur: 'اردو',
} as const

export function autonymOf(code: string): string {
  const trimmed = code.trim().toLowerCase()
  return LANGUAGE_AUTONYMS[trimmed] ?? trimmed.toUpperCase()
}
