/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Centralized utility functions for the LSC frontend
 */

import { parseDate } from './format-utils'
import { getCurrentLocale } from '@/i18n'

export function safeInitial(value: string | null | undefined, fallback: string = '?'): string {
  if (!value || typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed.charAt(0).toUpperCase() || fallback
}

type ClsxValue = string | boolean | undefined | null | Record<string, boolean | undefined> | ClsxValue[]

export function clsx(...classes: ClsxValue[]): string {
  const result: string[] = []
  for (const cls of classes) {
    if (!cls) continue
    if (typeof cls === 'string') {
      result.push(cls)
    } else if (Array.isArray(cls)) {
      const inner = clsx(...cls)
      if (inner) result.push(inner)
    } else if (typeof cls === 'object') {
      for (const [key, val] of Object.entries(cls)) {
        if (val) result.push(key)
      }
    }
  }
  return result.join(' ')
}

export function formatDate(dateString: string | Date | null | undefined): string {
  if (dateString === null || dateString === undefined || dateString === '') return ''
  const date = parseDate(dateString)
  if (date === null) return 'Invalid date'

  return date.toLocaleDateString(getCurrentLocale(), {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export function formatDateTime(dateString: string | Date | null | undefined): string {
  if (dateString === null || dateString === undefined || dateString === '') return ''
  const date = parseDate(dateString)
  if (date === null) return 'Invalid date'

  return date.toLocaleString(getCurrentLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}

export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return function (...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => {
      func(...args)
      timeout = null
    }, wait)
  }
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export function capitalizeFirst(str: string | null | undefined, fallback = ''): string {
  if (!str || typeof str !== 'string') return fallback
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value).length === 0
  return false
}

export function isOverdue(dateString: string | Date): boolean {
  const date = parseDate(dateString)
  if (date === null) return false
  return date < new Date()
}
