/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useRef, useEffect } from "react"
import { CatalogItem, CatalogImage as CatalogImageType, DuplicateCandidate } from "../../api/catalog-api"
import { Z3950SearchResult } from "../../api/cataloging-api"
import { useAuth } from "../../contexts/AuthContext"
import CatalogImageUpload from "../../components/catalog/CatalogImageUpload"
import { PrintableBarcode } from "../../components/print"
import { X, Loader2, Search, Check, AlertCircle, ExternalLink, Image, RefreshCw, Library, Eye } from "lucide-react"
import { ITEM_TYPES, ITEM_STATUSES, CATALOGING_DRAFT_KEY, emptyForm, type FormData } from "./constants"
import ConflictWarning from "../../components/catalog/ConflictWarning"
import type { ConflictData } from "../../hooks/useOptimisticLock"
import { t, useTranslation } from '@/i18n'
import { AcquisitionRationaleForm } from '@/components/cataloging/AcquisitionRationaleForm'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import Z3950PreviewPanel from "./Z3950PreviewPanel"
import { LexileParsePreview } from "../../components/LexileParsePreview"

interface CatalogItemFormModalProps {
  isOpen: boolean
  editingItem: CatalogItem | null
  formData: FormData
  setFormData: React.Dispatch<React.SetStateAction<FormData>>
  onFormChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
  isSaving: boolean
  onGenerateBarcode: () => void

  // Duplicates
  duplicates: DuplicateCandidate[]
  isCheckingDuplicates: boolean
  showDuplicateWarning: boolean

  // Draft
  draftRestored: boolean
  setDraftRestored: (v: boolean) => void

  // Z39.50
  showZ3950Search: boolean
  setShowZ3950Search: (v: boolean) => void
  z3950Results: Z3950SearchResult[]
  isSearchingZ3950: boolean
  onZ3950Search: () => void
  onZ3950Import: (record: Z3950SearchResult) => void
  selectedZ3950Record: Z3950SearchResult | null
  onSelectZ3950Record: (record: Z3950SearchResult) => void
  onUseZ3950Field: (key: keyof FormData, value: string) => void
  onUseAllZ3950Data: () => void
  onClearZ3950Selection: () => void

  // Cover
  isFetchingCover: boolean
  onFetchCover: () => void

  // Images
  catalogImages: CatalogImageType[]
  onImagesChanged: () => void

  // Optimistic locking
  isStale: boolean
  conflictData: ConflictData | null
  onForceSave: () => void
  onReloadItem: () => void
  onCancelConflict: () => void

  // Acquisition rationale
  hasRationale: boolean
  setHasRationale: (v: boolean) => void

  // Recently-used suggestions (E4)
  recentItems: CatalogItem[]

  // Save & add another (E1) — returns true on a successful keep-open create
  onSaveAndAddAnother: (e: React.SyntheticEvent) => Promise<boolean>
}

