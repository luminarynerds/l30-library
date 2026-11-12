/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { documentsApi, type GenealogyDocument } from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'
import { DOCUMENT_TYPES } from '../constants'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface UploadDocumentModalProps {
  projectId: number
  onClose: () => void
  onCreated: () => void
}

export function UploadDocumentModal({ projectId, onClose, onCreated }: UploadDocumentModalProps) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    document_type: 'census_record',
    document_date: '',
    document_location: '',
    source_repository: '',
    source_citation: '',
    file_url: '',
    tags: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!formData.title.trim()) return
    try {
      setSaving(true)
      await documentsApi.create(projectId, formData as Partial<GenealogyDocument>)
      toast.success(t('toast.genealogyDocuments.documentAdded'))
      onCreated()
    } catch {
      toast.error(t('genealogyDocuments.failedToAddDocument'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <Upload className="w-5 h-5 text-status-warning-500" />
          Add Document
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Document Title *</label>
            <input type="text" value={formData.title} onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
              placeholder={t('placeholder.genealogyDocuments.eg1880UsCensus')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Document Type</label>
            <select value={formData.document_type} onChange={e => setFormData(p => ({ ...p, document_type: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              {DOCUMENT_TYPES.map(dt => <option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
            <textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
              rows={2} placeholder={t('genealogyDocuments.describeTheContentsOfThis')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Document Date</label>
              <input type="text" value={formData.document_date} onChange={e => setFormData(p => ({ ...p, document_date: e.target.value }))}
                placeholder={t('placeholder.genealogyDocuments.eg1880OrJun')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Document Location</label>
              <input type="text" value={formData.document_location} onChange={e => setFormData(p => ({ ...p, document_location: e.target.value }))}
                placeholder={t('placeholder.genealogyDocuments.countyStateCountry')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Source Repository</label>
            <input type="text" value={formData.source_repository} onChange={e => setFormData(p => ({ ...p, source_repository: e.target.value }))}
              placeholder={t('placeholder.genealogyDocuments.egFamilysearchAncestryCounty')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Source Citation</label>
            <input type="text" value={formData.source_citation} onChange={e => setFormData(p => ({ ...p, source_citation: e.target.value }))}
              placeholder={t('genealogyDocuments.fullSourceCitationForGenealogical')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">File URL (optional)</label>
            <input type="url" value={formData.file_url} onChange={e => setFormData(p => ({ ...p, file_url: e.target.value }))}
              placeholder={t('placeholder.admin.https1')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Tags (comma-separated)</label>
            <input type="text" value={formData.tags} onChange={e => setFormData(p => ({ ...p, tags: e.target.value }))}
              placeholder={t('placeholder.genealogyDocuments.egIreland1880sImmigration')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button onClick={handleSubmit} disabled={!formData.title.trim() || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium">
            {saving ? 'Adding...' : 'Add Document'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
