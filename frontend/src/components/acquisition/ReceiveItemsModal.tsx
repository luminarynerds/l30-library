/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { X, Package, AlertCircle, CheckCircle2 } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { fetchApi } from '@/api/fetchApi'

interface POItem {
  id: number
  title: string
  author: string | null
  isbn: string | null
  quantity: number
  unit_price: number
  received_quantity: number
  notes: string | null
}

interface PurchaseOrder {
  id: number
  po_number: string
  vendor_name: string | null
  fund_name: string | null
  total_items: number
  total_amount: number
  items: POItem[]
}

interface ReceiveItemsModalProps {
  po: PurchaseOrder
  token: string
  onClose: () => void
  onSuccess: () => void
}

export default function ReceiveItemsModal({ po, token, onClose, onSuccess }: ReceiveItemsModalProps) {
  const { t } = useTranslation()
  const [receivedQuantities, setReceivedQuantities] = useState<Record<number, number>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [_allReceived, setAllReceived] = useState(false)

  // Initialize received quantities from current state
  useEffect(() => {
    const initial: Record<number, number> = {}
    po.items.forEach((item) => {
      initial[item.id] = item.received_quantity
    })
    setReceivedQuantities(initial)
  }, [po])

  const handleQuantityChange = (itemId: number, value: string) => {
    const qty = Math.max(0, Math.min(parseInt(value) || 0, (po.items.find((i) => i.id === itemId)?.quantity ?? 0) - (po.items.find((i) => i.id === itemId)?.received_quantity ?? 0)))
    setReceivedQuantities((prev) => ({ ...prev, [itemId]: qty }))
  }

  const handleReceiveAll = () => {
    const updated: Record<number, number> = {}
    po.items.forEach((item) => {
      updated[item.id] = item.quantity
    })
    setReceivedQuantities(updated)
    setAllReceived(true)
  }

  const handleSubmit = async () => {
    if (!token) return

    const items = po.items
      .filter((item) => (receivedQuantities[item.id] ?? 0) > item.received_quantity)
      .map((item) => ({
        item_id: item.id,
        received_quantity: receivedQuantities[item.id] ?? 0,
      }))

    if (items.length === 0) {
      toast.error(t('components.acquisition.receiveItems.noItemsToReceive'))
      return
    }

    setIsSubmitting(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${po.id}/receive`, {
        method: "PATCH",
        body: JSON.stringify({ items }),
      })
      toast.success(t('toast.itemsReceived'))
      onSuccess()
      onClose()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToReceiveItems'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const totalReceiving = po.items.reduce((sum, item) => sum + Math.max(0, (receivedQuantities[item.id] ?? 0) - item.received_quantity) * Number(item.unit_price), 0)
  const anyChanges = po.items.some((item) => (receivedQuantities[item.id] ?? 0) > item.received_quantity)
  const remainingItems = po.items.filter((item) => item.received_quantity < item.quantity)

  return (
    <ModalBackdrop onClose={onClose} title="Receive Items">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-lsc-cream dark:bg-lsc-brown/50 border-b border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Package className="w-5 h-5 text-lsc-rose" />
            <div>
              <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Receive Items</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{po.po_number} - {po.vendor_name}</p>
            </div>
          </div>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] hover:bg-lsc-border dark:hover:bg-earth-700 rounded-lg transition-colors" aria-label={t('aria.authModals.close')}>
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {remainingItems.length === 0 ? (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-4 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-status-success-600" />
              <div>
                <p className="font-medium text-status-success-900 dark:text-status-success-100">All items received</p>
                <p className="text-sm text-status-success-800 dark:text-status-success-200">{t('components.acquisition.receiveItems.thisPurchaseOrderHasBeen')}</p>
              </div>
            </div>
          ) : (
            <>
              <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                <div>
                  <p className="font-medium text-earth-900 dark:text-earth-200">{remainingItems.length} items awaiting delivery</p>
                  <p className="text-sm text-earth-800 dark:text-lsc-rose-light/80">{t('components.acquisition.receiveItems.enterQuantitiesReceivedToUpdate')}</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Items to Receive</h3>
                  {remainingItems.length > 0 && (
                    <button onClick={handleReceiveAll} className="text-sm px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors">
                      Receive All
                    </button>
                  )}
                </div>

                <div className="border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Ordered</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Already Recv'd</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Receive Now</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Unit Price</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Line Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                      {remainingItems.map((item) => {
                        const remaining = item.quantity - item.received_quantity
                        const nowReceiving = (receivedQuantities[item.id] ?? 0) - item.received_quantity
                        const lineTotal = nowReceiving * Number(item.unit_price)
                        return (
                          <tr key={item.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/30">
                            <td className="px-4 py-3">
                              <div>
                                <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={item.title}>{item.title}</p>
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.author}</p>
                                {item.isbn && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.isbn}</p>}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-center font-medium">{item.quantity}</td>
                            <td className="px-4 py-3 text-center text-lsc-dark/70 dark:text-lsc-cream/70">{item.received_quantity}</td>
                            <td className="px-4 py-3">
                              <input
                                type="number"
                                min="0"
                                max={remaining}
                                value={nowReceiving}
                                onChange={(e) => handleQuantityChange(item.id, e.target.value)}
                                disabled={remaining === 0}
                                className="w-16 px-2 py-1.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-center font-medium disabled:opacity-50"
                              />
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-sm">${Number(item.unit_price).toFixed(2)}</td>
                            <td className="px-4 py-3 text-right font-medium">${lineTotal.toFixed(2)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {anyChanges && (
                <div className="bg-lsc-cream dark:bg-lsc-brown/50 border border-lsc-border dark:border-earth-700 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.acquisition.receiveItems.costOfItemsBeingReceived')}</p>
                      <p className="text-lg font-semibold text-lsc-rose">${totalReceiving.toFixed(2)}</p>
                    </div>
                    <div className="text-right text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <p>Budget Impact:</p>
                      <p className="text-lsc-dark dark:text-lsc-cream font-medium">Encumbered → Spent</p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="sticky bottom-0 bg-lsc-cream dark:bg-lsc-brown/50 border-t border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-700 rounded-lg font-medium transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!anyChanges || isSubmitting}
            className="flex items-center gap-2 px-6 py-2 bg-status-success-600 hover:bg-status-success-700 disabled:bg-lsc-dark/50 text-white rounded-lg font-medium transition-colors"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full motion-safe:animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Complete Receive
              </>
            )}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
