/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Utility functions for components
 * This file provides commonly used utilities in shadcn/ui-style components
 */

import { clsx } from '@/utils/helpers'

export function cn(...inputs: (string | boolean | undefined | null)[]): string {
  return clsx(...inputs)
}

/**
 * Strip keys whose value is `undefined` from an object.
 * With `exactOptionalPropertyTypes` enabled, optional properties (`prop?: T`)
 * do NOT accept `undefined` — the key must be absent entirely.
 * Wrap object literals with this helper before passing them to typed functions.
 *
 * Usage: `someFunction(clean({ status: maybeUndefined, page: 1 }))`
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function clean<T extends Record<string, any>>(obj: T): { [K in keyof T]: Exclude<T[K], undefined> } {
  const result: Record<string, unknown> = {}
  for (const key of Object.keys(obj)) {
    if (obj[key] !== undefined) {
      result[key] = obj[key]
    }
  }
  return result as { [K in keyof T]: Exclude<T[K], undefined> }
}
