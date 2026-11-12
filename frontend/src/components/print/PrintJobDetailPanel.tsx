/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Print Job Detail Panel
 *
 * Shows detailed information about a selected print job and provides
 * a button to release it for pickup. Used in the left side of the kiosk layout.
 */

import { useState } from 'react'
import api from '../../api/api'
import PrintJobStatusBadge from './PrintJobStatusBadge'
import type { PrintJob } from '../../hooks/usePrintQueue'
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'

// ==================== Types ====================

interface PrintJobDetailPanelProps {
  /** The print job to display */
  job: PrintJob | null
  /** Callback when release succeeds */
  onReleaseSuccess?: () => void
  /** Callback when close is requested */
  onClose?: () => void
  /** Optional CSS class name */
  className?: string
}

// ==================== Component ====================

export default function PrintJobDetailPanel({
  job,
  onReleaseSuccess,
  onClose,
  className = '',
}: PrintJobDetailPanelProps) {
  const { t } = useTranslation()
  const [isReleasing, setIsReleasing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleRelease = async () => {
    if (!job) return

    setError(null)
    setSuccess(null)
    setIsReleasing(true)

    try {
      await api.post(`${API_BASE}/print/release`, {
        job_id: job.id,
      })

      setSuccess('Print job released successfully!')

      setTimeout(() => {
        onReleaseSuccess?.()
      }, 1500)
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to release print job'
      setError(errorMessage)
    } finally {
      setIsReleasing(false)
    }
  }

  if (!job) {
    return (
      <div
        className={`flex flex-col items-center justify-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`}
      >
        <p className="text-lg font-semibold">No job selected</p>
        <p className="text-sm">{t('components.print.printJobDetailPanel.selectAJobFromThe')}</p>
      </div>
    )
  }

  const totalPages = job.pages * job.copies
  const isReadyForRelease = job.status === 'ready'
  const isAlreadyReleased = job.status === 'released'
  const isFailed = job.status === 'failed'

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-earth-800 dark:text-earth-100">Job Details</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800 dark:hover:text-earth-100 text-xl"
          >
            ✕
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-status-danger-100 dark:bg-status-danger-900/30 border border-status-danger-400 text-status-danger-700 dark:text-status-danger-300 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Success Alert */}
      {success && (
        <div className="bg-status-success-100 dark:bg-status-success-900/30 border border-status-success-400 text-status-success-700 dark:text-status-success-300 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      {/* Job Details Card */}
      <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-6 mb-6 flex-1 min-h-0 overflow-y-auto">
        {/* Status */}
        <div className="mb-6">
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Status</p>
          <PrintJobStatusBadge status={job.status} size="lg" />
        </div>

        {/* Release Code */}
        <div className="mb-6 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
          <p className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light mb-1">Release Code</p>
          <p className="font-mono text-2xl font-bold text-earth-900 dark:text-earth-200 text-center">
            {job.release_code}
          </p>
          <p className="text-xs text-lsc-rose dark:text-lsc-rose-light text-center mt-2">
            Use this code to release your prints
          </p>
        </div>

        {/* Job Name */}
        <div className="mb-4">
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Job Name</p>
          <p className="text-lg font-semibold text-earth-800 dark:text-earth-100">{job.job_name}</p>
        </div>

        {/* Pages and Copies */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Pages</p>
            <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{job.pages}</p>
          </div>
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Copies</p>
            <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{job.copies}</p>
          </div>
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total</p>
            <p className="text-2xl font-bold text-earth-800 dark:text-earth-100">{totalPages}</p>
          </div>
        </div>

        {/* Cost */}
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4 mb-4">
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Cost</p>
          <p className="text-3xl font-bold text-status-success-700 dark:text-status-success-300">
            ${job.cost.toFixed(2)}
          </p>
        </div>

        {/* Timestamps */}
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-2">
          <div>
            <p className="font-medium">Created:</p>
            <p>{new Date(job.created_at).toLocaleString()}</p>
          </div>
          {job.released_at && (
            <div>
              <p className="font-medium">Released:</p>
              <p>{new Date(job.released_at).toLocaleString()}</p>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-3">
        {isReadyForRelease && (
          <button
            onClick={handleRelease}
            disabled={isReleasing}
            className="w-full px-6 py-4 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 disabled:bg-earth-400 font-bold text-lg transition-colors"
          >
            {isReleasing ? 'Releasing...' : 'Release Print Job'}
          </button>
        )}

        {isAlreadyReleased && (
          <div className="w-full px-6 py-4 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 text-lsc-rose dark:text-lsc-rose-light rounded-lg text-center font-semibold">
            Job already released
          </div>
        )}

        {isFailed && (
          <div className="w-full px-6 py-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-center font-semibold">
            Job failed - contact staff
          </div>
        )}

        {job.status === 'pending' && (
          <div className="w-full px-6 py-4 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 text-status-warning-700 dark:text-status-warning-300 rounded-lg text-center font-semibold">
            Still processing... please wait
          </div>
        )}
      </div>
    </div>
  )
}