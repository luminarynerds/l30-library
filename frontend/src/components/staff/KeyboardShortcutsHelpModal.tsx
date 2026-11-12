/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * KeyboardShortcutsHelpModal Component
 *
 * Read-only modal displaying available keyboard shortcuts for the patron management page.
 * Organized by category for easy reference.
 * For the customizable version, see KeyboardShortcutsPanel.
 */

import { Navigation, Zap, Settings } from 'lucide-react'
import {
  DEFAULT_BINDINGS,
  FIXED_SHORTCUTS,
  type ShortcutBinding,
} from '@/hooks/useKeyboardPreferences'
import { Modal } from '../ui/Modal'

// ==================== Types ====================

interface KeyboardShortcutsHelpModalProps {
  isOpen: boolean
  onClose: () => void
}

// ==================== Component ====================

export default function KeyboardShortcutsHelpModal({
  isOpen,
  onClose,
}: KeyboardShortcutsHelpModalProps): React.ReactElement | null {
  if (!isOpen) return null

  const allBindings = Object.values(DEFAULT_BINDINGS)
  const actionShortcuts = allBindings.filter(s => s.category === 'actions')
  const generalShortcuts = allBindings.filter(s => s.category === 'general')

  const renderShortcut = (shortcut: ShortcutBinding | typeof FIXED_SHORTCUTS[number]) => (
    <div
      key={shortcut.key}
      className="flex items-center justify-between py-2"
    >
      <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
        {shortcut.description}
      </span>
      <kbd className="px-2 py-1 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm">
        {shortcut.label}
      </kbd>
    </div>
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Keyboard Shortcuts"
      size="lg"
    >
      {/* Subtitle */}
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Quick actions for patron management
      </p>

      {/* Content */}
      <div className="space-y-6" style={{maxHeight: 'calc(85vh - 200px)', overflowY: 'auto'}}>
              {/* Navigation Shortcuts */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Navigation className="w-4 h-4 text-earth-600 dark:text-lsc-rose-light" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
                    Navigation
                  </h3>
                </div>
                <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
                  {FIXED_SHORTCUTS.map(renderShortcut)}
                </div>
              </div>

              {/* Action Shortcuts */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Zap className="w-4 h-4 text-status-warning-500 dark:text-status-warning-400" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
                    Actions
                  </h3>
                </div>
                <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
                  {actionShortcuts.map(renderShortcut)}
                </div>
              </div>

              {/* General Shortcuts */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <Settings className="w-4 h-4 text-status-success-500 dark:text-status-success-400" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
                    General
                  </h3>
                </div>
                <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
                  {generalShortcuts.map(renderShortcut)}
                </div>
              </div>

              {/* Tip */}
              <div className="p-4 bg-earth-50 dark:bg-earth-800/20 rounded-xl border border-lsc-border dark:border-earth-700">
                <p className="text-sm text-earth-800 dark:text-lsc-rose-light/80">
                  <strong>Tip:</strong> Shortcuts only work when not typing in an input field.
                  Press <kbd className="px-1.5 py-0.5 mx-0.5 text-xs font-mono bg-earth-100 dark:bg-earth-800 rounded">Escape</kbd> to
                  unfocus inputs and enable shortcuts.
                </p>
              </div>
      </div>
    </Modal>
  )
}
