/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { X, Plus, Edit2, Trash2, Save, Search, AlertTriangle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../ConfirmDialog'
import FundSpendPreview from './FundSpendPreview'
import { formatMoney } from '@/pages/StaffAcquisitionPage/types'
import { lookupISBN } from '@/api/acquisition-api'
import { validatePOBudget } from '@/api/domains/admin/acquisition-po-api'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import EDIHistorySection from './edi/EDIHistorySection'

interface PurchaseOrderItem {
  id: number
  title: string
  author: string | null
  isbn: string | null
  quantity: number
  unit_price: number
  notes: string | null
  backordered_quantity: number | null
  expected_ship_date: string | null
}

function formatShipDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

interface PurchaseOrderDetail {
  id: number
  po_number: string
  vendor_id: number | null
  vendor_name: string | null
  fund_id: number | null
  fund_name: string | null
  status: string
  total_amount: number
  notes: string | null
  items: PurchaseOrderItem[]
  created_by_id: number
}

interface Fund {
  id: number
  code: string
  name: string
  available_amount: number
}

interface Vendor {
  id: number
  name: string
}

interface EditPurchaseOrderModalProps {
  isOpen: boolean
  onClose: () => void
  purchaseOrder: PurchaseOrderDetail
  funds: Fund[]
  vendors: Vendor[]
  token: string
  onUpdate: () => void
}

interface LineItemFormData {
  title: string
  author: string
  isbn: string
  quantity: number
  unit_price: number
  notes: string
}

export default function EditPurchaseOrderModal({
  isOpen,
  onClose,
  purchaseOrder,
  funds,
  vendors,
  token: _token,
  onUpdate
}: EditPurchaseOrderModalProps) {
  const { t } = useTranslation()
  const [poData, setPoData] = useState({
    vendor_id: purchaseOrder.vendor_id || 0,
    fund_id: purchaseOrder.fund_id || 0,
    notes: purchaseOrder.notes || ''
  })

  const [editingItemId, setEditingItemId] = useState<number | null>(null)
  const [showAddItem, setShowAddItem] = useState(false)
  const [itemFormData, setItemFormData] = useState<LineItemFormData>({
    title: '',
    author: '',
    isbn: '',
    quantity: 1,
    unit_price: 0,
    notes: ''
  })

  const [loading, setLoading] = useState(false)
  const [deleteLineItemConfirm, setDeleteLineItemConfirm] = useState<{ id: number; title: string } | null>(null)
  const [isbnLoading, setIsbnLoading] = useState(false)
  const [budgetWarning, setBudgetWarning] = useState<{ level: string; message: string } | null>(null)

  const isEditable = purchaseOrder.status === 'draft'

  // Live fund-spend preview: sum of pending line items (server-side state),
  // compared against currently selected fund's available balance.
  const selectedFund = funds.find((f) => f.id === poData.fund_id) || null
  const newAmount = purchaseOrder.items.reduce(
    (sum, item) => sum + (Number(item.quantity) || 0) * (Number(item.unit_price) || 0),
    0
  )

  const runBudgetValidation = useCallback(async () => {
    if (!purchaseOrder.fund_id || purchaseOrder.fund_id === 0) {
      setBudgetWarning(null)
      return
    }
    try {
      const result = await validatePOBudget(purchaseOrder.id)
      if (result.warning_level === 'none') {
        setBudgetWarning(null)
      } else {
        setBudgetWarning({ level: result.warning_level, message: result.message })
      }
    } catch {
      // Silent — budget validation is advisory
    }
  }, [purchaseOrder.id, purchaseOrder.fund_id])

  useEffect(() => {
    if (!isEditable) {
      toast.error(t('components.acquisition.editPurchaseOrder.onlyPurchaseOrdersInDraft'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditable])

  useEffect(() => {
    if (isOpen && purchaseOrder.fund_id && purchaseOrder.fund_id > 0) {
      runBudgetValidation()
    }
  }, [isOpen, purchaseOrder.fund_id, runBudgetValidation])

  const resetItemForm = () => {
    setItemFormData({
      title: '',
      author: '',
      isbn: '',
      quantity: 1,
      unit_price: 0,
      notes: ''
    })
  }

  const handleISBNLookup = async () => {
    const rawIsbn = itemFormData.isbn.replace(/[-\s]/g, '')
    if (rawIsbn.length < 10) {
      toast.error(t('components.acquisition.editPurchaseOrder.enterAValidIsbnOr'))
      return
    }
    setIsbnLoading(true)
    try {
      const data = await lookupISBN(rawIsbn)
      if (data.success && data.result) {
        const r = data.result
        setItemFormData(prev => ({
          ...prev,
          title: r.title || prev.title,
          author: r.author || prev.author,
          unit_price: r.estimated_price || prev.unit_price,
          isbn: r.isbn_13 || r.isbn_10 || prev.isbn,
        }))
        toast.success(t('toast.acquisition.foundTitleByAuthor', { title: r.title, author: r.author }))
        if (r.previously_ordered) {
          toast(`Previously ordered on PO(s): ${r.previous_po_numbers.join(', ')}`, { icon: '⚠️' })
        }
        if (r.in_catalog) {
          toast(t('components.acquisition.editPurchaseOrder.thisItemIsAlreadyIn'), { icon: 'ℹ️' })
        }
      } else {
        toast.error(data.error || t('toast.acquisition.isbnNotFoundInExternal'))
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffMangaCataloging.isbnLookupFailed'))
    } finally {
      setIsbnLoading(false)
    }
  }

  const handleSavePOMetadata = async () => {
    setLoading(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${purchaseOrder.id}`, {
        method: 'PATCH',
        body: JSON.stringify(poData)
      })

      toast.success(t('components.acquisition.editPurchaseOrder.purchaseOrderUpdatedSuccessfully'))
      onUpdate()
      if (poData.fund_id > 0) {
        runBudgetValidation()
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.acquisition.unableToUpdatePurchaseOrder'))
    } finally {
      setLoading(false)
    }
  }

  const handleAddLineItem = async () => {
    if (!itemFormData.title.trim()) {
      toast.error(t('toast.acquisition.titleIsRequired'))
      return
    }

    setLoading(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${purchaseOrder.id}/items`, {
        method: 'POST',
        body: JSON.stringify(itemFormData)
      })

      toast.success(t('components.acquisition.editPurchaseOrder.lineItemAddedSuccessfully'))
      setShowAddItem(false)
      resetItemForm()
      onUpdate()
      runBudgetValidation()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.acquisition.unableToAddItemPlease'))
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateLineItem = async (itemId: number) => {
    setLoading(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${purchaseOrder.id}/items/${itemId}`, {
        method: 'PATCH',
        body: JSON.stringify(itemFormData)
      })

      toast.success(t('components.acquisition.editPurchaseOrder.lineItemUpdatedSuccessfully'))
      setEditingItemId(null)
      resetItemForm()
      onUpdate()
      runBudgetValidation()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.acquisition.unableToUpdateItemPlease'))
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteLineItem = async (itemId: number) => {
    setLoading(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${purchaseOrder.id}/items/${itemId}`, {
        method: 'DELETE',
      })

      toast.success(t('components.acquisition.editPurchaseOrder.lineItemDeletedSuccessfully'))
      setDeleteLineItemConfirm(null)
      onUpdate()
      runBudgetValidation()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.acquisition.unableToDeleteItemPlease'))
    } finally {
      setLoading(false)
    }
  }

  const startEditingItem = (item: PurchaseOrderItem) => {
    setEditingItemId(item.id)
    setItemFormData({
      title: item.title || '',
      author: item.author || '',
      isbn: item.isbn || '',
      quantity: item.quantity,
      unit_price: item.unit_price,
      notes: item.notes || ''
    })
  }

  const cancelEditingItem = () => {
    setEditingItemId(null)
    resetItemForm()
  }

  const isbnLookupButton = (
    <button
      type="button"
      onClick={handleISBNLookup}
      disabled={isbnLoading || !itemFormData.isbn.replace(/[-\s]/g, '').length}
      className="p-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-dark/20 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
      title="Lookup ISBN"
    >
      {isbnLoading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
    </button>
  )

  if (!isOpen) return null

  return (
    <ModalBackdrop onClose={onClose} title="Edit Purchase Order">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-5xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Edit Purchase Order {purchaseOrder.po_number}
            </h2>
            {!isEditable && (
              <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">
                This PO cannot be edited (Status: {purchaseOrder.status.replace('_', ' ').toUpperCase()})
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* PO Metadata Section */}
          <div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Purchase Order Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="po-vendor-select" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Vendor
                </label>
                <select
                  id="po-vendor-select"
                  value={poData.vendor_id}
                  onChange={(e) => setPoData({ ...poData, vendor_id: parseInt(e.target.value) })}
                  disabled={!isEditable || loading}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                >
                  <option value={0}>Select vendor...</option>
                  {vendors.map(v => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="po-fund-select" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Fund
                </label>
                <select
                  id="po-fund-select"
                  value={poData.fund_id}
                  onChange={(e) => setPoData({ ...poData, fund_id: parseInt(e.target.value) })}
                  disabled={!isEditable || loading}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                >
                  <option value={0}>Select fund...</option>
                  {funds.map(f => (
                    <option key={f.id} value={f.id}>{f.name} (Available: ${Number(f.available_amount).toFixed(2)})</option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
                  Notes
                </label>
                <textarea
                  value={poData.notes}
                  onChange={(e) => setPoData({ ...poData, notes: e.target.value })}
                  disabled={!isEditable || loading}
                  rows={3}
                  className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                />
              </div>
            </div>

            <button
              onClick={handleSavePOMetadata}
              disabled={!isEditable || loading}
              className="mt-4 flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              Save PO Information
            </button>

            <div className="mt-4">
              <FundSpendPreview fund={selectedFund} newAmount={newAmount} formatMoney={formatMoney} />
            </div>
          </div>

          {/* Budget Warning */}
          {budgetWarning && (
            <div className={`flex items-start gap-3 p-4 rounded-xl border ${
              budgetWarning.level === 'danger'
                ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800'
                : 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800'
            }`}>
              <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                budgetWarning.level === 'danger'
                  ? 'text-status-danger-600 dark:text-status-danger-400'
                  : 'text-status-warning-600 dark:text-status-warning-400'
              }`} />
              <div>
                <p className={`text-sm font-medium ${
                  budgetWarning.level === 'danger'
                    ? 'text-status-danger-800 dark:text-status-danger-300'
                    : 'text-status-warning-800 dark:text-status-warning-300'
                }`}>
                  {budgetWarning.level === 'danger' ? 'Budget Exceeded' : 'Budget Warning'}
                </p>
                <p className={`text-sm mt-0.5 ${
                  budgetWarning.level === 'danger'
                    ? 'text-status-danger-700 dark:text-status-danger-400'
                    : 'text-status-warning-700 dark:text-status-warning-400'
                }`}>
                  {budgetWarning.message}
                </p>
              </div>
            </div>
          )}

          <hr className="border-lsc-border dark:border-earth-700" />

          {/* EDI History Section — silently renders nothing when this PO has no EDI activity */}
          <EDIHistorySection poId={purchaseOrder.id} />

          {/* Line Items Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Line Items</h3>
              <button
                onClick={() => setShowAddItem(true)}
                disabled={!isEditable || loading || showAddItem}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-4 h-4" />
                Add Item
              </button>
            </div>

            {/* Add Item Form */}
            {showAddItem && (
              <div className="mb-4 p-4 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-cream dark:bg-lsc-brown">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Add New Item</h4>
                <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
                  <div className="md:col-span-2">
                    <input
                      type="text"
                      placeholder={t('placeholder.acquisition.title')}
                      value={itemFormData.title}
                      onChange={(e) => setItemFormData({ ...itemFormData, title: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder={t('placeholder.acquisition.author')}
                      value={itemFormData.author}
                      onChange={(e) => setItemFormData({ ...itemFormData, author: e.target.value })}
                      className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                    />
                  </div>
                  <div className="flex gap-1">
                    <input
                      type="text"
                      placeholder={t('placeholder.acquisition.isbn')}
                      value={itemFormData.isbn}
                      onChange={(e) => setItemFormData({ ...itemFormData, isbn: e.target.value })}
                      onBlur={() => {
                        if (itemFormData.isbn.replace(/[-\s]/g, '').length >= 10 && !itemFormData.title) {
                          handleISBNLookup()
                        }
                      }}
                      className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                    />
                    {isbnLookupButton}
                  </div>
                  <div>
                    <input
                      type="number"
                      placeholder={t('placeholder.acquisition.qty')}
                      min="1"
                      value={itemFormData.quantity}
                      onChange={(e) => setItemFormData({ ...itemFormData, quantity: parseInt(e.target.value) || 1 })}
                      className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                    />
                  </div>
                  <div>
                    <input
                      type="number"
                      placeholder={t('placeholder.acquisition.price')}
                      min="0"
                      step="0.01"
                      value={itemFormData.unit_price}
                      onChange={(e) => setItemFormData({ ...itemFormData, unit_price: parseFloat(e.target.value) || 0 })}
                      className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                    />
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={handleAddLineItem}
                    disabled={loading}
                    className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm disabled:opacity-50"
                  >
                    Save Item
                  </button>
                  <button
                    onClick={() => { setShowAddItem(false); resetItemForm(); }}
                    className="px-4 py-2 bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Line Items Table */}
            <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Title</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Author</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">ISBN</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Qty</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Price</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Total</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {purchaseOrder.items.map((item) => (
                    editingItemId === item.id ? (
                      <tr key={item.id} className="bg-lsc-cream dark:bg-lsc-brown">
                        <td colSpan={7} className="p-4">
                          <div className="grid grid-cols-6 gap-3">
                            <div className="col-span-2">
                              <input
                                type="text"
                                value={itemFormData.title}
                                onChange={(e) => setItemFormData({ ...itemFormData, title: e.target.value })}
                                className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              />
                            </div>
                            <div>
                              <input
                                type="text"
                                value={itemFormData.author}
                                onChange={(e) => setItemFormData({ ...itemFormData, author: e.target.value })}
                                className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              />
                            </div>
                            <div className="flex gap-1">
                              <input
                                type="text"
                                value={itemFormData.isbn}
                                onChange={(e) => setItemFormData({ ...itemFormData, isbn: e.target.value })}
                                className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              />
                              {isbnLookupButton}
                            </div>
                            <div>
                              <input
                                type="number"
                                min="1"
                                value={itemFormData.quantity}
                                onChange={(e) => setItemFormData({ ...itemFormData, quantity: parseInt(e.target.value) || 1 })}
                                className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              />
                            </div>
                            <div>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={itemFormData.unit_price}
                                onChange={(e) => setItemFormData({ ...itemFormData, unit_price: parseFloat(e.target.value) || 0 })}
                                className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              />
                            </div>
                          </div>
                          <div className="mt-3 flex gap-2">
                            <button
                              onClick={() => handleUpdateLineItem(item.id)}
                              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm"
                            >
                              Save
                            </button>
                            <button
                              onClick={cancelEditingItem}
                              className="px-4 py-2 bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      <tr key={item.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown">
                        <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">
                          {item.title}
                          {item.backordered_quantity != null && item.backordered_quantity > 0 && (
                            <div className="mt-1 flex items-center gap-1 text-xs text-status-warning-700 dark:text-status-warning-300">
                              <AlertTriangle className="w-3 h-3 shrink-0" aria-hidden="true" />
                              <span>
                                {item.expected_ship_date
                                  ? t('acquisitionsBackorder.lineNoteWithDate', {
                                      quantity: item.backordered_quantity,
                                      date: formatShipDate(item.expected_ship_date),
                                      defaultValue: `${item.backordered_quantity} backordered, expected ${formatShipDate(item.expected_ship_date)}`,
                                    })
                                  : t('acquisitionsBackorder.lineNoteNoDate', {
                                      quantity: item.backordered_quantity,
                                      defaultValue: `${item.backordered_quantity} backordered`,
                                    })}
                              </span>
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{item.author || '-'}</td>
                        <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{item.isbn || '-'}</td>
                        <td className="px-4 py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">{item.quantity}</td>
                        <td className="px-4 py-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">${Number(item.unit_price).toFixed(2)}</td>
                        <td className="px-4 py-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream">
                          ${(item.quantity * Number(item.unit_price)).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <button
                              onClick={() => startEditingItem(item)}
                              disabled={!isEditable || loading || editingItemId !== null}
                              className="p-2 text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-dark/20 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setDeleteLineItemConfirm({ id: item.id, title: item.title })}
                              disabled={!isEditable || loading}
                              className="p-2 text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  ))}

                  {purchaseOrder.items.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                        No line items yet. Click "Add Item" to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Total */}
            <div className="mt-4 flex justify-end">
              <div className="text-right">
                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Amount</div>
                <div className="text-2xl font-bold text-lsc-rose">${Number(purchaseOrder.total_amount).toFixed(2)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-lsc-white dark:bg-earth-800 border-t border-lsc-border dark:border-earth-700 p-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-lsc-cream hover:bg-lsc-border dark:bg-lsc-brown dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium"
          >
            Close
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!deleteLineItemConfirm}
        title="Delete Line Item?"
        message={`Are you sure you want to delete "${deleteLineItemConfirm?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteLineItemConfirm) handleDeleteLineItem(deleteLineItemConfirm.id) }}
        onCancel={() => setDeleteLineItemConfirm(null)}
        loading={loading}
      />
    </ModalBackdrop>
  )
}