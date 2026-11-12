/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '@/api/types';
import {
  Plus,
  Trash2,
  Archive,
  Download,
  Loader2,
  AlertCircle,
  FileIcon,
  Search,
  CheckCircle,
  X,
  History,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../ConfirmDialog'
import DocumentVersionHistory from './DocumentVersionHistory'
import api from '../../api/api'
import { useTranslation} from '@/i18n'
import FocusTrap from 'focus-trap-react'
import { openDownloadInNewTab } from '@/utils/openDownload'

export interface BoardDocument {
  id: number
  document_type: string
  title: string
  description?: string
  filename: string
  file_path: string
  file_size_bytes?: number | undefined
  mime_type?: string
  is_public: boolean
  meeting_id?: number
  status: string
  published_date?: string
  published_by_id?: number
  view_count: number
  download_count: number
  created_at: string
  updated_at?: string
}

export interface DocumentFormData {
  document_type: string
  title: string
  description: string
  filename: string
  file_path: string
  file_size_bytes?: number | undefined
  mime_type: string
  is_public: boolean
}

interface DocumentsSectionProps {
  token: string | null
  userRole: string
}

const DOCUMENT_TYPES = [
  'board_policy',
  'financial_report',
  'meeting_minutes',
  'strategic_plan',
  'bylaws',
  'annual_report',
  'other',
]

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  board_policy: 'Board Policy',
  financial_report: 'Financial Report',
  meeting_minutes: 'Meeting Minutes',
  strategic_plan: 'Strategic Plan',
  bylaws: 'Bylaws',
  annual_report: 'Annual Report',
  other: 'Other',
}

