/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Date and number localization utilities
 * Uses native Intl API for proper localization
 */

import { Language, getCurrentLanguage } from './translations'

// Map our language codes to BCP 47 locale tags
const LOCALE_MAP: Record<Language, string> = {
  en: 'en-US',
  es: 'es-419',
}

export function getLocale(language: Language): string {
  return LOCALE_MAP[language] || 'en-US'
}

/**
 * BCP 47 locale tag for the currently active UI language.
 * For toLocale*String call sites (API helpers, module-level formatters)
 * that can't reach useTranslation(); components re-render on language
 * switch, so these pick up the new locale on the next render.
 */
export function getCurrentLocale(): string {
  return getLocale(getCurrentLanguage())
}

export function formatDate(
  date: Date | string | number,
  language: Language,
  options: Intl.DateTimeFormatOptions = {}
): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date

  if (isNaN(dateObj.getTime())) {
    return 'Invalid date'
  }

  const locale = getLocale(language)
  return new Intl.DateTimeFormat(locale, options).format(dateObj)
}

export function formatShortDate(date: Date | string | number, language: Language): string {
  return formatDate(date, language, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
  })
}

export function formatLongDate(date: Date | string | number, language: Language): string {
  return formatDate(date, language, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function formatTime(date: Date | string | number, language: Language, use24Hour?: boolean): string {
  // Default to locale preference if not specified
  const hour12 = use24Hour === undefined ? undefined : !use24Hour

  return formatDate(date, language, {
    hour: 'numeric',
    minute: '2-digit',
    hour12,
  })
}

export function formatDateTime(date: Date | string | number, language: Language): string {
  return formatDate(date, language, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function formatRelativeTime(
  date: Date | string | number,
  language: Language,
  baseDate: Date = new Date()
): string {
  const dateObj = typeof date === 'string' || typeof date === 'number' ? new Date(date) : date
  const locale = getLocale(language)

  const diffMs = dateObj.getTime() - baseDate.getTime()
  const diffSec = Math.round(diffMs / 1000)
  const diffMin = Math.round(diffSec / 60)
  const diffHour = Math.round(diffMin / 60)
  const diffDay = Math.round(diffHour / 24)
  const diffWeek = Math.round(diffDay / 7)
  const diffMonth = Math.round(diffDay / 30)
  const diffYear = Math.round(diffDay / 365)

  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' })

  if (Math.abs(diffSec) < 60) {
    return rtf.format(diffSec, 'second')
  } else if (Math.abs(diffMin) < 60) {
    return rtf.format(diffMin, 'minute')
  } else if (Math.abs(diffHour) < 24) {
    return rtf.format(diffHour, 'hour')
  } else if (Math.abs(diffDay) < 7) {
    return rtf.format(diffDay, 'day')
  } else if (Math.abs(diffWeek) < 4) {
    return rtf.format(diffWeek, 'week')
  } else if (Math.abs(diffMonth) < 12) {
    return rtf.format(diffMonth, 'month')
  } else {
    return rtf.format(diffYear, 'year')
  }
}

export function formatNumber(
  value: number,
  language: Language,
  options: Intl.NumberFormatOptions = {}
): string {
  const locale = getLocale(language)
  return new Intl.NumberFormat(locale, options).format(value)
}

export function formatCurrency(
  value: number,
  language: Language,
  currency: string = 'CAD'
): string {
  return formatNumber(value, language, {
    style: 'currency',
    currency,
  })
}

export function formatPercentage(
  value: number,
  language: Language,
  decimals: number = 0
): string {
  return formatNumber(value, language, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatFileSize(bytes: number, language: Language): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = bytes
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${formatNumber(size, language, { maximumFractionDigits: 1 })} ${units[unitIndex]}`
}

export function parseLocalizedDate(dateString: string, _language: Language): Date | null {
  try {
    // Try native parsing first
    const date = new Date(dateString)
    if (!isNaN(date.getTime())) {
      return date
    }

    // Could add more sophisticated parsing here if needed
    return null
  } catch {
    return null
  }
}

export function getFirstDayOfWeek(language: Language): number {
  // Most locales start on Monday except US (Sunday)
  return language === 'en' ? 0 : 1
}

export function formatDuration(ms: number, _language: Language): string {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days}d ${hours % 24}h`
  } else if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

export default {
  getLocale,
  formatDate,
  formatShortDate,
  formatLongDate,
  formatTime,
  formatDateTime,
  formatRelativeTime,
  formatNumber,
  formatCurrency,
  formatPercentage,
  formatFileSize,
  parseLocalizedDate,
  getFirstDayOfWeek,
  formatDuration,
}
