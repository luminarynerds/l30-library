/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, Check, Eye, FileText, Loader, RefreshCw } from 'lucide-react'
import type { GenealogyDocument } from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'
import { getDocIcon } from '../constants'

interface OCRProcessingTabProps {
  documents: GenealogyDocument[]
  loading: boolean
  ocrLoading: number | null
  onTriggerOCR: (id: number) => void
  onViewDoc: (doc: GenealogyDocument) => void
}

export function OCRProcessingTab({ documents, loading, ocrLoading, onTriggerOCR, onViewDoc }: OCRProcessingTabProps) {
  const { t } = useTranslation()
  const pending = documents.filter(d => d.status === 'pending')
  const processing = documents.filter(d => d.status === 'processing')
  const completed = documents.filter(d => d.status === 'ocr_complete' || d.status === 'verified')

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin text-status-warning-500" /></div>
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatusSummary label="Pending OCR" count={pending.length} color="warning" />
        <StatusSummary label="Processing" count={processing.length} color="accent" />
        <StatusSummary label="OCR Complete" count={completed.length} color="success" />
      </div>

      {processing.length > 0 && (
        <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex items-center gap-3">
          <Loader className="w-4 h-4 motion-safe:animate-spin text-earth-600 flex-shrink-0" />
          <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
            {processing.length} document{processing.length !== 1 ? 's are' : ' is'} currently being processed by OCR. Results will appear shortly.
          </p>
        </div>
      )}

      {pending.length > 0 && (
        <div>
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-status-warning-500" />
            Documents Awaiting OCR
          </h3>
          <div className="space-y-2">
            {pending.map(doc => (
              <div key={doc.id} className="flex items-center justify-between p-4 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  {getDocIcon(doc.document_type)}
                  <div>
                    <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{doc.title}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{doc.document_type.replace(/_/g, ' ')}</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => onViewDoc(doc)} className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 rounded" aria-label={t('aria.genealogyDocuments.viewDocument')}>
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onTriggerOCR(doc.id)}
                    disabled={ocrLoading === doc.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm disabled:opacity-50"
                  >
                    {ocrLoading === doc.id ? <Loader className="w-3.5 h-3.5 motion-safe:animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Run OCR
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {completed.length > 0 && (
        <div>
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
            <Check className="w-4 h-4 text-status-success-500" />
            OCR Completed
          </h3>
          <div className="space-y-2">
            {completed.map(doc => (
              <div key={doc.id} className="flex items-center justify-between p-4 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex items-center gap-3">
                  {getDocIcon(doc.document_type)}
                  <div>
                    <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{doc.title}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{doc.document_type.replace(/_/g, ' ')}</p>
                      {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
                        <span className="text-xs text-status-success-600">
                          {Math.round(doc.ocr_confidence * 100)}% confidence
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <button onClick={() => onViewDoc(doc)} className="flex items-center gap-1.5 px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700">
                  <Eye className="w-3.5 h-3.5" />
                  View OCR
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {documents.length === 0 && (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 mx-auto text-earth-300 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyDocuments.noDocumentsInTheProject')}</p>
        </div>
      )}
    </div>
  )
}

function StatusSummary({ label, count, color }: { label: string; count: number; color: string }) {
  const colorClasses: Record<string, string> = {
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800 text-status-warning-700 dark:text-status-warning-300',
    accent: 'bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700 text-lsc-rose dark:text-lsc-rose-light',
    success: 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800 text-status-success-700 dark:text-status-success-300',
  }
  return (
    <div className={`rounded-xl border p-4 text-center ${colorClasses[color]}`}>
      <p className="text-2xl font-bold">{count}</p>
      <p className="text-xs mt-1">{label}</p>
    </div>
  )
}
