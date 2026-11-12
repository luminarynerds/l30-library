/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, Trash2, Loader2 } from "lucide-react"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface DeletingItem {
  type: "tag" | "group"
  id: number
  name: string
}

interface Props {
  deletingItem: DeletingItem
  isDeleting: boolean
  onConfirm: () => void
  onClose: () => void
}

export function DeleteConfirmModal({ deletingItem, isDeleting, onConfirm, onClose }: Props) {
  return (
    <ModalBackdrop onClose={onClose} title={`Delete ${deletingItem.type === "tag" ? "Tag" : "Group"}`} role="alertdialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Delete {deletingItem.type === "tag" ? "Tag" : "Group"}
          </h3>
        </div>
        <div className="p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-status-danger-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-lsc-dark dark:text-lsc-cream">
                Are you sure you want to delete "{deletingItem.name}"?
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                This action cannot be undone.
              </p>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex items-center gap-2 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors disabled:opacity-50"
          >
            {isDeleting && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
