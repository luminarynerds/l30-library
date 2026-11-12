/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { X, Pencil, Trash2, Check } from 'lucide-react'
import { t } from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface TagManagerProps {
  tags: string[]
  open: boolean
  onClose: () => void
  onRename: (oldName: string, newName: string) => void
  onDelete: (tagName: string) => void
}

export default function TagManager({ tags, open, onClose, onRename, onDelete }: TagManagerProps) {
  const [editingTag, setEditingTag] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  if (!open) return null

  const startEdit = (tag: string) => {
    setEditingTag(tag)
    setEditValue(tag)
    setConfirmDelete(null)
  }

  const submitEdit = () => {
    if (editingTag && editValue.trim() && editValue.trim() !== editingTag) {
      onRename(editingTag, editValue.trim())
    }
    setEditingTag(null)
    setEditValue('')
  }

  const handleDeleteConfirm = (tag: string) => {
    onDelete(tag)
    setConfirmDelete(null)
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 z-50" onClick={onClose} aria-hidden="true" />

      {/* Panel */}
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      <div
        role="dialog"
        aria-label={t('aria.shelf.manageTags')}
        className="fixed bottom-0 left-0 right-0 z-50 bg-lsc-white dark:bg-earth-800 rounded-t-2xl shadow-lg max-h-[70vh] overflow-y-auto sm:max-w-md sm:mx-auto sm:bottom-8 sm:rounded-xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-lsc-border/40 dark:border-earth-700/60">
          <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream">
            Manage Tags
          </h2>
          <button
            onClick={onClose}
            aria-label={t('aria.shelf.closeTagManager')}
            className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-4">
          {tags.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 text-center py-4">
              No tags yet. Add tags to your books to organize your shelf.
            </p>
          ) : (
            <ul className="space-y-2">
              {tags.map((tag) => (
                <li
                  key={tag}
                  className="flex items-center gap-2 py-2 px-3 rounded-xl bg-earth-50 dark:bg-earth-900/50"
                >
                  {editingTag === tag ? (
                    <>
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        maxLength={30}
                        autoFocus
                        onKeyDown={(e) => { if (e.key === 'Enter') submitEdit(); if (e.key === 'Escape') setEditingTag(null) }}
                        className="flex-1 text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-2 py-1 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
                      />
                      <button
                        onClick={submitEdit}
                        aria-label={t('aria.shelf.saveTagName')}
                        className="text-emerald-600 dark:text-emerald-400 hover:text-emerald-700"
                      >
                        <Check className="w-4 h-4" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => setEditingTag(null)}
                        aria-label={t('aria.shelf.cancelEditing')}
                        className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
                      >
                        <X className="w-4 h-4" aria-hidden="true" />
                      </button>
                    </>
                  ) : confirmDelete === tag ? (
                    <>
                      <span className="flex-1 text-sm text-status-danger-600 dark:text-status-danger-400">
                        Delete &quot;{tag}&quot;?
                      </span>
                      <button
                        onClick={() => handleDeleteConfirm(tag)}
                        className="text-xs font-medium px-2 py-1 rounded bg-status-danger-500 text-white hover:bg-status-danger-600 transition-colors"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
                      >
                        No
                      </button>
                    </>
                  ) : (
                    <>
                      <span className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream">
                        {tag}
                      </span>
                      <button
                        onClick={() => startEdit(tag)}
                        aria-label={`Rename tag ${tag}`}
                        className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                      >
                        <Pencil className="w-3.5 h-3.5" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() => setConfirmDelete(tag)}
                        aria-label={`Delete tag ${tag}`}
                        className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-500 dark:hover:text-status-danger-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      </FocusTrap>
    </>
  )
}
