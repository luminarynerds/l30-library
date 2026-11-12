/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Clock, Eye, Loader, RefreshCw } from 'lucide-react'
import type { GenealogyDocument } from '@/api/genealogy-research-api'
import { STATUS_COLORS, getDocIcon } from '../constants'

interface DocumentCardProps {
  doc: GenealogyDocument
  onView: () => void
  onOCR: () => void
  ocrLoading: boolean
}

export function DocumentCard({ doc, onView, onOCR, ocrLoading }: DocumentCardProps) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-earth-100 dark:bg-earth-700 flex items-center justify-center">
          {getDocIcon(doc.document_type)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream leading-snug line-clamp-2" title={doc.title}>{doc.title}</p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5 capitalize">{doc.document_type.replace(/_/g, ' ')}</p>
        </div>
      </div>

      {doc.document_date && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 flex items-center gap-1">
          <Clock className="w-3 h-3" /> {doc.document_date}
        </p>
      )}

      {doc.source_repository && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 truncate" title={doc.source_repository}>{doc.source_repository}</p>
      )}

      <div className="flex items-center justify-between">
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[doc.status] || STATUS_COLORS.pending}`}>
          {doc.status.replace(/_/g, ' ')}
        </span>
        <div className="flex gap-1">
          {doc.status === 'pending' && (
            <button
              onClick={onOCR}
              disabled={ocrLoading}
              className="p-1.5 text-earth-600 hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/20 rounded text-xs flex items-center gap-1 disabled:opacity-50"
              title="Run OCR"
            >
              {ocrLoading ? <Loader className="w-3.5 h-3.5 motion-safe:animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            </button>
          )}
          <button
            onClick={onView}
            className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 rounded"
            title="View details"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
        <div className="mt-2 pt-2 border-t border-earth-100 dark:border-earth-700">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
              <div
                className="h-full bg-status-success-500 rounded-full"
                style={{ width: `${doc.ocr_confidence * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-lsc-dark/70 dark:text-lsc-cream/70">{Math.round(doc.ocr_confidence * 100)}% OCR</span>
          </div>
        </div>
      )}
    </div>
  )
}
