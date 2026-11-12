/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { AlertTriangle } from 'lucide-react'
import type { ConflictData } from '../../hooks/useOptimisticLock'

interface ConflictWarningProps {
  conflictData: ConflictData
  onForceSave: () => void
  onReload: () => void
  onCancel: () => void
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

const ConflictWarning: React.FC<ConflictWarningProps> = ({
  conflictData,
  onForceSave,
  onReload,
  onCancel,
}) => {
  return (
    <div className="px-6 py-4 bg-status-warning-50 dark:bg-status-warning-900/20 border-b border-status-warning-200 dark:border-status-warning-800">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-status-warning-800 dark:text-status-warning-300">
            Concurrent Edit Detected
          </p>
          <p className="text-sm text-status-warning-700 dark:text-status-warning-400 mt-1">
            This item was modified by another user at{' '}
            {formatTime(conflictData.serverUpdatedAt)}.
            Your changes may overwrite theirs.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            <button
              type="button"
              onClick={onForceSave}
              className="px-3 py-1.5 text-sm font-medium bg-status-warning-600 hover:bg-status-warning-700 text-white rounded-lg transition-colors"
            >
              Save Anyway
            </button>
            <button
              type="button"
              onClick={onReload}
              className="px-3 py-1.5 text-sm font-medium bg-lsc-white dark:bg-earth-800 border border-status-warning-300 dark:border-status-warning-700 text-status-warning-800 dark:text-status-warning-300 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/30 rounded-lg transition-colors"
            >
              Reload &amp; Discard My Changes
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 text-sm font-medium text-status-warning-700 dark:text-status-warning-400 hover:underline"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ConflictWarning