const CatalogItemFormModal: React.FC<CatalogItemFormModalProps> = ({
  isOpen,
  editingItem,
  formData,
  setFormData,
  onFormChange,
  onSubmit,
  onClose,
  isSaving,
  onGenerateBarcode,
  duplicates,
  isCheckingDuplicates,
  showDuplicateWarning,
  draftRestored,
  setDraftRestored,
  showZ3950Search,
  setShowZ3950Search,
  z3950Results,
  isSearchingZ3950,
  onZ3950Search,
  onZ3950Import: _onZ3950Import,
  selectedZ3950Record,
  onSelectZ3950Record,
  onUseZ3950Field,
  onUseAllZ3950Data,
  onClearZ3950Selection,
  isFetchingCover,
  onFetchCover,
  catalogImages,
  onImagesChanged,
  isStale,
  conflictData,
  onForceSave,
  onReloadItem,
  onCancelConflict,
  hasRationale,
  setHasRationale,
  recentItems,
  onSaveAndAddAnother,
// eslint-disable-next-line complexity
}) => {
  const { t: tt } = useTranslation()
  const { token } = useAuth()

  const isbnRef = useRef<HTMLInputElement>(null)

  // Autofocus ISBN field when modal opens for new item (supports USB barcode scanners)
  useEffect(() => {
    if (isOpen && !editingItem) {
      const timer = setTimeout(() => isbnRef.current?.focus(), 100)
      return () => clearTimeout(timer)
    }
  }, [isOpen, editingItem])

  // Handle Enter key on ISBN field to trigger Z39.50 search
  const handleIsbnKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const val = formData.isbn.trim()
      if (/^\d{9}[\dX]$/.test(val) || /^\d{13}$/.test(val)) {
        e.preventDefault()
        onZ3950Search()
      }
    }
  }

  // Derived filled-state for collapsible section badges and header count (E3)
  const physicalFilled = [formData.location, formData.barcode, formData.publication_year, formData.publisher].filter(v => v.trim()).length
  const descriptionFilled = [formData.subjects, formData.lexile_measure ?? '', formData.description].filter(v => v.trim()).length
  // Count only meaningfully-filled fields (exclude defaulted item_type/status selects)
  const filledFieldCount = [
    formData.title, formData.author, formData.isbn, formData.cover_url,
    formData.location, formData.barcode, formData.publication_year, formData.publisher,
    formData.subjects, formData.lexile_measure ?? '', formData.description,
  ].filter(v => v.trim()).length

  // Recently-used suggestions from current page results (E4)
  const distinct = (vals: (string | null | undefined)[]) =>
    Array.from(new Set(vals.map(v => (v ?? '').trim()).filter(Boolean)))
  const locationSuggestions = distinct(recentItems.map(i => i.location))
  const publisherSuggestions = distinct(recentItems.map(i => i.publisher))
  const subjectSuggestions = distinct(recentItems.map(i => i.subjects))

  if (!isOpen) return null

  return (
    <ModalBackdrop onClose={onClose} title="Dialog" role="alertdialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between z-10">
          <div className="flex items-baseline gap-3">
            <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{editingItem ? "Edit Item" : "Add New Item"}</h2>
            {filledFieldCount > 0 && (
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{filledFieldCount} {t('staff.cataloging.fieldsEnteredShort', 'fields entered')}</span>
            )}
          </div>
          <button onClick={onClose} aria-label="Close" className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-xl focus:outline-none focus:ring-2 focus:ring-lsc-rose">
            <X aria-hidden="true" className="w-5 h-5" />
          </button>
        </div>

        {/* Z39.50 Import Panel */}
        {showZ3950Search && !editingItem && !selectedZ3950Record && (
          <div className="px-6 py-5 bg-earth-50 dark:bg-earth-800/20 border-b border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <Library className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              <h3 className="font-serif text-lg font-semibold text-earth-800 dark:text-lsc-rose-light/80">
                Import from Library of Congress
              </h3>
            </div>
            <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mb-4">
              Save time by importing catalog data. Enter an ISBN or title to search.
            </p>

            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={formData.isbn || formData.title}
                onChange={(e) => {
                  const val = e.target.value
                  if (/^[\d\-X]+$/.test(val.replace(/\s/g, ''))) {
                    setFormData(prev => ({ ...prev, isbn: val, title: '' }))
                  } else {
                    setFormData(prev => ({ ...prev, title: val, isbn: '' }))
                  }
                }}
                placeholder={t('placeholder.catalogItemFormModal.enterIsbnEg9780123456789')}
                aria-label={t('staff.cataloging.locImportSearchLabel', 'ISBN or title to import from Library of Congress')}
                className="flex-1 px-4 py-2.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:outline-none"
                autoFocus
              />
              <button onClick={onZ3950Search} disabled={isSearchingZ3950 || (!formData.isbn && !formData.title)}
                className="px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg flex items-center gap-2 font-medium transition-colors">
                {isSearchingZ3950 ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
                Search
              </button>
            </div>
            <p aria-live="polite" className="text-xs text-lsc-rose dark:text-lsc-rose-light mb-3 min-h-[1rem]">
              {formData.isbn
                ? t('staff.cataloging.searchingByIsbn', 'Searching by ISBN')
                : formData.title
                  ? t('staff.cataloging.searchingByTitle', 'Searching by title')
                  : ''}
            </p>

            {z3950Results.length > 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                {z3950Results.map((record, idx) => (
                  <div key={idx} className="p-3 bg-lsc-white dark:bg-earth-800 rounded-lg flex items-start justify-between gap-3 border border-lsc-border dark:border-earth-700">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={record.title ?? undefined}>{record.title}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {record.author} {record.publication_year && `(${record.publication_year})`}{record.edition && ` — ${record.edition}`}
                      </p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                        {[record.publisher, record.isbn && `ISBN: ${record.isbn}`, record.lc_call_number].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    <button onClick={() => onSelectZ3950Record(record)}
                      className="px-3 py-1.5 text-sm bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg flex items-center gap-1 flex-shrink-0 transition-colors">
                      <Eye className="w-3 h-3" />
                      Review
                    </button>
                  </div>
                ))}
              </div>
            )}

            <button
              type="button"
              onClick={() => setShowZ3950Search(false)}
              className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              Skip, enter details manually
            </button>
          </div>
        )}

        {/* Z39.50 Side-by-Side Preview */}
        {selectedZ3950Record && !editingItem && (
          <Z3950PreviewPanel
            record={selectedZ3950Record}
            formData={formData}
            onUseField={onUseZ3950Field}
            onUseAll={onUseAllZ3950Data}
            onClose={onClearZ3950Selection}
          />
        )}

        {/* Duplicate Warning */}
        {duplicates.length > 0 && (
          <div role="alert" className="px-6 py-4 bg-status-warning-50 dark:bg-status-warning-900/20 border-b border-status-warning-200 dark:border-status-warning-800">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-status-warning-800 dark:text-status-warning-300">Potential Duplicate{duplicates.length > 1 ? 's' : ''} Found</p>
                <p className="text-sm text-status-warning-700 dark:text-status-warning-400 mb-2">
                  {duplicates.length} existing item{duplicates.length > 1 ? 's match' : ' matches'} your entry. Review before saving.
                </p>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {duplicates.map(dup => (
                    <div key={dup.id} className="flex items-center justify-between p-2 bg-lsc-white dark:bg-earth-800 rounded border border-status-warning-200 dark:border-status-warning-700">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={dup.title}>{dup.title}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                          {dup.author} {dup.isbn && `| ISBN: ${dup.isbn}`} | {Math.round(dup.match_confidence * 100)}% match ({dup.match_type})
                        </p>
                      </div>
                      <a href={`/catalog/${dup.id}`} target="_blank" rel="noopener noreferrer"
                        className="p-1.5 text-status-warning-600 hover:text-status-warning-700 dark:text-status-warning-400">
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  ))}
                </div>
                {showDuplicateWarning && (
                  <p className="mt-2 text-sm text-status-warning-800 dark:text-status-warning-300 font-medium">
                    Click Save again to create anyway, or modify your entry.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}


        {/* Concurrent edit conflict warning */}
        {isStale && conflictData && (
          <ConflictWarning
            conflictData={conflictData}
            onForceSave={onForceSave}
            onReload={onReloadItem}
            onCancel={onCancelConflict}
          />
        )}
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          {/* Draft restored notice */}
          {draftRestored && (
            <div className="flex items-center justify-between p-3 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg">
              <p className="text-sm text-status-success-800 dark:text-status-success-300 flex items-center gap-2">
                <Check className="w-4 h-4" />
                Draft restored from your last session.
              </p>
              <button
                type="button"
                onClick={() => {
                  setFormData(emptyForm)
                  setDraftRestored(false)
                  setShowZ3950Search(true)
                  localStorage.removeItem(CATALOGING_DRAFT_KEY)
                }}
                className="text-sm text-status-success-700 dark:text-status-success-400 hover:underline font-medium"
              >
                Discard draft
              </button>
            </div>
          )}

          {/* Re-open import option */}
          {!showZ3950Search && !editingItem && !selectedZ3950Record && (
            <button
              type="button"
              onClick={() => setShowZ3950Search(true)}
              className="flex items-center gap-2 text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              <Library className="w-4 h-4" />
              Import from Library of Congress instead
            </button>
          )}

          {/* Cover Preview */}
          {(editingItem || formData.cover_url) && (
            <div className="flex items-start gap-4 p-4 bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-xl">
              {formData.cover_url ? (
                <img src={formData.cover_url} alt="Cover preview" className="w-20 h-28 object-cover rounded shadow-sm" />
              ) : (
                <div className="w-20 h-28 bg-lsc-border dark:bg-earth-700 rounded flex items-center justify-center">
                  <Image className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/60" />
                </div>
              )}
              <div className="flex-1">
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="cover_url">Cover Image URL</label>
                <input id="cover_url" type="url" name="cover_url" value={formData.cover_url} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose text-sm"
                  placeholder={t('placeholder.catalogItemFormModal.httpsexamplecomcoverjpg')} />
                {editingItem && (
                  <button type="button" onClick={onFetchCover} disabled={isFetchingCover}
                    className="mt-2 px-3 py-1.5 text-sm bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg flex items-center gap-2 transition-colors">
                    {isFetchingCover ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                    Auto-fetch Cover
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Image Upload */}
          {editingItem && token && (
            <div className="p-4 bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-xl">
              <CatalogImageUpload
                itemId={editingItem.id}
                images={catalogImages}
                token={token}
                onImagesChanged={onImagesChanged}
              />
            </div>
          )}

          {/* Essential Fields */}
          <fieldset className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <legend className="text-sm font-semibold text-lsc-rose px-2">Essential</legend>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="title">Title *</label>
                <input id="title" type="text" name="title" value={formData.title} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="author">Author</label>
                <input id="author" type="text" name="author" value={formData.author} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="isbn">ISBN</label>
                <div className="relative">
                  <input id="isbn" ref={isbnRef} type="text" name="isbn" value={formData.isbn} onChange={onFormChange} onKeyDown={handleIsbnKeyDown}
                    aria-describedby="isbn-hint"
                    className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                    placeholder={t('placeholder.catalogItemFormModal.9780123456789')} />
                  {isCheckingDuplicates && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
                    </div>
                  )}
                </div>
                <p id="isbn-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('staff.cataloging.isbnHint', '10 or 13 digits, no dashes — triggers auto-lookup')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="item_type">Type</label>
                <select id="item_type" name="item_type" value={formData.item_type} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose">
                  {ITEM_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="status">Status</label>
                <select id="status" name="status" value={formData.status} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose">
                  {["Available", "Circulation", "Acquisitions", "Lost", "Damaged", "Collection"].map(group => (
                    <optgroup key={group} label={group}>
                      {ITEM_STATUSES.filter(s => s.group === group).map((s) => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
            </div>
          </fieldset>

          {/* Physical / Location Details */}
          <details className="border border-lsc-border dark:border-earth-700 rounded-xl" open={!!editingItem || !!formData.barcode || !!formData.location}>
            <summary className="text-sm font-semibold text-lsc-rose px-4 py-3 cursor-pointer hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 rounded-xl select-none flex items-center gap-2">
              <span>Physical &amp; Location Details</span>
              {physicalFilled > 0 && (
                <span className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70" aria-label={t('staff.cataloging.fieldsEntered', `${physicalFilled} fields entered`)}>
                  <span aria-hidden="true">• </span>{physicalFilled} {t('staff.cataloging.entered', 'entered')}
                </span>
              )}
            </summary>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-4 pb-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="location">Location</label>
                <input id="location" list="location-suggestions" type="text" name="location" value={formData.location} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" placeholder={t('placeholder.catalogItemFormModal.egShelfA3')} />
                <datalist id="location-suggestions">
                  {locationSuggestions.map(v => <option key={v} value={v} />)}
                </datalist>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between gap-2">
                  <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80" htmlFor="barcode">Barcode</label>
                  <button
                    type="button"
                    onClick={onGenerateBarcode}
                    className="text-xs font-medium text-lsc-rose hover:text-lsc-rose/80"
                  >
                    Auto-generate
                  </button>
                </div>
                <input id="barcode" type="text" name="barcode" value={formData.barcode} onChange={onFormChange}
                  aria-describedby="barcode-hint"
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
                <p id="barcode-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('staff.cataloging.barcodeHint', 'Auto-generate creates an LSC- code')}</p>
                {formData.barcode.trim() && (
                  <div className="mt-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-700/30 p-3">
                    <p className="mb-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Print preview</p>
                    <PrintableBarcode value={formData.barcode.trim()} format="code128" width={240} height={60} />
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="publication_year">Year</label>
                <input id="publication_year" type="number" name="publication_year" value={formData.publication_year} onChange={onFormChange}
                  aria-describedby="year-hint"
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" placeholder={t('placeholder.catalogItemFormModal.2024')} />
                <p id="year-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('staff.cataloging.yearHint', '4-digit year')}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="publisher">Publisher</label>
                <input id="publisher" list="publisher-suggestions" type="text" name="publisher" value={formData.publisher} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
                <datalist id="publisher-suggestions">
                  {publisherSuggestions.map(v => <option key={v} value={v} />)}
                </datalist>
              </div>
            </div>
          </details>

          {/* Description & Subjects */}
          <details className="border border-lsc-border dark:border-earth-700 rounded-xl" open={!!editingItem || !!formData.description || !!formData.subjects}>
            <summary className="text-sm font-semibold text-lsc-rose px-4 py-3 cursor-pointer hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 rounded-xl select-none flex items-center gap-2">
              <span>Description &amp; Subjects</span>
              {descriptionFilled > 0 && (
                <span className="text-xs font-normal text-lsc-dark/70 dark:text-lsc-cream/70" aria-label={t('staff.cataloging.fieldsEntered', `${descriptionFilled} fields entered`)}>
                  <span aria-hidden="true">• </span>{descriptionFilled} {t('staff.cataloging.entered', 'entered')}
                </span>
              )}
            </summary>
            <div className="grid grid-cols-1 gap-4 px-4 pb-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="subjects">Subjects</label>
                <input id="subjects" list="subject-suggestions" type="text" name="subjects" value={formData.subjects} onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  placeholder={t('placeholder.catalogItemFormModal.fictionMysteryThrillerCommaseparated')} />
                <datalist id="subject-suggestions">
                  {subjectSuggestions.map(v => <option key={v} value={v} />)}
                </datalist>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">Mood browse tips: quiet (nature, gardening, poetry, cooking) · funny (humor, comedy) · feel good (romance, community, family, friendship) · gripping (mystery, thriller, suspense, noir) · surprising (science fiction, fantasy, cyberpunk) · understood (memoir, identity, immigration, mental health, neurodivergence)</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="lexile_measure">{t('staff_form_lexile_label')}</label>
                <input
                  id="lexile_measure"
                  type="text"
                  name="lexile_measure"
                  value={formData.lexile_measure ?? ''}
                  onChange={onFormChange}
                  placeholder={t('staff_form_lexile_placeholder')}
                  maxLength={10}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-describedby="lexile-hint"
                />
                <LexileParsePreview raw={formData.lexile_measure} />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="description">Description</label>
                <textarea id="description" name="description" value={formData.description} onChange={onFormChange} rows={3}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
              </div>
            </div>
          </details>

          {/* Media-specific Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Multimedia fields - DVD/Blu-ray */}
            {(formData.item_type === "dvd" || formData.item_type === "bluray") && (<>
              <div className="md:col-span-2 pt-4 border-t border-lsc-border dark:border-earth-700"><p className="text-sm font-semibold text-lsc-rose">DVD/Blu-ray Details</p></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="director">Director</label><input id="director" type="text" name="director" value={formData.director} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="studio">Studio</label><input id="studio" type="text" name="studio" value={formData.studio} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div className="md:col-span-2"><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="actors">Cast</label><input id="actors" type="text" name="actors" value={formData.actors} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" placeholder={t('placeholder.catalogItemFormModal.commaseparated')} /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="runtime_minutes">Runtime (min)</label><input id="runtime_minutes" type="number" name="runtime_minutes" value={formData.runtime_minutes} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="content_rating_dvd">Rating</label><select id="content_rating_dvd" name="content_rating" value={formData.content_rating} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"><option value="">Select...</option><option value="G">G</option><option value="PG">PG</option><option value="PG-13">PG-13</option><option value="R">R</option><option value="NC-17">NC-17</option><option value="Unrated">Unrated</option></select></div>
            </>)}

            {/* Multimedia fields - CD/Vinyl */}
            {(formData.item_type === "cd" || formData.item_type === "vinyl") && (<>
              <div className="md:col-span-2 pt-4 border-t border-lsc-border dark:border-earth-700"><p className="text-sm font-semibold text-lsc-rose">Music Details</p></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="artist">Artist</label><input id="artist" type="text" name="artist" value={formData.artist} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="music_genre">Genre</label><input id="music_genre" type="text" name="music_genre" value={formData.music_genre} onChange={onFormChange} placeholder={t('placeholder.catalogItemFormModal.rockJazzEtc')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="track_count">Tracks</label><input id="track_count" type="number" name="track_count" value={formData.track_count} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="content_rating_music">Content</label><select id="content_rating_music" name="content_rating" value={formData.content_rating} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"><option value="">Select...</option><option value="Explicit">Explicit</option><option value="Clean">Clean</option></select></div>
            </>)}

            {/* Multimedia fields - Games */}
            {formData.item_type === "game" && (<>
              <div className="md:col-span-2 pt-4 border-t border-lsc-border dark:border-earth-700"><p className="text-sm font-semibold text-lsc-rose">Game Details</p></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="platform">Platform</label><input id="platform" type="text" name="platform" value={formData.platform} onChange={onFormChange} placeholder={t('placeholder.catalogItemFormModal.ps5SwitchEtc')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="game_genre">Genre</label><input id="game_genre" type="text" name="game_genre" value={formData.game_genre} onChange={onFormChange} placeholder={t('placeholder.catalogItemFormModal.actionRpgEtc')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="player_count">Players</label><input id="player_count" type="text" name="player_count" value={formData.player_count} onChange={onFormChange} placeholder={t('placeholder.catalogItemFormModal.14Players')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="content_rating_game">ESRB</label><select id="content_rating_game" name="content_rating" value={formData.content_rating} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"><option value="">Select...</option><option value="E">E - Everyone</option><option value="E10+">E10+</option><option value="T">T - Teen</option><option value="M">M - Mature</option></select></div>
            </>)}

            {/* Multimedia fields - Equipment/Kits */}
            {(formData.item_type === "equipment" || formData.item_type === "kit" || formData.item_type === "tool") && (<>
              <div className="md:col-span-2 pt-4 border-t border-lsc-border dark:border-earth-700"><p className="text-sm font-semibold text-lsc-rose">{formData.item_type === "kit" ? "Kit" : formData.item_type === "tool" ? "Tool" : "Equipment"} Details</p></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="brand">Brand</label><input id="brand" type="text" name="brand" value={formData.brand} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="model_number">Model</label><input id="model_number" type="text" name="model_number" value={formData.model_number} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="dimensions">Dimensions</label><input id="dimensions" type="text" name="dimensions" value={formData.dimensions} onChange={onFormChange} placeholder={t('placeholder.catalogItemFormModal.eg12x9x3In')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="material">Material</label><input id="material" type="text" name="material" value={formData.material} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="weight_lbs">Weight (lbs)</label><input id="weight_lbs" type="text" name="weight_lbs" value={formData.weight_lbs} onChange={onFormChange} placeholder="e.g. 2.5" className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="replacement_cost">Replacement Cost</label><input id="replacement_cost" type="text" name="replacement_cost" value={formData.replacement_cost} onChange={onFormChange} placeholder="e.g. 149.99" className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              {(formData.item_type === "tool" || formData.item_type === "equipment") && (<>
                <div className="md:col-span-2 pt-3 border-t border-lsc-border/50 dark:border-earth-700/50"><p className="text-sm font-semibold text-lsc-rose">Safety & Power</p></div>
                <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="power_source">Power Source</label><select id="power_source" name="power_source" value={formData.power_source} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"><option value="">Select...</option><option value="manual">Manual</option><option value="battery">Battery</option><option value="corded">Corded Electric</option><option value="pneumatic">Pneumatic</option><option value="gas">Gas</option></select></div>
                <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="voltage">Voltage</label><input id="voltage" type="text" name="voltage" value={formData.voltage} onChange={onFormChange} placeholder="e.g. 120V, 20V battery" className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
                <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="safety_category">Safety Category</label><select id="safety_category" name="safety_category" value={formData.safety_category} onChange={onFormChange} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"><option value="">Select...</option><option value="hand_tool">Hand Tool</option><option value="power_tool">Power Tool</option><option value="precision">Precision</option><option value="hazardous">Hazardous</option></select></div>
                <div className="flex items-center gap-2"><input id="safety_certification_required" type="checkbox" name="safety_certification_required" checked={formData.safety_certification_required} onChange={onFormChange} className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose" /><label className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80" htmlFor="safety_certification_required">Safety certification required</label></div>
                {formData.safety_certification_required && (
                  <div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="certification_name">Certification Name</label><input id="certification_name" type="text" name="certification_name" value={formData.certification_name} onChange={onFormChange} placeholder="e.g. Table Saw Safety" className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
                )}
                <div className="md:col-span-2"><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="accessories_included">Accessories Included</label><textarea id="accessories_included" name="accessories_included" value={formData.accessories_included} onChange={onFormChange} rows={2} placeholder="Case, spare blade, wrench..." className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none" /></div>
                <div className="md:col-span-2"><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="consumables_needed">Consumables Needed</label><textarea id="consumables_needed" name="consumables_needed" value={formData.consumables_needed} onChange={onFormChange} rows={2} placeholder="Blades, bits, batteries..." className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none" /></div>
                <div className="md:col-span-2"><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="condition_notes">Condition Notes</label><textarea id="condition_notes" name="condition_notes" value={formData.condition_notes} onChange={onFormChange} rows={2} placeholder="Current condition, wear notes..." className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none" /></div>
              </>)}
              {formData.item_type === "kit" && (
                <div className="md:col-span-2"><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="kit_contents">Kit Contents</label><textarea id="kit_contents" name="kit_contents" value={formData.kit_contents} onChange={onFormChange} rows={3} placeholder={t('placeholder.catalogItemFormModal.listItemsInKit')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose" /></div>
              )}
            </>)}
          </div>

          {/* Cataloging Status + Acquisition Rationale (edit mode only) */}
          {editingItem && (
            <div className="pt-4 border-t border-lsc-border dark:border-earth-700 space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1" htmlFor="cataloging_status">
                  Cataloging status
                </label>
                <select
                  id="cataloging_status"
                  name="cataloging_status"
                  value={formData.cataloging_status ?? ""}
                  onChange={onFormChange}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <option value="">--</option>
                  <option value="uncataloged">Uncataloged</option>
                  <option value="in_progress">In progress</option>
                  <option value="cataloged" disabled={!hasRationale}>Cataloged{!hasRationale ? " (rationale required)" : ""}</option>
                </select>
                {formData.cataloging_status === "cataloged" && !hasRationale && (
                  <p role="alert" className="text-sm text-lsc-rose mt-1">
                    {tt('acquisitionRationale.requiredBeforeCataloged')}
                  </p>
                )}
              </div>

              <AcquisitionRationaleForm
                catalogItemId={editingItem.id}
                mode={hasRationale ? 'edit' : 'create'}
                onSaved={() => setHasRationale(true)}
              />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium transition-colors">
              Cancel
            </button>
            {!editingItem && (
              <button
                type="button"
                disabled={isSaving}
                onClick={async (e) => { if (await onSaveAndAddAnother(e)) isbnRef.current?.focus() }}
                className="px-4 py-2 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-earth-700 disabled:opacity-50 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium flex items-center gap-2 transition-colors"
              >
                {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : null}
                {t('staff.cataloging.saveAndAddAnother', 'Save & add another')}
              </button>
            )}
            <button type="submit" disabled={isSaving || (!!editingItem && formData.cataloging_status === "cataloged" && !hasRationale)}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium flex items-center gap-2 transition-colors">
              {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Check aria-hidden="true" className="w-4 h-4" />}
              {editingItem ? "Update" : "Create"}
              {duplicates.length > 0 && !editingItem && " Anyway"}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}

export default CatalogItemFormModal
