/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useMemo } from 'react'

// Actions that can be rebound by the user
export type ShortcutAction =
  | 'focusSearch'
  | 'showHelp'
  | 'quickCheckout'
  | 'quickCheckin'
  | 'renewAll'
  | 'printReceipt'
  | 'editPatron'
  | 'blockToggle'
  | 'addNote'

export interface ShortcutBinding {
  key: string
  modifier?: 'ctrl' | null
  label: string
  description: string
  category: 'navigation' | 'actions' | 'general'
}

export type ShortcutBindings = Record<ShortcutAction, ShortcutBinding>

export const DEFAULT_BINDINGS: ShortcutBindings = {
  focusSearch: {
    key: 'f',
    modifier: 'ctrl',
    label: 'Ctrl + F',
    description: 'Focus search input',
    category: 'general',
  },
  showHelp: {
    key: '?',
    modifier: null,
    label: '?',
    description: 'Show keyboard shortcuts',
    category: 'general',
  },
  quickCheckout: {
    key: 'c',
    modifier: null,
    label: 'C',
    description: 'Quick checkout for patron',
    category: 'actions',
  },
  quickCheckin: {
    key: 'i',
    modifier: null,
    label: 'I',
    description: 'Quick check-in (focus input)',
    category: 'actions',
  },
  renewAll: {
    key: 'r',
    modifier: null,
    label: 'R',
    description: 'Renew all eligible items',
    category: 'actions',
  },
  printReceipt: {
    key: 'p',
    modifier: null,
    label: 'P',
    description: 'Print receipt for patron',
    category: 'actions',
  },
  editPatron: {
    key: 'e',
    modifier: null,
    label: 'E',
    description: 'Edit selected patron profile',
    category: 'actions',
  },
  blockToggle: {
    key: 'b',
    modifier: null,
    label: 'B',
    description: 'Block/unblock selected patron',
    category: 'actions',
  },
  addNote: {
    key: 'n',
    modifier: null,
    label: 'N',
    description: 'Add new note to patron',
    category: 'actions',
  },
}

// Non-rebindable navigation shortcuts (always active)
export const FIXED_SHORTCUTS = [
  { key: 'ArrowUp', label: 'Up Arrow', description: 'Select previous patron in list', category: 'navigation' as const },
  { key: 'ArrowDown', label: 'Down Arrow', description: 'Select next patron in list', category: 'navigation' as const },
  { key: 'Enter', label: 'Enter', description: 'Open selected patron details', category: 'navigation' as const },
  { key: 'Escape', label: 'Escape', description: 'Clear selection / close panels', category: 'navigation' as const },
]

const STORAGE_KEY_PREFIX = 'lsc_keyboard_prefs_'

function getStorageKey(userId: number): string {
  return `${STORAGE_KEY_PREFIX}${userId}`
}

function formatLabel(key: string, modifier?: 'ctrl' | null): string {
  if (modifier === 'ctrl') return `Ctrl + ${key.toUpperCase()}`
  if (key === '?') return '?'
  if (key === '/') return '/'
  return key.toUpperCase()
}

export function useKeyboardPreferences(userId: number | undefined) {
  const [bindings, setBindings] = useState<ShortcutBindings>(() => {
    if (!userId) return DEFAULT_BINDINGS
    try {
      const stored = localStorage.getItem(getStorageKey(userId))
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<ShortcutBindings>
        // Merge with defaults to handle any new actions added later
        return { ...DEFAULT_BINDINGS, ...parsed }
      }
    } catch { /* ignore corrupt data */ }
    return DEFAULT_BINDINGS
  })

  const save = useCallback((updated: ShortcutBindings) => {
    setBindings(updated)
    if (userId) {
      try {
        localStorage.setItem(getStorageKey(userId), JSON.stringify(updated))
      } catch { /* storage full, ignore */ }
    }
  }, [userId])

  const updateBinding = useCallback((action: ShortcutAction, key: string, modifier?: 'ctrl' | null) => {
    const updated = {
      ...bindings,
      [action]: {
        ...bindings[action],
        key,
        modifier: modifier ?? null,
        label: formatLabel(key, modifier),
      },
    }
    save(updated)
  }, [bindings, save])

  const resetToDefaults = useCallback(() => {
    save({ ...DEFAULT_BINDINGS })
  }, [save])

  // Find conflicts: returns the action that already uses this key+modifier combo
  const findConflict = useCallback((key: string, modifier: 'ctrl' | null | undefined, excludeAction: ShortcutAction): ShortcutAction | null => {
    const entries = Object.entries(bindings) as [ShortcutAction, ShortcutBinding][]
    for (const [action, binding] of entries) {
      if (action === excludeAction) continue
      const bindMod = binding.modifier ?? null
      const checkMod = modifier ?? null
      if (binding.key.toLowerCase() === key.toLowerCase() && bindMod === checkMod) {
        return action
      }
    }
    return null
  }, [bindings])

  const isDefault = useMemo(() => {
    return JSON.stringify(bindings) === JSON.stringify(DEFAULT_BINDINGS)
  }, [bindings])

  return { bindings, updateBinding, resetToDefaults, findConflict, isDefault }
}
