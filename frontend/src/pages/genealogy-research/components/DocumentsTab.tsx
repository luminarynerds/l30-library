/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  FileText, Search, Loader,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'

export default function DocumentsTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [documents, setDocuments] = useState<Array<{
    id: number; title: string; document_type: string;
    document_date?: string; status: string;
  }>>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(() => {
    loadDocuments()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, typeFilter])

  async function loadDocuments() {
    try {
      setLoading(true)
      const { documentsApi } = await import('@/api/genealogy-research-api')
      const data = await documentsApi.list(projectId, { ...(typeFilter ? { document_type: typeFilter } : {}), ...(search ? { search: search } : {}),})
      setDocuments(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadDocuments'))
    } finally {
      setLoading(false)
    }
  }

  const documentTypes = [
    'birth_certificate', 'death_certificate', 'marriage_certificate', 'census_record',
    'immigration_record', 'military_record', 'photograph', 'letter', 'newspaper_clipping',
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && loadDocuments()}
              placeholder={t('placeholder.board.searchDocuments')}
              aria-label={t('aria.board.searchDocuments')}
              className="w-full pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm"
            />
          </div>
        </div>
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm"
        >
          <option value="">All Types</option>
          {documentTypes.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
      ) : documents.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyResearchPageContent.noDocumentsFoundUploadFamily')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
              <div className="flex items-start gap-3">
                <FileText className="w-8 h-8 text-status-warning-500 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={doc.title}>{doc.title}</p>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{doc.document_type.replace(/_/g, ' ')}</p>
                  {doc.document_date && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{doc.document_date}</p>}
                </div>
              </div>
              <div className="flex items-center gap-2 mt-3">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  doc.status === 'verified' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' :
                  doc.status === 'ocr_complete' ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light' :
                  'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                }`}>
                  {doc.status.replace(/_/g, ' ')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
