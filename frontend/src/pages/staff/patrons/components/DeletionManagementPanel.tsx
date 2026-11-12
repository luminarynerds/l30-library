/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle } from "lucide-react"

interface DeletionManagementPanelProps {
  patronId: number
  onInitiateDeletion: () => void
}

export function DeletionManagementPanel({ patronId, onInitiateDeletion }: DeletionManagementPanelProps) {
  return (
    <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <AlertTriangle className="w-5 h-5 text-status-danger-500" />
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">Account Deletion</h3>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Permanently delete patron account (ID: {patronId})
      </p>
      <button
        onClick={onInitiateDeletion}
        className="px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700"
      >
        Initiate Deletion
      </button>
    </div>
  )
}
