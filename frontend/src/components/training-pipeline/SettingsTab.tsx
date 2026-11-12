/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  Loader, Download, Play, Trash2, Shield, Zap,
} from 'lucide-react'
import {
  getRetentionStats, triggerBatchProcessing,
  triggerRetentionCleanup, exportTrainingData,
} from '../../api/training-pipeline-api'
import type { RetentionStats } from '../../api/training-pipeline-api'
import { t } from '@/i18n'

export function SettingsTab() {
  const [retention, setRetention] = useState<RetentionStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState('')
  const [exportDomain, setExportDomain] = useState('shared')
  const [batchDomain, setBatchDomain] = useState('')

  useEffect(() => {
    getRetentionStats().then(setRetention).catch(console.error).finally(() => setLoading(false))
  }, [])

  async function handleBatchProcess() {
    setActionMsg('Processing...')
    try {
      await triggerBatchProcessing(batchDomain || undefined)
      setActionMsg('Batch processing queued.')
    } catch { setActionMsg('Failed to start batch processing.') }
    setTimeout(() => setActionMsg(''), 3000)
  }

  async function handleRetentionCleanup() {
    setActionMsg('Running cleanup...')
    try {
      await triggerRetentionCleanup()
      setActionMsg('Retention cleanup queued.')
    } catch { setActionMsg('Cleanup failed.') }
    setTimeout(() => setActionMsg(''), 3000)
  }

  async function handleExport() {
    setActionMsg('Exporting...')
    try {
      const result = await exportTrainingData(exportDomain)
      const blob = new Blob([result.jsonl], { type: 'application/jsonl' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `training-${exportDomain}-${result.example_count}examples.jsonl`
      a.click()
      URL.revokeObjectURL(url)
      setActionMsg(`Exported ${result.example_count} examples.`)
    } catch { setActionMsg('Export failed.') }
    setTimeout(() => setActionMsg(''), 3000)
  }

  if (loading) return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>

  return (
    <div className="space-y-6">
      {actionMsg && (
        <div className="px-4 py-2 bg-status-info-50 dark:bg-status-info-900/20 text-status-info-800 dark:text-status-info-200 text-sm rounded-lg">
          {actionMsg}
        </div>
      )}

      {/* Retention stats */}
      {retention && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4" /> Data Retention
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Total Entries</p>
              <p className="font-bold text-lsc-dark dark:text-lsc-cream">{retention.total_entries}</p>
            </div>
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Patron Interactions</p>
              <p className="font-bold text-lsc-dark dark:text-lsc-cream">{retention.patron_interaction_entries}</p>
            </div>
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Expired</p>
              <p className="font-bold text-status-warning-600 dark:text-status-warning-400">{retention.expired_entries}</p>
            </div>
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Retention Period</p>
              <p className="font-bold text-lsc-dark dark:text-lsc-cream">{retention.retention_months} months</p>
            </div>
          </div>
          <button onClick={handleRetentionCleanup}
            className="mt-4 px-4 py-2 text-sm bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200 rounded-lg hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50 flex items-center gap-2">
            <Trash2 className="w-4 h-4" /> Run Retention Cleanup
          </button>
        </div>
      )}

      {/* Batch processing */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Play className="w-4 h-4" /> Batch Processing
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">
          Process unprocessed knowledge entries into scored training examples.
        </p>
        <div className="flex items-end gap-3">
          <div>
            <label className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 block mb-1">Persona (optional)</label>
            <input value={batchDomain} onChange={e => setBatchDomain(e.target.value)} placeholder={t('placeholder.adminTrainingPipeline.egSharedReference')}
              className="text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 w-48" />
          </div>
          <button onClick={handleBatchProcess}
            className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 flex items-center gap-2">
            <Zap className="w-4 h-4" /> Process Batch
          </button>
        </div>
      </div>

      {/* Export */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Download className="w-4 h-4" /> Export Training Data
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-3">
          Download approved training examples as JSONL for fine-tuning.
        </p>
        <div className="flex items-end gap-3">
          <div>
            <label className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 block mb-1">Persona Domain</label>
            <input value={exportDomain} onChange={e => setExportDomain(e.target.value)}
              className="text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 w-48" />
          </div>
          <button onClick={handleExport}
            className="px-4 py-2 text-sm bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 flex items-center gap-2">
            <Download className="w-4 h-4" /> Export JSONL
          </button>
        </div>
      </div>
    </div>
  )
}
