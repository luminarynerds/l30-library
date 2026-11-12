/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { ChevronDown, Eye, Link2, Loader, Plus, RefreshCw, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { documentsApi, type GenealogyDocument, type PersonSummary } from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import { STATUS_COLORS, getDocIcon } from '../constants'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface DocumentDetailModalProps {
  doc: GenealogyDocument
  persons: PersonSummary[]
  projectId: number
  onClose: () => void
  onOCR: () => void
  ocrLoading: boolean
  onLinked: () => void
}

export function DocumentDetailModal({ doc, persons, projectId, onClose, onOCR, ocrLoading, onLinked }: DocumentDetailModalProps) {
  const { t } = useTranslation()
  const [showLinkPerson, setShowLinkPerson] = useState(false)
  const [selectedPersonId, setSelectedPersonId] = useState('')
  const [roleInDoc, setRoleInDoc] = useState('')
  const [linking, setLinking] = useState(false)
  const [showOCR, setShowOCR] = useState(false)

  async function handleLinkPerson() {
    if (!selectedPersonId) return
    try {
      setLinking(true)
      await documentsApi.linkPerson(projectId, clean({
        person_id: Number(selectedPersonId),
        document_id: doc.id,
        role_in_document: roleInDoc || undefined,
      }))
      toast.success(t('genealogyDocuments.personLinkedToDocument'))
      setShowLinkPerson(false)
      setSelectedPersonId('')
      setRoleInDoc('')
      onLinked()
    } catch {
      toast.error(t('genealogyDocuments.failedToLinkPerson'))
    } finally {
      setLinking(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-earth-100 dark:bg-earth-700 flex items-center justify-center flex-shrink-0">
              {getDocIcon(doc.document_type)}
            </div>
            <div>
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{doc.title}</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{doc.document_type.replace(/_/g, ' ')}</p>
            </div>
          </div>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 rounded-lg" aria-label={t('aria.authModals.close')}>
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex items-center gap-3 mb-5">
          <span className={`text-sm px-3 py-1 rounded-full font-medium ${STATUS_COLORS[doc.status] || STATUS_COLORS.pending}`}>
            {doc.status.replace(/_/g, ' ')}
          </span>
          {doc.status === 'pending' && (
            <button onClick={onOCR} disabled={ocrLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm disabled:opacity-50">
              {ocrLoading ? <Loader className="w-3.5 h-3.5 motion-safe:animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              Run OCR
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-5">
          {doc.document_date && <InfoRow label="Date" value={doc.document_date} />}
          {doc.document_location && <InfoRow label="Location" value={doc.document_location} />}
          {doc.source_repository && <InfoRow label="Repository" value={doc.source_repository} />}
          {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
            <InfoRow label="OCR Confidence" value={`${Math.round(doc.ocr_confidence * 100)}%`} />
          )}
        </div>

        {doc.source_citation && (
          <div className="mb-4">
            <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Source Citation</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">{doc.source_citation}</p>
          </div>
        )}

        {doc.description && (
          <div className="mb-4">
            <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{doc.description}</p>
          </div>
        )}

        {doc.ocr_text && (
          <div className="mb-4">
            <button
              onClick={() => setShowOCR(!showOCR)}
              className="flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light mb-2"
            >
              <Eye className="w-4 h-4" />
              {showOCR ? 'Hide' : 'View'} OCR Text
              <ChevronDown className={`w-4 h-4 transition-transform ${showOCR ? 'rotate-180' : ''}`} />
            </button>
            {showOCR && (
              <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-4 max-h-48 overflow-y-auto">
                <pre className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap font-mono">
                  {doc.ocr_text}
                </pre>
              </div>
            )}
          </div>
        )}

        <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Link2 className="w-4 h-4 text-earth-600" />
              Link People to Document
            </h3>
            <button onClick={() => setShowLinkPerson(!showLinkPerson)}
              className="flex items-center gap-1.5 text-sm text-status-warning-600 hover:text-status-warning-700 dark:text-status-warning-300 font-medium">
              <Plus className="w-3.5 h-3.5" />
              Link Person
            </button>
          </div>
          {showLinkPerson && (
            <div className="bg-earth-50 dark:bg-earth-900/50 rounded-lg p-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Select Person</label>
                <select value={selectedPersonId} onChange={e => setSelectedPersonId(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
                  <option value="">Choose a person...</option>
                  {persons.map(p => (
                    <option key={p.id} value={p.id}>{p.given_names} {p.surname || ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('genealogyDocuments.roleInDocumentOptional')}</label>
                <input type="text" value={roleInDoc} onChange={e => setRoleInDoc(e.target.value)}
                  placeholder={t('placeholder.genealogyDocuments.egHeadOfHousehold')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
              <div className="flex gap-2">
                <button onClick={handleLinkPerson} disabled={!selectedPersonId || linking}
                  className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm disabled:opacity-50 font-medium">
                  {linking ? 'Linking...' : 'Link Person'}
                </button>
                <button onClick={() => setShowLinkPerson(false)}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800 text-sm">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </ModalBackdrop>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-earth-800 dark:text-earth-200">{value}</p>
    </div>
  )
}
