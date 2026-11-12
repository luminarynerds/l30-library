/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Download, FileDown, FileText, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useQuery } from '@tanstack/react-query'
import { AdminShell } from '../../components/shells/AdminShell'
import {
  downloadMarcExportJob,
  exportMarcNow,
  listMarcExportJobs,
  type MarcBatchJobResponse,
  type MarcExportFormat,
} from '../../api/domains/catalog/marc-export-api'

type ScopeMode = 'all' | 'since' | 'single'

const ITEM_TYPES: Array<{ value: string; label: string }> = [
  { value: '', label: 'All types' },
  { value: 'book', label: 'Book' },
  { value: 'ebook', label: 'E-book' },
  { value: 'audiobook', label: 'Audiobook' },
  { value: 'dvd', label: 'DVD' },
  { value: 'cd', label: 'CD' },
  { value: 'periodical', label: 'Periodical' },
  { value: 'other', label: 'Other' },
]

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function extensionFor(format: MarcExportFormat): string {
  return format === 'marcxml' ? 'xml' : 'mrc'
}

function timestampSlug(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}` +
    `-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  )
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function StatusPill({ status }: { status: string }) {
  const ok = status === 'completed' || status === 'success'
  const fail = status === 'failed' || status === 'error'
  const cls = ok
    ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    : fail
      ? 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
      : 'bg-lsc-cream text-lsc-dark dark:bg-earth-700 dark:text-lsc-cream'
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{status}</span>
  )
}

export default function ExportMarcPage(): React.ReactElement {
  const [format, setFormat] = useState<MarcExportFormat>('marc21')
  const [scope, setScope] = useState<ScopeMode>('all')
  const [sinceDate, setSinceDate] = useState<string>('')
  const [singleId, setSingleId] = useState<string>('')
  const [itemType, setItemType] = useState<string>('')
  const [downloading, setDownloading] = useState(false)

  const jobsQuery = useQuery({
    queryKey: ['marc-export-jobs'],
    queryFn: () => listMarcExportJobs(10),
    staleTime: 30 * 1000,
  })

  const onDownload = async () => {
    if (scope === 'since' && !sinceDate) {
      toast.error('Please pick a "modified since" date.')
      return
    }
    if (scope === 'single') {
      const id = Number(singleId)
      if (!Number.isInteger(id) || id <= 0) {
        toast.error('Please enter a valid catalog item ID.')
        return
      }
    }

    setDownloading(true)
    try {
      const params: Parameters<typeof exportMarcNow>[0] = { format }
      if (itemType) params.item_type = itemType
      if (scope === 'since') {
        params.incremental_since = new Date(sinceDate).toISOString()
      } else if (scope === 'single') {
        params.catalog_item_id = Number(singleId)
      }
      const blob = await exportMarcNow(params)
      const filename = `l30-export-${timestampSlug()}.${extensionFor(format)}`
      triggerBlobDownload(blob, filename)
      toast.success('Export downloaded')
      void jobsQuery.refetch()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Export failed')
    } finally {
      setDownloading(false)
    }
  }

  const onDownloadJob = async (job: MarcBatchJobResponse) => {
    try {
      const blob = await downloadMarcExportJob(job.id)
      const fallbackExt = job.file_format === 'marcxml' ? 'xml' : 'mrc'
      const filename = job.file_name || `l30-export-${job.id}.${fallbackExt}`
      triggerBlobDownload(blob, filename)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Download failed')
    }
  }

  const jobs = jobsQuery.data?.items ?? []

  return (
    <AdminShell
      title="Export MARC"
      subtitle="Download catalog records as MARC21 or MARCXML."
      icon={<FileDown className="w-7 h-7 text-lsc-rose" />}
    >
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 space-y-5">
        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Records to export</legend>
          <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
            <input type="radio" name="scope" value="all" checked={scope === 'all'} onChange={() => setScope('all')} />
            All records
          </label>
          <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
            <input type="radio" name="scope" value="since" checked={scope === 'since'} onChange={() => setScope('since')} />
            Records modified since…
          </label>
          {scope === 'since' && (
            <input
              type="date"
              value={sinceDate}
              onChange={(e) => setSinceDate(e.target.value)}
              className="ml-6 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          )}
          <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
            <input type="radio" name="scope" value="single" checked={scope === 'single'} onChange={() => setScope('single')} />
            Single record by ID
          </label>
          {scope === 'single' && (
            <input
              type="number"
              min={1}
              value={singleId}
              onChange={(e) => setSingleId(e.target.value)}
              placeholder="Catalog item ID"
              className="ml-6 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          )}
        </fieldset>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="block">
            <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Item type</span>
            <select
              value={itemType}
              onChange={(e) => setItemType(e.target.value)}
              disabled={scope === 'single'}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
            >
              {ITEM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </label>
          <fieldset>
            <span className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Format</span>
            <div className="flex gap-4 pt-2">
              <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
                <input type="radio" name="format" value="marc21" checked={format === 'marc21'} onChange={() => setFormat('marc21')} />
                MARC21 (.mrc)
              </label>
              <label className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
                <input type="radio" name="format" value="marcxml" checked={format === 'marcxml'} onChange={() => setFormat('marcxml')} />
                MARCXML
              </label>
            </div>
          </fieldset>
        </div>

        <div className="flex justify-end">
          <button
            onClick={onDownload}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {downloading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
            {downloading ? 'Preparing…' : 'Download'}
          </button>
        </div>
      </div>

      <div className="mt-8">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-5 h-5 text-lsc-rose" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Recent exports</h2>
        </div>
        {jobsQuery.isLoading ? (
          <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Loading…
          </div>
        ) : jobs.length === 0 ? (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">No export jobs yet.</p>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-lsc-cream dark:bg-earth-900 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <tr>
                  <th scope="col" className="px-4 py-2">Created</th>
                  <th scope="col" className="px-4 py-2">Format</th>
                  <th scope="col" className="px-4 py-2">Records</th>
                  <th scope="col" className="px-4 py-2">Status</th>
                  <th scope="col" className="px-4 py-2 text-right">Download</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-t border-lsc-border dark:border-earth-700">
                    <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">{formatDate(job.created_at)}</td>
                    <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">{job.file_format || '—'}</td>
                    <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">{job.total_records}</td>
                    <td className="px-4 py-3"><StatusPill status={job.status} /></td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => onDownloadJob(job)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                        aria-label={`Download export ${job.id}`}
                      >
                        <Download className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
