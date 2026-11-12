/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Download, Database, Loader2, Trash2, Mail, ShieldCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import {
  getDataExportManifest,
  exportDataBundle,
  type ExportManifest,
  type TableCount,
} from '../api/domains/admin/admin-data-export-api'
import { useBranding } from '@/contexts/BrandingContext'

const MIN_PASSPHRASE_LENGTH = 12

function estimateExportSize(counts: TableCount[]): string {
  const totalRows = counts.reduce((sum, c) => sum + Math.max(0, c.rows), 0)
  const estimatedBytes = totalRows * 200
  if (estimatedBytes < 1024) return `${estimatedBytes} B`
  if (estimatedBytes < 1024 * 1024) return `${(estimatedBytes / 1024).toFixed(1)} KB`
  return `${(estimatedBytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatRowCount(counts: TableCount[]): string {
  return counts.reduce((sum, c) => sum + Math.max(0, c.rows), 0).toLocaleString()
}

export default function AdminDataExportPage(): React.ReactElement {
  const branding = useBranding()
  const [manifest, setManifest] = useState<ExportManifest | null>(null)
  const [loadingManifest, setLoadingManifest] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [ackWipe, setAckWipe] = useState(false)

  // Encrypted-bundle download controls
  const [showPassphrase, setShowPassphrase] = useState(false)
  const [passphrase, setPassphrase] = useState('')
  const [exportHash, setExportHash] = useState<string | null>(null)

  // Manifest display controls (client-side)
  const [tableFilter, setTableFilter] = useState('')
  const [sortByRows, setSortByRows] = useState(false)
  const [showEmpty, setShowEmpty] = useState(false)

  const fetchManifest = useCallback(async () => {
    setLoadingManifest(true)
    try {
      const data = await getDataExportManifest()
      setManifest(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to load export manifest')
    } finally {
      setLoadingManifest(false)
    }
  }, [])

  useEffect(() => {
    fetchManifest()
  }, [fetchManifest])

  const filteredCounts = useMemo(() => {
    if (!manifest) return []
    let counts = manifest.counts.filter(c =>
      c.table.toLowerCase().includes(tableFilter.toLowerCase())
    )
    if (!showEmpty) counts = counts.filter(c => c.rows > 0)
    if (sortByRows) counts = [...counts].sort((a, b) => b.rows - a.rows)
    return counts
  }, [manifest, tableFilter, sortByRows, showEmpty])

  const passphraseValid = passphrase.length >= MIN_PASSPHRASE_LENGTH

  const handleExport = useCallback(async () => {
    if (!passphraseValid) return
    setExporting(true)
    try {
      const { blob, sha256, filename } = await exportDataBundle(passphrase)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename || 'l30-export.zip'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      setExportHash(sha256)
      setShowPassphrase(false)
      setPassphrase('')
      toast.success('Encrypted export downloaded')
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }, [passphrase, passphraseValid])

  return (
    <AdminShell
      title="Data Export"
      subtitle="Back up your library data or prepare for migration"
      icon={<Download className="w-7 h-7 text-lsc-rose" />}
    >
      {/* Manifest */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden mb-6">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center gap-2">
          <Database className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Export manifest
          </h2>
          {manifest && (
            <span className="ml-2 text-xs px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full text-lsc-dark/70 dark:text-lsc-cream/70">
              ~{estimateExportSize(manifest.counts)}
            </span>
          )}
        </div>
        {loadingManifest ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : manifest ? (
          <div className="p-4 space-y-4">
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                {manifest.library_system_name}
              </span>{' '}
              <span className="font-mono text-xs">({manifest.library_system_code})</span>
            </div>

            {/* Search & filter controls */}
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Filter tables..."
                value={tableFilter}
                onChange={(e) => setTableFilter(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream"
                aria-label="Filter tables by name"
              />
              <div className="flex items-center gap-4 text-sm">
                <label className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                  <input type="checkbox" checked={sortByRows} onChange={(e) => setSortByRows(e.target.checked)} className="w-4 h-4 rounded" />
                  Sort by row count
                </label>
                <label className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                  <input type="checkbox" checked={showEmpty} onChange={(e) => setShowEmpty(e.target.checked)} className="w-4 h-4 rounded" />
                  Show empty tables
                </label>
              </div>
              <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                Showing {filteredCounts.length} of {manifest.counts.length} tables
              </div>
            </div>

            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60">
                  <th className="py-2">Table</th>
                  <th className="py-2 text-right">Rows</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {filteredCounts.map((c) => (
                  <tr key={c.table}>
                    <td className="py-2 font-mono text-lsc-dark dark:text-lsc-cream">{c.table}</td>
                    <td className="py-2 text-right text-lsc-dark dark:text-lsc-cream">
                      {c.rows < 0 ? '—' : c.rows.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {manifest.notes.length > 0 && (
              <ul className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 list-disc list-inside space-y-1">
                {manifest.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            No manifest available
          </div>
        )}
      </section>

      {/* Export */}
      <section className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 mb-6">
        {manifest && (
          <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 mb-4">
            Downloads a passphrase-encrypted ZIP archive of your library system &middot; estimated ~{estimateExportSize(manifest.counts)} &middot; {formatRowCount(manifest.counts)} total rows
          </p>
        )}

        {!showPassphrase ? (
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowPassphrase(true)}
              disabled={exporting}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              Download export
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label htmlFor="export-passphrase" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Encryption passphrase
              </label>
              <input
                id="export-passphrase"
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                autoComplete="new-password"
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream"
                aria-describedby="export-passphrase-help"
              />
              <p id="export-passphrase-help" className="mt-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                At least 12 characters. You&rsquo;ll need this to open the archive.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleExport}
                disabled={exporting || !passphraseValid}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {exporting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
                {exporting ? 'Encrypting…' : 'Encrypt & download'}
              </button>
              <button
                type="button"
                onClick={() => { setShowPassphrase(false); setPassphrase('') }}
                disabled={exporting}
                className="px-4 py-2 rounded-xl text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {exportHash && (
          <div className="mt-4 rounded-xl border border-lsc-rose/40 bg-lsc-cream dark:bg-earth-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Save this passphrase and hash</h3>
            </div>
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-3">
              Save this passphrase and SHA-256 hash. The passphrase is required to open the archive (use Keka or 7-Zip on macOS). The hash is required to request a data wipe.
            </p>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">SHA-256</div>
            <code className="block break-all font-mono text-xs text-lsc-dark dark:text-lsc-cream bg-lsc-white dark:bg-earth-800 rounded-lg px-3 py-2">
              {exportHash}
            </code>
          </div>
        )}
      </section>

      {/* Wipe section -- collapsed */}
      <details className="mb-6">
        <summary className="flex items-center gap-2 cursor-pointer text-sm text-status-danger-600 dark:text-status-danger-400 font-medium py-2">
          <Trash2 className="w-4 h-4" />
          Planning to leave? Request a data wipe
        </summary>
        <div className="mt-2 rounded-xl border border-status-danger-300 dark:border-status-danger-800 bg-status-danger-50 dark:bg-status-danger-900/20 p-4">
          <div className="text-sm text-status-danger-900 dark:text-status-danger-200">
            <p className="mb-3">
              Download and verify the archive above, then email{' '}
              <a href={`mailto:${branding.contact_email}`} className="underline font-medium">{branding.contact_email}</a>{' '}
              from an admin account to request permanent deletion of this library system. Deletion is irreversible and runs after a 7-day cooling-off period.
            </p>
            <label className="flex items-start gap-3 cursor-pointer mb-4">
              <input type="checkbox" checked={ackWipe} onChange={(e) => setAckWipe(e.target.checked)} className="mt-1" />
              <span>I have verified my export and would like to request a data wipe.</span>
            </label>
            {ackWipe && (
              <a href={`mailto:${branding.contact_email}?subject=Data%20Wipe%20Request`} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-status-danger-600 text-white font-medium hover:bg-status-danger-700 transition-colors text-sm">
                <Mail aria-hidden="true" className="w-4 h-4" />
                Request Data Wipe
              </a>
            )}
          </div>
        </div>
      </details>
    </AdminShell>
  )
}
