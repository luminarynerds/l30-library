/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Printer, FileText, Clock, CheckCircle, AlertTriangle, ExternalLink } from 'lucide-react'
import api from '../api/api'
import { useAuth } from '../contexts/AuthContext'
import PageContainer from '@/components/layout/PageContainer'
import { getCurrentLocale } from '@/i18n'

interface PrintJob {
  id: number
  job_name: string
  job_uid: string
  status: string
  pages: number
  copies: number
  color_mode: string
  cost: number
  submitted_at: string
  release_code: string | null
}

type Tab = 'jobs' | 'guide'

const STATUS_STYLES: Record<string, string> = {
  queued: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  submitted: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  printing: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300',
  completed: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  held: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  failed: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  cancelled: 'bg-earth-100 text-earth-600 dark:bg-earth-800/30 dark:text-earth-400',
}

function statusStyle(status: string): string {
  return STATUS_STYLES[status] ?? 'bg-earth-100 text-earth-600 dark:bg-earth-800/30 dark:text-earth-400'
}

export default function MyPrintJobsPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('jobs')
  const [jobs, setJobs] = useState<PrintJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    let cancelled = false

    async function fetchJobs() {
      try {
        setLoading(true)
        const res = await api.get('/print/my-jobs')
        if (!cancelled) setJobs(res)
      } catch {
        if (!cancelled) setError('Could not load print jobs')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchJobs()
    const interval = setInterval(fetchJobs, 30000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [user])

  const tabs: { key: Tab; label: string; icon: typeof Printer }[] = [
    { key: 'jobs', label: 'My Print Jobs', icon: FileText },
    { key: 'guide', label: 'Print Guide', icon: Printer },
  ]

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Printer className="w-8 h-8 text-lsc-rose" />
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Printing</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">View your print jobs and printing information</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-lsc-rose text-lsc-rose'
                : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-earth-700 dark:hover:text-earth-200'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* My Print Jobs tab */}
      {tab === 'jobs' && (
        <div>
          {loading && (
            <div className="text-center py-12 text-earth-600 dark:text-earth-400">
              <Printer className="w-12 h-12 mx-auto mb-3 opacity-50 motion-safe:animate-pulse" />
              <p>Loading print jobs...</p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg text-sm text-status-danger-800 dark:text-status-danger-300 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              {error}
            </div>
          )}

          {!loading && !error && jobs.length === 0 && (
            <div className="text-center py-12 text-earth-600 dark:text-earth-400">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No print jobs yet</p>
              <p className="text-sm mt-1">Submit a print job from a library computer or upload a file to get started.</p>
            </div>
          )}

          {!loading && !error && jobs.length > 0 && (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 shadow-sm p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60 flex-shrink-0" />
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                          {job.job_name}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span>{job.pages} {job.pages === 1 ? 'page' : 'pages'}{job.copies > 1 ? ` x ${job.copies} copies` : ''}</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(job.submitted_at).toLocaleString(getCurrentLocale(), {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                          })}
                        </span>
                        {job.cost > 0 && (
                          <span>${job.cost.toFixed(2)}</span>
                        )}
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize whitespace-nowrap ${statusStyle(job.status)}`}>
                      {job.status}
                    </span>
                  </div>

                  {job.status === 'held' && job.release_code && (
                    <div className="mt-3 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg">
                      <p className="text-sm text-status-warning-800 dark:text-status-warning-300">
                        <span className="font-medium">Release code:</span>{' '}
                        <code className="font-mono text-base font-bold">{job.release_code}</code>
                      </p>
                      <p className="text-xs text-status-warning-700/80 dark:text-status-warning-400/80 mt-1">
                        Enter this code at a release station to print your job.
                      </p>
                    </div>
                  )}

                  {job.status === 'completed' && (
                    <div className="mt-2 flex items-center gap-1 text-sm text-status-success-700 dark:text-status-success-400">
                      <CheckCircle className="w-4 h-4" />
                      Printed successfully
                    </div>
                  )}

                  {job.status === 'failed' && (
                    <div className="mt-2 flex items-center gap-1 text-sm text-status-danger-700 dark:text-status-danger-400">
                      <AlertTriangle className="w-4 h-4" />
                      Print failed -- ask at the circulation desk for help.
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Print Guide tab */}
      {tab === 'guide' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 shadow-sm p-6">
          <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            How to Print at the Library
          </h2>
          <div className="space-y-4 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            <div>
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">From a Library Computer</h3>
              <p>Print from any application. Your job will appear in the "My Print Jobs" tab with a release code.</p>
            </div>
            <div>
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">From Your Device (Wireless)</h3>
              <p>Follow our wireless printing guide for step-by-step instructions on printing from your phone, tablet, or laptop.</p>
              <a
                href="/guides/wireless-printing"
                className="inline-flex items-center gap-1 mt-2 text-lsc-rose hover:underline font-medium"
              >
                <ExternalLink className="w-4 h-4" />
                Wireless Printing Guide
              </a>
            </div>
            <div>
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">Releasing Your Print Job</h3>
              <p>Once submitted, go to a print release station and enter your release code to start printing. Jobs are held for 24 hours before being automatically deleted.</p>
            </div>
            <div>
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">Pricing</h3>
              <p>Black &amp; white: $0.10/page. Color: $0.25/page. Double-sided printing saves paper and is enabled by default.</p>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  )
}
