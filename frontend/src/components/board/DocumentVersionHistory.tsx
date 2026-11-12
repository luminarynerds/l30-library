/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { History, Download, Plus, Loader2, AlertCircle, X } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  listDocumentVersions,
  createDocumentVersion,
  DocumentVersion,
  DocumentVersionCreate,
} from '../../api/board-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface DocumentVersionHistoryProps {
  documentId: number
  documentTitle: string
  canCreate: boolean
  onClose: () => void
}

export default function DocumentVersionHistory({
  documentId,
  documentTitle,
  canCreate,
  onClose,
}: DocumentVersionHistoryProps): React.ReactElement {
  const { t } = useTranslation()
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showNewVersionForm, setShowNewVersionForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const fetchVersions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listDocumentVersions(documentId)
      setVersions(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load versions'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [documentId])

  useEffect(() => {
    fetchVersions()
  }, [fetchVersions])

  const handleCreateVersion = async (data: DocumentVersionCreate) => {
    try {
      setSubmitting(true)
      await createDocumentVersion(documentId, data)
      toast.success(t('toast.board.newVersionAdded'))
      setShowNewVersionForm(false)
      await fetchVersions()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to add version'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDownload = (version: DocumentVersion) => {
    const link = document.createElement('a')
    link.href = version.file_url
    link.setAttribute('target', '_blank')
    link.setAttribute('rel', 'noopener noreferrer')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const formatFileSize = (bytes: number | null) => {
    if (!bytes || bytes === 0) return null
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <ModalBackdrop onClose={onClose} title="Version History">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <History className="w-5 h-5 text-lsc-rose" />
            <div>
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
                Version History
              </h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                {documentTitle}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
            aria-label={t('aria.board.closeVersionHistory')}
          >
            <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto p-6 space-y-4">
          {canCreate && (
            <button
              onClick={() => setShowNewVersionForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors text-sm"
            >
              <Plus className="w-4 h-4" />
              Add New Version
            </button>
          )}

          {showNewVersionForm && (
            <NewVersionForm
              onSubmit={handleCreateVersion}
              onCancel={() => setShowNewVersionForm(false)}
              loading={submitting}
            />
          )}

          {error && (
            <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
              <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 text-lsc-rose motion-safe:animate-spin" />
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-10">
              <History className="w-10 h-10 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto mb-3" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                No versions recorded yet.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {[...versions].reverse().map((version) => (
                <div
                  key={version.id}
                  className="border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex items-start justify-between gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Version {version.version_number}
                      </span>
                      {version.file_type && (
                        <span className="px-1.5 py-0.5 text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                          {version.file_type}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                      {formatDate(version.created_at)}
                      {version.file_size && (
                        <span className="ml-2">&bull; {formatFileSize(version.file_size)}</span>
                      )}
                    </p>

                    {version.change_notes && (
                      <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
                        {version.change_notes}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => handleDownload(version)}
                    className="flex-shrink-0 p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                    aria-label={`Download version ${version.version_number}`}
                  >
                    <Download className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ============ New Version Form ============

interface NewVersionFormProps {
  onSubmit: (data: DocumentVersionCreate) => Promise<void>
  onCancel: () => void
  loading: boolean
}

function NewVersionForm({ onSubmit, onCancel, loading }: NewVersionFormProps): React.ReactElement {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<DocumentVersionCreate>({
    file_url: '',
    file_size: null,
    file_type: null,
    change_notes: null,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validate = () => {
    const newErrors: Record<string, string> = {}
    if (!formData.file_url.trim()) newErrors.file_url = 'File URL is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value === '' ? null : value,
    }))
    if (errors[name]) {
      setErrors((prev) => {
        const updated = { ...prev }
        delete updated[name]
        return updated
      })
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return
    await onSubmit(formData)
  }

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-lg p-4 bg-lsc-cream/30 dark:bg-earth-700/30">
      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
        Add New Version
      </h3>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            File URL / Path *
          </label>
          <input
            type="text"
            name="file_url"
            value={formData.file_url}
            onChange={handleChange}
            disabled={loading}
            className={`w-full px-3 py-2 text-sm rounded-lg border ${
              errors.file_url ? 'border-status-danger-500' : 'border-lsc-border dark:border-earth-700'
            } bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream`}
            placeholder={t('placeholder.board.documentsboard2026documentv2pdf')}
          />
          {errors.file_url && (
            <p className="text-xs text-status-danger-600 mt-1">{errors.file_url}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              File Type
            </label>
            <input
              type="text"
              name="file_type"
              value={formData.file_type ?? ''}
              onChange={handleChange}
              disabled={loading}
              className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.board.applicationpdf')}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              File Size (bytes)
            </label>
            <input
              type="number"
              name="file_size"
              value={formData.file_size ?? ''}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  file_size: e.target.value ? parseInt(e.target.value) : null,
                }))
              }
              disabled={loading}
              className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.board.1024000')}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Change Notes
          </label>
          <textarea
            name="change_notes"
            value={formData.change_notes ?? ''}
            onChange={handleChange}
            disabled={loading}
            rows={2}
            className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream resize-none"
            placeholder={t('components.board.documentVersionHistory.describeWhatChangedInThis')}
          />
        </div>

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {loading && <Loader2 className="w-3 h-3 motion-safe:animate-spin" />}
            Save Version
          </button>
        </div>
      </form>
    </div>
  )
}
