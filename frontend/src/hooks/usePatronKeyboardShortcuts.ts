/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * usePatronKeyboardShortcuts Hook
 *
 * Provides keyboard navigation and shortcuts for the Staff Patrons page.
 * Reads customizable bindings from useKeyboardPreferences.
 * Fixed shortcuts (arrows, enter, escape) are always active.
 */

import { useEffect, useCallback, useRef } from 'react'
import type { ShortcutBindings } from './useKeyboardPreferences'

// ==================== Types ====================

export interface KeyboardShortcutsConfig {
  onFocusSearch: () => void
  onEscape: () => void
  onNavigateUp: () => void
  onNavigateDown: () => void
  onEnter: () => void
  onEdit: () => void
  onBlockToggle: () => void
  onAddNote: () => void
  onShowHelp: () => void
  onQuickCheckout?: () => void
  onRenewAll?: () => void
  onQuickCheckin?: () => void
  onPrintReceipt?: () => void
  enabled?: boolean
  bindings: ShortcutBindings
}

// ==================== Hook ====================

export function usePatronKeyboardShortcuts(config: KeyboardShortcutsConfig): void {
  const { enabled = true } = config

  // Use refs to avoid stale closures
  const configRef = useRef(config)
  useEffect(() => { configRef.current = config; }, [config])


  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return

    const { bindings } = configRef.current

    // Check if focus is in an input, textarea, or contenteditable
    const target = event.target as HTMLElement
    const isInputFocused =
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable ||
      target.closest('[role="dialog"]') !== null

    const isMod = event.metaKey || event.ctrlKey
    const isShift = event.shiftKey
    const pressedKey = event.key.toLowerCase()

    // --- Modifier shortcuts (work even in inputs) ---
    // Check all bindings that require ctrl modifier
    if (isMod) {
      if (bindings.focusSearch.modifier === 'ctrl' && pressedKey === bindings.focusSearch.key) {
        event.preventDefault()
        configRef.current.onFocusSearch()
        return
      }
    }

    // --- ? for help (shift+/ or literal ?) ---
    const helpBinding = bindings.showHelp
    if (helpBinding.key === '?' && (event.key === '?' || (isShift && event.key === '/'))) {
      if (!isInputFocused) {
        event.preventDefault()
        configRef.current.onShowHelp()
        return
      }
    } else if (helpBinding.key !== '?' && !helpBinding.modifier && pressedKey === helpBinding.key) {
      if (!isInputFocused && !isMod) {
        event.preventDefault()
        configRef.current.onShowHelp()
        return
      }
    }

    // --- Escape (always works, fixed) ---
    if (event.key === 'Escape') {
      if (!isInputFocused) event.preventDefault()
      configRef.current.onEscape()
      return
    }

    // --- Following shortcuts only when not in an input ---
    if (isInputFocused) return

    // Fixed navigation keys
    switch (event.key) {
      case 'ArrowUp':
        event.preventDefault()
        configRef.current.onNavigateUp()
        return
      case 'ArrowDown':
        event.preventDefault()
        configRef.current.onNavigateDown()
        return
      case 'Enter':
        event.preventDefault()
        configRef.current.onEnter()
        return
    }

    // Customizable action bindings (no modifier required)
    if (isMod) return

    const actionMap: Record<string, () => void> = {}
    const add = (binding: { key: string; modifier?: 'ctrl' | null }, handler: (() => void) | undefined) => {
      if (!handler || binding.modifier === 'ctrl') return
      actionMap[binding.key.toLowerCase()] = handler
    }

    add(bindings.editPatron, configRef.current.onEdit)
    add(bindings.blockToggle, configRef.current.onBlockToggle)
    add(bindings.addNote, configRef.current.onAddNote)
    add(bindings.quickCheckout, configRef.current.onQuickCheckout)
    add(bindings.renewAll, configRef.current.onRenewAll)
    add(bindings.quickCheckin, configRef.current.onQuickCheckin)
    add(bindings.printReceipt, configRef.current.onPrintReceipt)

    // Also check focusSearch without modifier (if user rebound it)
    if (bindings.focusSearch.modifier !== 'ctrl') {
      add(bindings.focusSearch, configRef.current.onFocusSearch)
    }

    const handler = actionMap[pressedKey]
    if (handler) {
      event.preventDefault()
      handler()
    }
  }, [enabled])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}

export default usePatronKeyboardShortcuts
