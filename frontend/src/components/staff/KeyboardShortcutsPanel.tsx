/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Navigation, Zap, Settings, RotateCcw, AlertTriangle } from 'lucide-react'
import { Modal } from '../ui/Modal'
import {
  FIXED_SHORTCUTS,
  type ShortcutAction,
  type ShortcutBindings,
} from '@/hooks/useKeyboardPreferences'

interface KeyboardShortcutsPanelProps {
  isOpen: boolean
  onClose: () => void
  bindings: ShortcutBindings
  onUpdateBinding: (action: ShortcutAction, key: string, modifier?: 'ctrl' | null) => void
  onResetToDefaults: () => void
  findConflict: (key: string, modifier: 'ctrl' | null | undefined, excludeAction: ShortcutAction) => ShortcutAction | null
  isDefault: boolean
}

const ACTION_ORDER: ShortcutAction[] = [
  'focusSearch',
  'showHelp',
  'editPatron',
  'blockToggle',
  'addNote',
  'quickCheckout',
  'quickCheckin',
  'renewAll',
  'printReceipt',
]

export default function KeyboardShortcutsPanel({
  isOpen,
  onClose,
  bindings,
  onUpdateBinding,
  onResetToDefaults,
  findConflict,
  isDefault,
}: KeyboardShortcutsPanelProps): React.ReactElement | null {
  const [editingAction, setEditingAction] = useState<ShortcutAction | null>(null)
  const [conflict, setConflict] = useState<{ action: ShortcutAction; with: ShortcutAction } | null>(null)

  if (!isOpen) return null

  const actionsByCategory = {
    general: ACTION_ORDER.filter(a => bindings[a].category === 'general'),
    actions: ACTION_ORDER.filter(a => bindings[a].category === 'actions'),
  }

  const handleKeyCapture = (e: React.KeyboardEvent, action: ShortcutAction) => {
    // Ignore modifier-only presses
    if (['Control', 'Meta', 'Shift', 'Alt'].includes(e.key)) return
    e.preventDefault()
    e.stopPropagation()

    // Block reserved keys
    const reserved = ['ArrowUp', 'ArrowDown', 'Enter', 'Escape', 'Tab']
    if (reserved.includes(e.key)) return

    const modifier = (e.ctrlKey || e.metaKey) ? 'ctrl' as const : null
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key

    // Check for conflict
    const conflictAction = findConflict(key, modifier, action)
    if (conflictAction) {
      setConflict({ action, with: conflictAction })
      // Still apply -- user can see the warning and undo
      onUpdateBinding(action, key, modifier)
      // Also clear the conflicting binding by swapping
      const oldBinding = bindings[action]
      onUpdateBinding(conflictAction, oldBinding.key, oldBinding.modifier)
      setEditingAction(null)
      return
    }

    setConflict(null)
    onUpdateBinding(action, key, modifier)
    setEditingAction(null)
  }

  const renderBinding = (action: ShortcutAction) => {
    const binding = bindings[action]
    const isEditing = editingAction === action

    return (
      <div
        key={action}
        className="flex items-center justify-between py-2.5"
      >
        <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
          {binding.description}
        </span>
        <div className="flex items-center gap-2">
          {isEditing ? (
            <input
              autoFocus
              readOnly
              className="w-28 px-2 py-1 text-xs font-mono text-center bg-lsc-rose/10 dark:bg-lsc-rose/20 border-2 border-lsc-rose rounded animate-pulse focus:outline-none"
              placeholder="Press key..."
              onKeyDown={(e) => handleKeyCapture(e, action)}
              onBlur={() => setEditingAction(null)}
            />
          ) : (
            <>
              <kbd className="px-2 py-1 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm min-w-[2rem] text-center">
                {binding.label}
              </kbd>
              <button
                onClick={() => { setEditingAction(action); setConflict(null) }}
                className="px-2 py-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/30 rounded transition-colors"
              >
                Edit
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => { setEditingAction(null); setConflict(null); onClose() }}
      title="Keyboard Shortcuts"
      size="lg"
      footer={
        !isDefault ? (
          <button
            onClick={() => { onResetToDefaults(); setConflict(null) }}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg transition-colors ml-auto"
          >
            <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
            Reset to Defaults
          </button>
        ) : undefined
      }
    >
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Click <strong>Edit</strong> then press a new key to rebind. Shortcuts are saved per user.
      </p>

      {/* Conflict warning */}
      {conflict && (
        <div className="flex items-start gap-2 p-3 mb-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-lg">
          <AlertTriangle className="w-4 h-4 text-status-warning-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
            Key conflict detected. The bindings for <strong>{bindings[conflict.action].description}</strong> and <strong>{bindings[conflict.with].description}</strong> have been swapped.
          </p>
        </div>
      )}

      <div className="space-y-6" style={{ maxHeight: 'calc(85vh - 250px)', overflowY: 'auto' }}>
        {/* Navigation (fixed) */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Navigation className="w-4 h-4 text-earth-600 dark:text-lsc-rose-light" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
              Navigation
            </h3>
            <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">(fixed)</span>
          </div>
          <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
            {FIXED_SHORTCUTS.map((s) => (
              <div key={s.key} className="flex items-center justify-between py-2.5">
                <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{s.description}</span>
                <kbd className="px-2 py-1 text-xs font-mono bg-lsc-cream dark:bg-lsc-brown rounded border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm">
                  {s.label}
                </kbd>
              </div>
            ))}
          </div>
        </div>

        {/* Actions (customizable) */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-status-warning-500 dark:text-status-warning-400" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
              Actions
            </h3>
          </div>
          <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
            {actionsByCategory.actions.map(renderBinding)}
          </div>
        </div>

        {/* General (customizable) */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Settings className="w-4 h-4 text-status-success-500 dark:text-status-success-400" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
              General
            </h3>
          </div>
          <div className="bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl p-4 divide-y divide-lsc-border/50 dark:divide-earth-600/50">
            {actionsByCategory.general.map(renderBinding)}
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