export default function DocumentsSection({
  token,
  userRole,
}: DocumentsSectionProps): React.ReactElement {
  const [documents, setDocuments] = useState<BoardDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('All')
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'draft' | 'archived'>('published')
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; title: string } | null>(null)
  const [publishConfirm, setPublishConfirm] = useState<{ id: number; title: string } | null>(null)
  const [archiveConfirm, setArchiveConfirm] = useState<{ id: number; title: string } | null>(null)
  const [versionHistory, setVersionHistory] = useState<{ id: number; title: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const { t } = useTranslation()

  const isAdmin = ['admin', 'super_admin'].includes(userRole)
  const canCreate = ['staff', 'admin', 'super_admin'].includes(userRole)

  const fetchDocuments = useCallback(async () => {
    if (!token) return

    try {
      setLoading(true)
      setError(null)
      const data = await api.get(`${API_BASE}/board/documents`)
      const documentsList = Array.isArray(data) ? data : (data.documents || [])
      documentsList.sort(
        (a: BoardDocument, b: BoardDocument) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      setDocuments(documentsList)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to fetch documents'
      setError(message)
      toast.error(message)
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // Derive category chips dynamically from fetched data
  const categoryChips = React.useMemo(() => {
    const counts: Record<string, number> = {}
    documents.forEach((doc) => {
      const type = doc.document_type || 'other'
      counts[type] = (counts[type] || 0) + 1
    })
    return Object.entries(counts)
      .map(([type, count]) => ({
        type,
        label: DOCUMENT_TYPE_LABELS[type] || type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        count,
      }))
      .sort((a, b) => b.count - a.count)
  }, [documents])

  const handleCreateDocument = async (formData: DocumentFormData) => {
    if (!token) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/documents`, formData)
      toast.success(t('toast.documentCreated'))
      setShowForm(false)
      await fetchDocuments()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to create document'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteDocument = async () => {
    if (!token || !deleteConfirm) return

    try {
      setSubmitting(true)
      await api.delete(`${API_BASE}/board/documents/${deleteConfirm.id}`)
      toast.success(t('toast.documentDeleted'))
      setDeleteConfirm(null)
      await fetchDocuments()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to delete document'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handlePublishDocument = async () => {
    if (!token || !publishConfirm) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/documents/${publishConfirm.id}/publish`, {})
      toast.success(t('toast.documentPublished'))
      setPublishConfirm(null)
      await fetchDocuments()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to publish document'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleArchiveDocument = async () => {
    if (!token || !archiveConfirm) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/documents/${archiveConfirm.id}/archive`, {})
      toast.success(t('toast.documentArchived'))
      setArchiveConfirm(null)
      await fetchDocuments()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to archive document'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownloadDocument = (doc: BoardDocument) => {
    try {
      openDownloadInNewTab(doc.file_path, doc.filename)
    } catch (err) {
      console.error(err)
      toast.error(t('toast.documentLinkInvalid', "This document's link can't be opened. Ask library staff to check it."))
    }
  }

  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      (doc.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.filename || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.description || '').toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === 'All' || doc.document_type === filterType
    const matchesStatus =
      statusFilter === 'all' ? true : doc.status === statusFilter

    return matchesSearch && matchesType && matchesStatus
  })

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes === 0) return 'Unknown'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            Board Documents
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {documents.length} documents on file
          </p>
        </div>

        {canCreate && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Document
          </button>
        )}
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('placeholder.board.searchDocuments')}
            aria-label={t('aria.board.searchDocuments')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        {/* Category Filter Chips */}
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by document type">
          <button
            onClick={() => setFilterType('All')}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filterType === 'All'
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/20'
            }`}
          >
            All ({documents.length})
          </button>
          {categoryChips.map((chip) => (
            <button
              key={chip.type}
              onClick={() => setFilterType(chip.type)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                filterType === chip.type
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/20'
              }`}
            >
              {chip.label} ({chip.count})
            </button>
          ))}
        </div>

        {/* Status Filter Chips */}
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
          {([
            { value: 'all', label: 'All Statuses' },
            { value: 'published', label: 'Published' },
            { value: 'draft', label: 'Drafts' },
            { value: 'archived', label: 'Archived' },
          ] as const).map((option) => (
            <button
              key={option.value}
              onClick={() => setStatusFilter(option.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                statusFilter === option.value
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/20'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Documents List */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
        {filteredDocuments.length === 0 ? (
          <div className="p-8 text-center">
            <Archive className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {searchQuery || filterType !== 'All' || statusFilter !== 'published' ? 'No documents match the selected filters' : 'No documents yet'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-300px)]">
            <table className="w-full" aria-label={t('aria.board.boardDocuments')}>
              <thead className="bg-lsc-cream dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Document
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Type
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Size
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Status
                  </th>
                  <th scope="col" className="px-6 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                {filteredDocuments.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <FileIcon className="w-5 h-5 text-lsc-rose flex-shrink-0" />
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {doc.title}
                          </p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {doc.filename}
                          </p>
                          {doc.description && (
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                              {doc.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      <span className="px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded text-xs font-medium">
                        {DOCUMENT_TYPE_LABELS[doc.document_type] || doc.document_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          doc.status === 'published'
                            ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
                            : doc.status === 'archived'
                              ? 'bg-earth-200 text-earth-700 dark:bg-earth-700 dark:text-earth-200'
                              : 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                        }`}
                      >
                        {doc.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setVersionHistory({ id: doc.id, title: doc.title })}
                          className="p-2 hover:bg-category-100 dark:bg-category-900/30 dark:hover:bg-category-900/30 rounded-lg transition-colors"
                          aria-label={`View version history for ${doc.title}`}
                          title="Version History"
                        >
                          <History className="w-4 h-4 text-category-600 dark:text-category-400" aria-hidden="true" />
                        </button>
                        <button
                          onClick={() => handleDownloadDocument(doc)}
                          className="p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                          aria-label={`Download ${doc.title}`}
                        >
                          <Download className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                        </button>
                        {isAdmin && doc.status === 'draft' && (
                          <button
                            onClick={() => setPublishConfirm({ id: doc.id, title: doc.title })}
                            className="p-2 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded-lg transition-colors"
                            aria-label={`Publish ${doc.title}`}
                          >
                            <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
                          </button>
                        )}
                        {isAdmin && doc.status === 'published' && (
                          <button
                            onClick={() => setArchiveConfirm({ id: doc.id, title: doc.title })}
                            className="p-2 hover:bg-status-warning-100 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/30 rounded-lg transition-colors"
                            aria-label={`Archive ${doc.title}`}
                          >
                            <Archive className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
                          </button>
                        )}
                        {isAdmin && (
                          <button
                            onClick={() => setDeleteConfirm({ id: doc.id, title: doc.title })}
                            className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                            aria-label={`Delete ${doc.title}`}
                          >
                            <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Form Modal */}
      {showForm && (
        <DocumentForm
          onSubmit={handleCreateDocument}
          onCancel={() => setShowForm(false)}
          loading={submitting}
        />
      )}

      {/* Publish Confirmation */}
      <ConfirmDialog
        isOpen={!!publishConfirm}
        title="Publish Document?"
        message={`Are you sure you want to publish "${publishConfirm?.title}"?`}
        confirmText="Publish"
        cancelText="Cancel"
        confirmVariant="success"
        onConfirm={handlePublishDocument}
        onCancel={() => setPublishConfirm(null)}
        loading={submitting}
      />

      <ConfirmDialog
        isOpen={!!archiveConfirm}
        title="Archive Document?"
        message={`Are you sure you want to archive "${archiveConfirm?.title}"?`}
        confirmText="Archive"
        cancelText="Cancel"
        confirmVariant="warning"
        onConfirm={handleArchiveDocument}
        onCancel={() => setArchiveConfirm(null)}
        loading={submitting}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Document?"
        message={`Are you sure you want to delete "${deleteConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteDocument}
        onCancel={() => setDeleteConfirm(null)}
        loading={submitting}
      />

      {/* Version History Modal */}
      {versionHistory && (
        <DocumentVersionHistory
          documentId={versionHistory.id}
          documentTitle={versionHistory.title}
          canCreate={canCreate}
          onClose={() => setVersionHistory(null)}
        />
      )}
    </div>
  )
}

// Document Form Component
interface DocumentFormProps {
  onSubmit: (data: DocumentFormData) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

function DocumentForm({ onSubmit, onCancel, loading = false }: DocumentFormProps): React.ReactElement {
  const { t } = useTranslation();

  // Escape key handler
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading) {
        onCancel()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel, loading])

  const [formData, setFormData] = useState({
    document_type: 'other',
    title: '',
    description: '',
    filename: '',
    file_path: '',
    file_size_bytes: undefined as number | undefined,
    mime_type: '',
    is_public: true,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const newErrors: Record<string, string> = {}
    if (!formData.title.trim()) newErrors.title = 'Title is required'
    if (!formData.filename.trim()) newErrors.filename = 'Filename is required'
    if (!formData.file_path.trim()) newErrors.file_path = 'File path is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    setFormData((prev) => ({ ...prev, [name]: newValue }))
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    await onSubmit(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      <div role="dialog" aria-modal="true" aria-labelledby="doc-form-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
          <h2 id="doc-form-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Add Document</h2>
          <button
            onClick={onCancel}
            disabled={loading}
            aria-label="Close"
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div>
            <label htmlFor="document_type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Document Type *
            </label>
            <select
              id="document_type"
              name="document_type"
              value={formData.document_type}
              onChange={handleChange}
              disabled={loading}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            >
              {DOCUMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {DOCUMENT_TYPE_LABELS[type] || type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="doc_title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Title *
            </label>
            <input
              id="doc_title"
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              disabled={loading}
              className={`w-full px-4 py-2 rounded-lg border ${
                errors.title ? 'border-status-danger-500' : 'border-lsc-border dark:border-earth-700'
              } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream`}
              placeholder={t('placeholder.board.documentTitle')}
            />
            {errors.title && <p className="text-sm text-status-danger-600 mt-1">{errors.title}</p>}
          </div>

          <div>
            <label htmlFor="doc_description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Description
            </label>
            <textarea
              id="doc_description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              disabled={loading}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('components.board.documentsSection.briefDescriptionOfTheDocument')}
            />
          </div>

          <div>
            <label htmlFor="doc_filename" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Filename *
            </label>
            <input
              id="doc_filename"
              type="text"
              name="filename"
              value={formData.filename}
              onChange={handleChange}
              disabled={loading}
              className={`w-full px-4 py-2 rounded-lg border ${
                errors.filename ? 'border-status-danger-500' : 'border-lsc-border dark:border-earth-700'
              } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream`}
              placeholder={t('placeholder.board.documentpdf')}
            />
            {errors.filename && <p className="text-sm text-status-danger-600 mt-1">{errors.filename}</p>}
          </div>

          <div>
            <label htmlFor="doc_file_path" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              File Path / URL *
            </label>
            <input
              id="doc_file_path"
              type="text"
              name="file_path"
              value={formData.file_path}
              onChange={handleChange}
              disabled={loading}
              className={`w-full px-4 py-2 rounded-lg border ${
                errors.file_path ? 'border-status-danger-500' : 'border-lsc-border dark:border-earth-700'
              } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream`}
              placeholder={t('placeholder.board.documentsboard2026documentpdfOrHttps')}
            />
            {errors.file_path && <p className="text-sm text-status-danger-600 mt-1">{errors.file_path}</p>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="doc_mime_type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                MIME Type
              </label>
              <input
                id="doc_mime_type"
                type="text"
                name="mime_type"
                value={formData.mime_type}
                onChange={handleChange}
                disabled={loading}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.board.applicationpdf')}
              />
            </div>
            <div>
              <label htmlFor="doc_file_size" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                File Size (bytes)
              </label>
              <input
                id="doc_file_size"
                type="number"
                name="file_size_bytes"
                value={formData.file_size_bytes || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, file_size_bytes: e.target.value ? parseInt(e.target.value) : undefined }))}
                disabled={loading}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.board.1024000')}
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_public"
              name="is_public"
              checked={formData.is_public}
              onChange={handleChange}
              disabled={loading}
              className="w-4 h-4 text-lsc-rose rounded focus:ring-lsc-rose"
            />
            <label htmlFor="is_public" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Make document public when published
            </label>
          </div>

          <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
            >
              {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Add Document
            </button>
          </div>
        </form>
      </div>
      </FocusTrap>
    </div>
  )
}
