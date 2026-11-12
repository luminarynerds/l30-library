/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * i18n configuration
 * Contains language settings and utility functions
 */

// Languages that use right-to-left (RTL) text direction
export const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur']

export function isRTLLanguage(lang: string): boolean {
  return RTL_LANGUAGES.includes(lang)
}

const config = {
  RTL_LANGUAGES,
  isRTLLanguage,
}

export default config
