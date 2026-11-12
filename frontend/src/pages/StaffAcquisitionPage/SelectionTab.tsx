/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from "react"
import { Plus, Search, Loader2, ShoppingCart, Trash2, X } from "lucide-react"
import toast from "react-hot-toast"
import AcquisitionErrorBoundary from "../../components/acquisition/AcquisitionErrorBoundary"
import FundSpendPreview from "../../components/acquisition/FundSpendPreview"
import SelectionEnrichment from "../../components/acquisition/SelectionEnrichment"
import { useTranslation} from "@/i18n"
import { type Fund, type Vendor, type SelectionItem, type ExternalSearchResult, apiFetch, formatMoney } from "./types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface SelectionTabProps {
  token: string
  selectionItems: SelectionItem[]
  vendors: Vendor[]
  funds: Fund[]
  loadData: () => void
  setActiveTab: (tab: string) => void
}

export default function SelectionTab({ token, selectionItems, vendors, funds, loadData, setActiveTab }: SelectionTabProps) {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<ExternalSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedItems, setSelectedItems] = useState<number[]>([])
  const [showConvertModal, setShowConvertModal] = useState(false)
  const [convertVendorId, setConvertVendorId] = useState<number>(0)
  const [convertFundId, setConvertFundId] = useState<number>(0)
  const convertVendorSelectId = useId()
  const convertFundSelectId = useId()

  const handleExternalSearch = async () => {
    if (!token || !searchQuery.trim()) return
    setIsSearching(true)
    try {
      const data = await apiFetch<{ results: ExternalSearchResult[] }>(token, "/external-search?q=" + encodeURIComponent(searchQuery) + "&source=open_library")
      setSearchResults(data.results)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.selectionList.searchFailed'))
    } finally {
      setIsSearching(false)
    }
  }

  const handleAddToSelection = async (item: ExternalSearchResult) => {
    if (!token) return
    try {
      await apiFetch(token, "/selection-list", { method: "POST", body: JSON.stringify({ title: item.title, author: item.author, isbn: item.isbn, cover_url: item.cover_url, source: item.source, source_id: item.source_id }) })
      toast.success(t('toast.selectionTab.added'))
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleRemoveSelection = async (id: number) => {
    if (!token) return
    try {
      await apiFetch(token, "/selection-list/" + id, { method: "DELETE" })
      toast.success(t('toast.selectionTab.removed'))
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleConvertToPO = () => {
    if (!token || selectedItems.length === 0 || vendors.length === 0 || funds.length === 0) {
      toast.error(t('staffAcquisition.selectItemsAndEnsureVendors'))
      return
    }
    setConvertVendorId(vendors[0]?.id || 0)
    setConvertFundId(funds[0]?.id || 0)
    setShowConvertModal(true)
  }

  const handleConfirmConvertToPO = async () => {
    if (!token || convertVendorId === 0 || convertFundId === 0) {
      toast.error(t('staffAcquisition.pleaseSelectAVendorAnd'))
      return
    }
    try {
      await apiFetch(token, "/selection-list/convert-to-po", { method: "POST", body: JSON.stringify({ selection_item_ids: selectedItems, vendor_id: convertVendorId, fund_id: convertFundId }) })
      toast.success(t('toast.selectionTab.purchaseOrderCreated'))
      setSelectedItems([])
      setShowConvertModal(false)
      setActiveTab("orders")
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  return (
    <>
      <div className="space-y-6">
        <div className="space-y-4"><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Search Open Library</h2><div className="flex gap-2"><input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleExternalSearch()} placeholder={t('staffAcquisition.searchByTitleAuthorOr')} aria-label={t('staffAcquisition.searchByTitleAuthorOr2')} className="flex-1 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /><button onClick={handleExternalSearch} disabled={isSearching} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl font-medium flex items-center gap-2">{isSearching ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search aria-hidden="true" className="w-4 h-4" />}Search</button></div>{searchResults.length > 0 && <div className="border border-lsc-border dark:border-earth-700 rounded-xl divide-y divide-lsc-border dark:divide-earth-700 max-h-64 overflow-y-auto">{searchResults.map((result, idx) => (<div key={idx} className="p-3 flex items-center gap-4 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30">{result.cover_url && <img src={result.cover_url} alt={`Cover of ${result.title}`} className="w-10 h-14 object-cover rounded" />}<div className="flex-1 min-w-0"><p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={result.title ?? undefined}>{result.title}</p><p className="text-sm text-lsc-dark/70 truncate" title={result.author ?? undefined}>{result.author}</p></div><button onClick={() => handleAddToSelection(result)} className="px-3 py-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-xl flex items-center gap-1"><Plus aria-hidden="true" className="w-3 h-3" />Add</button></div>))}</div>}</div>
        <AcquisitionErrorBoundary fallbackMessage="Failed to load enrichment tools">
          <SelectionEnrichment token={token || ""} items={selectionItems} onRefresh={loadData} />
        </AcquisitionErrorBoundary>
        <div className="space-y-4"><div className="flex justify-between items-center"><h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Selection List ({selectionItems.length})</h2>{selectedItems.length > 0 && <button onClick={handleConvertToPO} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><ShoppingCart aria-hidden="true" className="w-4 h-4" />Create PO ({selectedItems.length})</button>}</div>{selectionItems.length === 0 ? <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffAcquisition.noItemsInSelectionList')}</p> : <div className="border border-lsc-border dark:border-earth-700 rounded-xl divide-y divide-lsc-border dark:divide-earth-700">{selectionItems.map((item) => (<div key={item.id} className="p-3 flex items-center gap-4"><input type="checkbox" checked={selectedItems.includes(item.id)} onChange={(e) => setSelectedItems(e.target.checked ? [...selectedItems, item.id] : selectedItems.filter((i) => i !== item.id))} className="w-4 h-4 rounded border-lsc-border text-lsc-rose" />{item.cover_url && <img src={item.cover_url} alt={`Cover of ${item.title}`} className="w-10 h-14 object-cover rounded" />}<div className="flex-1 min-w-0"><p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title ?? undefined}>{item.title}</p><p className="text-sm text-lsc-dark/70 truncate" title={item.author ?? undefined}>{item.author}</p><div className="flex gap-2 mt-1"><span className="text-xs px-2 py-0.5 bg-lsc-cream rounded">{item.priority}</span><span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.source}</span></div></div><button onClick={() => handleRemoveSelection(item.id)} className="p-2 text-lsc-dark/70 hover:text-status-danger-600 rounded-xl" aria-label={`Remove ${item.title} from selection`}><Trash2 aria-hidden="true" className="w-4 h-4" /></button></div>))}</div>}</div>
      </div>

      {showConvertModal && (
        <ModalBackdrop onClose={() => setShowConvertModal(false)} title="Create Purchase Order">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Create Purchase Order</h2>
              <button onClick={() => setShowConvertModal(false)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark rounded-xl" aria-label={t('aria.authModals.close')}><X aria-hidden="true" className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Creating PO from {selectedItems.length} selection item(s)
              </p>
              <div>
                <label htmlFor={convertVendorSelectId} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Vendor *</label>
                <select
                  id={convertVendorSelectId}
                  value={convertVendorId}
                  onChange={(e) => setConvertVendorId(parseInt(e.target.value))}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value={0}>Select vendor...</option>
                  {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor={convertFundSelectId} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">Fund *</label>
                <select
                  id={convertFundSelectId}
                  value={convertFundId}
                  onChange={(e) => setConvertFundId(parseInt(e.target.value))}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value={0}>Select fund...</option>
                  {funds.map(f => <option key={f.id} value={f.id}>{f.name} (Available: {formatMoney(f.available_amount)})</option>)}
                </select>
              </div>
              {/* Live fund-spend preview. SelectionItem.estimated_price is optional;
                  items without a price contribute 0 — TODO: surface "incomplete pricing"
                  hint when any selected item lacks estimated_price. */}
              <FundSpendPreview
                fund={funds.find(f => f.id === convertFundId) || null}
                newAmount={selectionItems
                  .filter(item => selectedItems.includes(item.id))
                  .reduce((sum, item) => sum + (Number(item.estimated_price) || 0), 0)}
                formatMoney={formatMoney}
              />
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button type="button" onClick={() => setShowConvertModal(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium">Cancel</button>
                <button onClick={handleConfirmConvertToPO} disabled={convertVendorId === 0 || convertFundId === 0} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"><ShoppingCart aria-hidden="true" className="w-4 h-4" />Create PO</button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}
