/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Print Job Queue
 *
 * Displays a list of print jobs in the queue with status indicators.
 * Highlights ready jobs and shows pending jobs that are being processed.
 * Designed for the right-side panel in kiosk layout with live updates.
 */

import { useMemo } from 'react'
import PrintJobStatusBadge from './PrintJobStatusBadge'
import type { PrintJob } from '../../hooks/usePrintQueue'
import { useTranslation } from '@/i18n'

// ==================== Types ====================

interface PrintJobQueueProps {
  /** Array of print jobs to display */
  jobs: PrintJob[]
  /** Currently selected job ID */
  selectedJobId?: number
  /** Callback when a job is selected */
  onSelectJob?: (jobId: number) => void
  /** Whether the queue is loading */
  isLoading?: boolean
  /** Optional CSS class name */
  className?: string
}

// ==================== Component ====================

export default function PrintJobQueue({
  jobs,
  selectedJobId,
  onSelectJob,
  isLoading = false,
  className = '',
}: PrintJobQueueProps) {
  const { t } = useTranslation()
  // Group jobs by status for better organization
  const groupedJobs = useMemo(() => {
    const groups: Record<string, PrintJob[]> = {
      ready: [],
      pending: [],
      released: [],
      failed: [],
    }

    jobs.forEach((job) => {
      if (job.status in groups) {
        groups[job.status as keyof typeof groups]?.push(job)
      }
    })

    return groups
  }, [jobs])

  // Sort jobs within each group (most recent first)
  const sortedGroups = useMemo(() => {
    const sorted: Record<'ready' | 'pending' | 'released' | 'failed', PrintJob[]> = {
      ready: [],
      pending: [],
      released: [],
      failed: [],
    }
    Object.entries(groupedJobs).forEach(([status, jobList]) => {
      const sortedList = jobList.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      sorted[status as keyof typeof sorted] = sortedList
    })
    return sorted
  }, [groupedJobs])

  if (isLoading && jobs.length === 0) {
    return (
      <div
        className={`flex items-center justify-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`}
      >
        <p>Loading queue...</p>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`}
      >
        <p className="text-lg font-semibold">No print jobs</p>
        <p className="text-sm">{t('components.print.printJobQueue.theQueueIsEmpty')}</p>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Ready Jobs Section */}
      {sortedGroups.ready.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 px-2">
            Ready for Pickup ({sortedGroups.ready.length})
          </h3>
          <div className="space-y-2">
            {sortedGroups.ready.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                {...(onSelectJob !== undefined ? { onSelect: onSelectJob } : {})}
              />
            ))}
          </div>
        </div>
      )}

      {/* Pending Jobs Section */}
      {sortedGroups.pending.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 px-2">
            Processing ({sortedGroups.pending.length})
          </h3>
          <div className="space-y-2">
            {sortedGroups.pending.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                {...(onSelectJob !== undefined ? { onSelect: onSelectJob } : {})}
              />
            ))}
          </div>
        </div>
      )}

      {/* Released Jobs Section */}
      {sortedGroups.released.length > 0 && (
        <div className="opacity-60">
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 px-2">
            Released ({sortedGroups.released.length})
          </h3>
          <div className="space-y-2">
            {sortedGroups.released.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                {...(onSelectJob !== undefined ? { onSelect: onSelectJob } : {})}
              />
            ))}
          </div>
        </div>
      )}

      {/* Failed Jobs Section */}
      {sortedGroups.failed.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 px-2">
            Failed ({sortedGroups.failed.length})
          </h3>
          <div className="space-y-2">
            {sortedGroups.failed.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isSelected={selectedJobId === job.id}
                {...(onSelectJob !== undefined ? { onSelect: onSelectJob } : {})}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ==================== Job Card Subcomponent ====================

interface JobCardProps {
  job: PrintJob
  isSelected: boolean
  onSelect?: (jobId: number) => void
}

function JobCard({ job, isSelected, onSelect }: JobCardProps) {
  return (
    <button
      onClick={() => onSelect?.(job.id)}
      className={`w-full text-left p-3 rounded-lg border-2 transition-all ${
        isSelected
          ? 'border-lsc-rose/50 bg-earth-50 dark:bg-earth-800/20'
          : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-border dark:hover:border-earth-500'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-earth-800 dark:text-earth-100 truncate" title={job.job_name}>
            {job.job_name}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Code: <span className="font-mono font-bold">{job.release_code}</span>
          </p>
        </div>
        <PrintJobStatusBadge status={job.status} size="sm" />
      </div>
      <div className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span>
          {job.pages} {job.pages === 1 ? 'page' : 'pages'} × {job.copies}{' '}
          {job.copies === 1 ? 'copy' : 'copies'}
        </span>
        <span className="font-semibold text-earth-800 dark:text-earth-100">${job.cost.toFixed(2)}</span>
      </div>
    </button>
  )
}
