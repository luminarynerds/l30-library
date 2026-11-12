/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SearchLoadingState Component
 *
 * Displays loading progress with per-source status indicators
 * while federated search is executing
 */

import React, { useMemo } from 'react'
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import type { SourceSearchStatus } from '../types/federated-search.types'
import { t } from '@/i18n'

// ==================== Types ====================

interface SearchLoadingStateProps {
  /** Per-source search status */
  sourceStatus: SourceSearchStatus[]
  /** Overall search status */
  status: 'idle' | 'searching' | 'success' | 'error' | 'cancelled'
  /** Time elapsed in milliseconds */
  elapsedTimeMs?: number
  /** CSS class name */
  className?: string
}

// ==================== Component ====================

export function SearchLoadingState({
  sourceStatus,
  status,
  elapsedTimeMs = 0,
  className,
}: SearchLoadingStateProps): React.ReactElement {
  const loadingCount = useMemo(() => sourceStatus.filter(s => s.status === 'loading' || s.status === 'pending').length, [sourceStatus])

  const successCount = useMemo(() => sourceStatus.filter(s => s.status === 'success').length, [sourceStatus])

  const errorCount = useMemo(() => sourceStatus.filter(s => s.status === 'error').length, [sourceStatus])

  const progressPercentage = useMemo(() => {
    if (sourceStatus.length === 0) return 0
    return Math.round(((successCount + errorCount) / sourceStatus.length) * 100)
  }, [sourceStatus, successCount, errorCount])

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          {status === 'searching' && (
            <>
              <Loader2 className="w-4 h-4 motion-safe:animate-spin motion-safe:animate-spin" aria-hidden="true" />
              <span>Searching {sourceStatus.length} sources...</span>
            </>
          )}
          {status === 'success' && (
            <>
              <CheckCircle2 className="w-4 h-4 text-status-success-600" aria-hidden="true" />
              <span>Search complete</span>
            </>
          )}
          {status === 'error' && (
            <>
              <AlertCircle className="w-4 h-4 text-status-danger-600" aria-hidden="true" />
              <span>Search error</span>
            </>
          )}
          {status === 'cancelled' && (
            <>
              <Clock className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              <span>Search cancelled</span>
            </>
          )}
        </h3>

        {/* Time Elapsed */}
        {elapsedTimeMs > 0 && (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70" aria-label={`Search time: ${formatTime(elapsedTimeMs)}`}>
            {formatTime(elapsedTimeMs)}
          </span>
        )}
      </div>

      {/* Progress Bar */}
      {status === 'searching' && (
        <div
          className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-2 overflow-hidden"
          role="progressbar"
          aria-valuenow={progressPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Search progress: ${progressPercentage}% complete`}
        >
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 motion-safe:transition-all motion-safe:duration-300"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      )}

      {/* Summary Stats */}
      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
        <div className="flex justify-between">
          <span>Sources:</span>
          <span>
            <span className="text-status-success-600 dark:text-status-success-400 font-medium">{successCount}</span> completed,{' '}
            <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">{loadingCount}</span> loading,{' '}
            <span className="text-status-danger-600 dark:text-status-danger-400 font-medium">{errorCount}</span> failed
          </span>
        </div>
      </div>

      {/* Per-Source Status List */}
      <div
        className="space-y-2"
        role="region"
        aria-label={t('aria.federated-search.searchSourceStatus')}
        aria-live="polite"
        aria-atomic="false"
      >
        {sourceStatus.map((source) => (
          <SourceStatusItem key={source.source} source={source} />
        ))}
      </div>

      {/* Additional Messages */}
      {status === 'searching' && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 italic">
          Searching across multiple sources. Results will appear as they arrive.
        </p>
      )}

      {status === 'error' && errorCount > 0 && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-3">
          <p className="text-xs text-status-danger-700 dark:text-status-danger-300">
            Some sources failed to respond. Showing results from available sources.
          </p>
        </div>
      )}

      {status === 'cancelled' && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-3">
          <p className="text-xs text-status-warning-700 dark:text-status-warning-300">
            Search was cancelled. Partial results may be displayed.
          </p>
        </div>
      )}
    </div>
  )
}

// ==================== Subcomponents ====================

function SourceStatusItem({ source }: { source: SourceSearchStatus }): React.ReactElement {
  const statusIcon = getStatusIcon(source.status)
  const statusColor = getStatusColor(source.status)

  return (
    <div className="flex items-center gap-3 p-2 rounded-lg bg-earth-50 dark:bg-earth-800/50">
      {/* Status Icon */}
      <div className={clsx('flex-shrink-0', statusColor.icon)}>
        {statusIcon}
      </div>

      {/* Source Name */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {formatSourceName(source.source)}
        </div>
        {source.status === 'error' && source.error && (
          <div className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-0.5">{source.error}</div>
        )}
      </div>

      {/* Status Label and Time */}
      <div className="flex-shrink-0 text-right">
        <div className={clsx('text-xs font-medium', statusColor.text)}>
          {source.status === 'loading' && 'Loading...'}
          {source.status === 'pending' && 'Pending...'}
          {source.status === 'success' && 'Done'}
          {source.status === 'error' && 'Failed'}
          {source.status === 'cancelled' && 'Cancelled'}
        </div>
        {source.timeMs && (
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
            {(source.timeMs / 1000).toFixed(1)}s
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== Utility Functions ====================

function getStatusIcon(status: SourceSearchStatus['status']): React.ReactElement {
  switch (status) {
    case 'pending':
    case 'loading':
      return <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
    case 'success':
      return <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
    case 'error':
      return <AlertCircle className="w-4 h-4" aria-hidden="true" />
    case 'cancelled':
      return <Clock className="w-4 h-4" aria-hidden="true" />
    default:
      return <Clock className="w-4 h-4" aria-hidden="true" />
  }
}

function getStatusColor(status: SourceSearchStatus['status']): {
  icon: string
  text: string
} {
  switch (status) {
    case 'pending':
    case 'loading':
      return { icon: 'text-earth-600', text: 'text-lsc-rose dark:text-lsc-rose-light' }
    case 'success':
      return { icon: 'text-status-success-600', text: 'text-status-success-600 dark:text-status-success-400' }
    case 'error':
      return { icon: 'text-status-danger-600', text: 'text-status-danger-600 dark:text-status-danger-400' }
    case 'cancelled':
      return { icon: 'text-earth-600', text: 'text-lsc-dark/70 dark:text-lsc-cream/70' }
    default:
      return { icon: 'text-earth-600', text: 'text-lsc-dark/70 dark:text-lsc-cream/70' }
  }
}

function formatSourceName(source: string): string {
  const names: Record<string, string> = {
    'local-catalog': 'Local Catalog',
    'open-library': 'Open Library',
    'google-books': 'Google Books',
    'worldcat': 'WorldCat',
    'isbn-search': 'ISBN Search',
  }
  return names[source] || source
}

function formatTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = (ms / 1000).toFixed(1)
  return `${seconds}s`
}

export default SearchLoadingState
