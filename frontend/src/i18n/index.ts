/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * i18n (Internationalization) System
 * Export all i18n utilities for easy importing
 */

// Main hooks and providers
export { I18nProvider, useTranslation, useLanguage } from './I18nContext'

// Translation functions and types
export {
  getTranslation,
  createTranslator,
  getLanguageTranslations,
  isRTL,
  languages,
  LANGUAGES,
  t,
  type Language,
} from './translations'

// Localization utilities
export {
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
  formatDuration,
  getLocale,
  getCurrentLocale,
  getFirstDayOfWeek,
} from './localization'

// Configuration
export { RTL_LANGUAGES, isRTLLanguage } from './config'
