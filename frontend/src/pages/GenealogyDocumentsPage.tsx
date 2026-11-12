/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { FileText, Upload, Search, Loader, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  documentsApi,
  personsApi,
  recordLinkingApi,
  type GenealogyDocument,
  type PersonSummary,
  type RecordLink,
} from '@/api/genealogy-research-api'
import { useTranslation } from '@/i18n'
import { DOCUMENT_TYPES } from './genealogy-documents/constants'
import {
  DocumentCard,
  OCRProcessingTab,
  RecordLinkingTab,
  UploadDocumentModal,
  DocumentDetailModal,
} from './genealogy-documents/components'

interface GenealogyDocumentsPageProps {
  projectId: number
}

export default function GenealogyDocumentsPage({ projectId }: GenealogyDocumentsPageProps) {
  const { t } = useTranslation()
  const [documents, setDocuments] = useState<GenealogyDocument[]>([])
  const [persons, setPersons] = useState<PersonSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<GenealogyDocument | null>(null)
  const [showDocDetail, setShowDocDetail] = useState(false)
  const [ocrLoading, setOcrLoading] = useState<number | null>(null)
  const [pendingLinks, setPendingLinks] = useState<RecordLink[]>([])
  const [linksLoading, setLinksLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'documents' | 'ocr' | 'linking'>('documents')

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true)
      const [docsData, personsData] = await Promise.all([
        documentsApi.list(projectId, {
          ...(typeFilter ? { document_type: typeFilter } : {}),
          ...(search ? { search } : {}),
        }),
        personsApi.list(projectId),
      ])
      setDocuments(docsData as GenealogyDocument[])
      setPersons(personsData as PersonSummary[])
    } catch {
      toast.error(t('genealogyDocuments.failedToLoadDocuments'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, typeFilter, search])

  const loadPendingLinks = useCallback(async () => {
    try {
      setLinksLoading(true)
      const links = await recordLinkingApi.list(projectId, 'suggested')
      setPendingLinks(links as RecordLink[])
    } catch {
      toast.error(t('genealogyDocuments.failedToLoadRecordLinks'))
    } finally {
      setLinksLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  useEffect(() => {
    if (activeTab === 'linking') {
      loadPendingLinks()
    }
  }, [activeTab, loadPendingLinks])

  async function handleTriggerOCR(docId: number) {
    try {
      setOcrLoading(docId)
      await documentsApi.triggerOCR(projectId, docId)
      toast.success(t('toast.genealogyDocuments.ocrProcessingStarted'))
      loadDocuments()
    } catch {
      toast.error(t('genealogyDocuments.failedToStartOcr'))
    } finally {
      setOcrLoading(null)
    }
  }

  async function handleReviewLink(linkId: number, status: 'confirmed' | 'rejected') {
    try {
      await recordLinkingApi.review(projectId, linkId, { status })
      toast.success(status === 'confirmed' ? 'Link confirmed' : 'Link rejected')
      loadPendingLinks()
    } catch {
      toast.error(t('genealogyDocuments.failedToReviewLink'))
    }
  }

  async function handleAnalyzeLinks() {
    try {
      setLinksLoading(true)
      const newLinks = await recordLinkingApi.analyze(projectId)
      const linkArr = newLinks as RecordLink[]
      toast.success(t('toast.genealogyDocuments.foundLengthPotentialMatches', { length: linkArr.length }))
      loadPendingLinks()
    } catch {
      toast.error(t('toast.genealogyDocuments.analysisFailed'))
    } finally {
      setLinksLoading(false)
    }
  }

  const docsWithOCR = documents.filter(d => d.ocr_text || d.status === 'ocr_complete')
  const processingDocs = documents.filter(d => d.status === 'processing')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <FileText className="w-5 h-5 text-status-warning-500" />
            Document Management
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {documents.length} documents &bull; {docsWithOCR.length} with OCR &bull; {pendingLinks.length} pending links
          </p>
        </div>
        <button
          onClick={() => setShowUploadModal(true)}
          className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm"
        >
          <Upload className="w-4 h-4" />
          Add Document
        </button>
      </div>

      <div className="border-b border-lsc-border dark:border-earth-700">
        <nav className="flex gap-1 -mb-px">
          {([
            { id: 'documents', label: 'All Documents', count: documents.length },
            { id: 'ocr', label: 'OCR Processing', count: processingDocs.length },
            { id: 'linking', label: 'Record Linking', count: pendingLinks.length },
          ] as { id: typeof activeTab; label: string; count: number }[]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-status-warning-500 text-status-warning-600 dark:text-status-warning-400'
                  : 'border-transparent text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <input
                  type="text"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && loadDocuments()}
                  placeholder={t('genealogyDocuments.searchByTitleDescriptionOr')}
                  aria-label={t('genealogyDocuments.searchByTitleDescriptionOr2')}
                  className="w-full pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <select
              value={typeFilter}
              onChange={e => setTypeFilter(e.target.value)}
              className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">All Types</option>
              {DOCUMENT_TYPES.map(dt => (
                <option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <button
              onClick={loadDocuments}
              className="p-2 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <Loader className="w-6 h-6 motion-safe:animate-spin text-status-warning-500" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-16 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
              <FileText className="w-14 h-14 mx-auto text-earth-300 mb-4" />
              <h3 className="font-serif font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">No Documents Yet</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-5 max-w-sm mx-auto">
                Upload birth certificates, census records, photographs, letters, and other genealogy documents to build your research archive.
              </p>
              <button
                onClick={() => setShowUploadModal(true)}
                className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
              >
                Add Your First Document
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map(doc => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  onView={() => { setSelectedDoc(doc); setShowDocDetail(true) }}
                  onOCR={() => handleTriggerOCR(doc.id)}
                  ocrLoading={ocrLoading === doc.id}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'ocr' && (
        <OCRProcessingTab
          documents={documents}
          loading={loading}
          ocrLoading={ocrLoading}
          onTriggerOCR={handleTriggerOCR}
          onViewDoc={doc => { setSelectedDoc(doc); setShowDocDetail(true) }}
        />
      )}

      {activeTab === 'linking' && (
        <RecordLinkingTab
          links={pendingLinks}
          persons={persons}
          documents={documents}
          loading={linksLoading}
          onAnalyze={handleAnalyzeLinks}
          onReview={handleReviewLink}
          onRefresh={loadPendingLinks}
        />
      )}

      {showUploadModal && (
        <UploadDocumentModal
          projectId={projectId}
          onClose={() => setShowUploadModal(false)}
          onCreated={() => { setShowUploadModal(false); loadDocuments() }}
        />
      )}
      {showDocDetail && selectedDoc && (
        <DocumentDetailModal
          doc={selectedDoc}
          persons={persons}
          projectId={projectId}
          onClose={() => { setShowDocDetail(false); setSelectedDoc(null) }}
          onOCR={() => handleTriggerOCR(selectedDoc.id)}
          ocrLoading={ocrLoading === selectedDoc.id}
          onLinked={() => loadDocuments()}
        />
      )}
    </div>
  )
}
