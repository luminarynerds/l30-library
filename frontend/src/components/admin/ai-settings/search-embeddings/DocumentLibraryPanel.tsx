/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileText, Loader2, Trash2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'

import { useTranslation } from '@/i18n'
import {
  deleteDocument,
  getDocumentList,
  getDocumentStats,
  uploadPdfDocument,
  uploadTextDocument,
} from '../../semantic-search/semantic-search-api-helpers'
import { AccordionSection, StatCard } from '../../semantic-search/SemanticSearchPrimitives'
import { DOCUMENT_TYPES } from '../../semantic-search/semantic-search-admin-data'
import ConfirmDialog from '@/components/ConfirmDialog'

interface Props {
  expanded: boolean
  onToggle: () => void
}

export function DocumentLibraryPanel({ expanded, onToggle }: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [docTitle, setDocTitle] = useState('')
  const [docType, setDocType] = useState('newsletter')
  const [docDescription, setDocDescription] = useState('')
  const [docPublishDate, setDocPublishDate] = useState('')
  const [docTags, setDocTags] = useState('')
  const [docTextContent, setDocTextContent] = useState('')
  const [uploadMode, setUploadMode] = useState<'pdf' | 'text'>('pdf')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmTitle, setConfirmTitle] = useState('')
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const { data: docList, refetch: refetchDocs } = useQuery({
    queryKey: ['library-documents'],
    queryFn: () => getDocumentList(),
    staleTime: 1000 * 30,
  })

  const { data: docStats, refetch: refetchDocStats } = useQuery({
    queryKey: ['library-document-stats'],
    queryFn: getDocumentStats,
    staleTime: 1000 * 30,
  })

  const resetForm = () => {
    setDocTitle('')
    setDocDescription('')
    setDocPublishDate('')
    setDocTags('')
  }

  const uploadPdfMutation = useMutation({
    mutationFn: uploadPdfDocument,
    onSuccess: () => {
      toast.success(t('admin.adminSemanticSearch.pdfUploadedAndChunkedSuccessfully'))
      refetchDocs(); refetchDocStats()
      queryClient.invalidateQueries({ queryKey: ['embedding-stats'] })
      resetForm()
    },
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToUploadPdf')),
  })

  const uploadTextMutation = useMutation({
    mutationFn: uploadTextDocument,
    onSuccess: () => {
      toast.success(t('admin.adminSemanticSearch.textContentIngestedAndChunked'))
      refetchDocs(); refetchDocStats()
      queryClient.invalidateQueries({ queryKey: ['embedding-stats'] })
      resetForm()
      setDocTextContent('')
    },
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToIngestText')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      toast.success(t('toast.adminSemanticSearch.documentDeleted'))
      refetchDocs(); refetchDocStats()
      queryClient.invalidateQueries({ queryKey: ['embedding-stats'] })
    },
    onError: (err: Error) => toast.error(err.message || t('toast.adminSemanticSearch.failedToDeleteDocument')),
  })

  const handleDocUpload = () => {
    if (!docTitle.trim()) { toast.error(t('toast.acquisition.titleIsRequired')); return }
    const formData = new FormData()
    formData.append('title', docTitle)
    formData.append('document_type', docType)
    if (docDescription) formData.append('description', docDescription)
    if (docPublishDate) formData.append('publish_date', docPublishDate)
    if (docTags) formData.append('tags', docTags)
    formData.append('auto_embed', 'true')

    if (uploadMode === 'pdf') {
      const input = document.getElementById('doc-pdf-input') as HTMLInputElement
      if (!input?.files?.length) { toast.error(t('admin.adminSemanticSearch.selectAPdfFile')); return }
      formData.append('file', input.files[0]!)
      uploadPdfMutation.mutate(formData)
    } else {
      if (!docTextContent.trim()) { toast.error(t('admin.adminSemanticSearch.pasteSomeTextContent')); return }
      formData.append('text_content', docTextContent)
      uploadTextMutation.mutate(formData)
    }
  }

  return (
    <AccordionSection
      id="documents"
      title="Document Library"
      icon={<FileText className="h-5 w-5 text-teal-500" />}
      badge={
        docStats ? (
          <span className="px-2 py-0.5 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 text-xs rounded-full">
            {docStats.total_documents} documents &middot; {docStats.total_chunks} chunks
          </span>
        ) : undefined
      }
      expanded={expanded}
      onToggle={onToggle}
    >
      <div className="space-y-6">
        <p className="text-sm text-earth-600 dark:text-earth-300">
          Upload newsletters, annual reports, and other library content for semantic search.
          PDFs are automatically text-extracted and chunked. Embeddings are generated in the background.
        </p>

        {docStats && docStats.total_documents > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="Documents" value={docStats.total_documents} />
            <StatCard label="Chunks" value={docStats.total_chunks} />
            {Object.entries(docStats.by_type).map(([type, count]) => (
              <StatCard key={type} label={type.replace(/_/g, ' ')} value={count} />
            ))}
          </div>
        )}

        <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <Upload className="w-5 h-5 text-teal-500 flex-shrink-0" />
            <h4 className="text-sm font-semibold text-earth-900 dark:text-earth-100">Upload Document</h4>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setUploadMode('pdf')}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                uploadMode === 'pdf'
                  ? 'bg-teal-600 text-white'
                  : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 hover:bg-earth-200 dark:hover:bg-earth-600'
              }`}
            >
              PDF Upload
            </button>
            <button
              onClick={() => setUploadMode('text')}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                uploadMode === 'text'
                  ? 'bg-teal-600 text-white'
                  : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 hover:bg-earth-200 dark:hover:bg-earth-600'
              }`}
            >
              Paste Text
            </button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Title *</label>
              <input
                type="text"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                placeholder={t('placeholder.adminSemanticSearch.fall2024Newsletter')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Document Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              >
                {DOCUMENT_TYPES.map((dt) => (
                  <option key={dt.value} value={dt.value}>{dt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Publish Date</label>
              <input
                type="date"
                value={docPublishDate}
                onChange={(e) => setDocPublishDate(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Tags (comma-separated)</label>
              <input
                type="text"
                value={docTags}
                onChange={(e) => setDocTags(e.target.value)}
                placeholder={t('placeholder.adminSemanticSearch.summerReadingStaffPicks')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Description (optional)</label>
            <input
              type="text"
              value={docDescription}
              onChange={(e) => setDocDescription(e.target.value)}
              placeholder={t('admin.adminSemanticSearch.quarterlyNewsletterWithStaffPicks')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm"
            />
          </div>

          {uploadMode === 'pdf' ? (
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">PDF File</label>
              <input
                id="doc-pdf-input"
                type="file"
                accept=".pdf"
                className="w-full text-sm text-earth-600 dark:text-earth-300 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-medium file:bg-teal-50 dark:file:bg-teal-900/30 file:text-teal-700 dark:file:text-teal-300 hover:file:bg-teal-100"
              />
            </div>
          ) : (
            <div>
              <label className="block text-xs font-medium text-earth-600 dark:text-earth-300 mb-1">Text Content</label>
              <textarea
                value={docTextContent}
                onChange={(e) => setDocTextContent(e.target.value)}
                rows={6}
                placeholder={t('admin.adminSemanticSearch.pasteTheNewsletterOrReport')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-earth-900 dark:text-earth-100 text-sm font-mono"
              />
            </div>
          )}

          <button
            onClick={handleDocUpload}
            disabled={uploadPdfMutation.isPending || uploadTextMutation.isPending}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-xl disabled:opacity-50 transition-colors shadow-sm hover:shadow-md"
          >
            {(uploadPdfMutation.isPending || uploadTextMutation.isPending) ? (
              <><Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Processing...</>
            ) : (
              <><Upload className="w-4 h-4" /> Upload &amp; Index</>
            )}
          </button>
        </div>

        {docList && docList.documents.length > 0 && (
          <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
            <div className="px-4 py-3 bg-earth-50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
              <h4 className="text-sm font-semibold text-earth-900 dark:text-earth-100">Uploaded Documents ({docList.total})</h4>
            </div>
            <div className="divide-y divide-earth-200 dark:divide-earth-700">
              {docList.documents.map((doc) => (
                <div key={doc.id} className="px-4 py-3 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-teal-500 flex-shrink-0" />
                      <span className="text-sm font-medium text-earth-900 dark:text-earth-100 truncate" title={doc.title}>{doc.title}</span>
                      <span className="px-1.5 py-0.5 bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 text-xs rounded">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-xs text-earth-600 dark:text-earth-300 mt-0.5 flex items-center gap-3">
                      <span>{doc.chunk_count} chunks</span>
                      {doc.page_count && <span>{doc.page_count} pages</span>}
                      {doc.publish_date && <span>{new Date(doc.publish_date).toLocaleDateString()}</span>}
                      <span>Uploaded {new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => { setConfirmTitle(doc.title); setPendingAction(() => () => deleteMutation.mutate(doc.id)); setConfirmOpen(true) }}
                    disabled={deleteMutation.isPending}
                    className="ml-3 inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-1.5 text-status-danger-500 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete document?"
        message={<>Delete <strong>{confirmTitle}</strong> and its embeddings?</>}
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </AccordionSection>
  )
}
