/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { Button } from '../ui'
import ConfirmDialog from '../ConfirmDialog'
import { ListChecks, ShoppingCart, Trash2, Loader2 } from 'lucide-react'
import {
  getSelectionList,
  removeFromSelectionList,
  convertSelectionToPO,
  lookupISBN,
  getVendors,
  getFunds,
} from '../../api/domains/admin/acquisition-api'
import type { SelectionListItem } from '../../api/domains/admin/acquisition-api'
import { useTranslation, getCurrentLocale } from '@/i18n'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatCurrency(n: number | null | undefined): string {
  if (n == null) return '—'
  return `$${n.toFixed(2)}`
}

export function SelectionListPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const [showConvertModal, setShowConvertModal] = useState(false)
  const [convertVendor, setConvertVendor] = useState<number | null>(null)
  const [convertFund, setConvertFund] = useState<number | null>(null)
  const [removeTarget, setRemoveTarget] = useState<SelectionListItem | null>(null)

  const { data: selData, isLoading } = useQuery({
    queryKey: ['selectors', 'selection-list', priorityFilter],
    queryFn: () => getSelectionList(priorityFilter ? { priority: priorityFilter, per_page: 200 } : { per_page: 200 }),
  })

  const { data: vendorsData } = useQuery({
    queryKey: ['selectors', 'vendors'],
    queryFn: () => getVendors({ status: 'active' }),
    enabled: showConvertModal,
  })

  const { data: fundsData } = useQuery({
    queryKey: ['selectors', 'funds'],
    queryFn: () => getFunds({ status: 'active' }),
    enabled: showConvertModal,
  })

  // Price lookups for items with ISBNs
  const itemsWithIsbn = useMemo(
    () => (selData?.items ?? []).filter(i => i.isbn && !i.price),
    [selData]
  )
  const isbnList = useMemo(() => itemsWithIsbn.map(i => i.isbn!), [itemsWithIsbn])

  const { data: priceLookups } = useQuery({
    queryKey: ['selectors', 'price-lookups', isbnList],
    queryFn: async () => {
      const results: Record<string, number | null> = {}
      await Promise.all(
        isbnList.map(async isbn => {
          try {
            const resp = await lookupISBN(isbn)
            results[isbn] = resp.result?.estimated_price ?? null
          } catch { /* skip */ }
        })
      )
      return results
    },
    enabled: isbnList.length > 0,
    staleTime: 5 * 60 * 1000,
  })

  const removeMut = useMutation({
    mutationFn: (id: number) => removeFromSelectionList(id),
    onSuccess: () => {
      toast.success(t('toast.selectionList.itemRemoved'))
      setRemoveTarget(null)
      setSelected(prev => { const next = new Set(prev); next.delete(removeMut.variables!); return next })
      queryClient.invalidateQueries({ queryKey: ['selectors'] })
    },
    onError: () => toast.error(t('toast.shelf.failedToRemove')),
  })

  const convertMut = useMutation({
    mutationFn: () =>
      convertSelectionToPO({
        selection_item_ids: Array.from(selected),
        vendor_id: convertVendor!,
        fund_id: convertFund!,
      }),
    onSuccess: data => {
      toast.success(t('toast.selectorDashboard.purchaseOrderCreatedPoPurchaseorderid', { purchaseorderid: data.po_number }))
      setShowConvertModal(false)
      setSelected(new Set())
      setConvertVendor(null)
      setConvertFund(null)
      queryClient.invalidateQueries({ queryKey: ['selectors'] })
    },
    onError: () => toast.error(t('selectorDashboard.failedToConvertToPo')),
  })

  const items = selData?.items ?? []
  const allSelected = items.length > 0 && selected.size === items.length

  const toggleAll = () => {
    if (allSelected) setSelected(new Set())
    else setSelected(new Set(items.map(i => i.id)))
  }

  const toggleOne = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const getPrice = (item: SelectionListItem): number | null => {
    if (item.price != null) return item.price
    if (item.isbn && priceLookups?.[item.isbn] != null) return priceLookups[item.isbn] ?? null
    return null
  }

  const selectedItems = items.filter(i => selected.has(i.id))
  const runningTotal = selectedItems.reduce((sum, i) => sum + (getPrice(i) ?? 0), 0)

  if (isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
  }

  return (
    <div className="space-y-4">
      {/* ─── Toolbar ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <select
            value={priorityFilter}
            onChange={e => setPriorityFilter(e.target.value)}
            className="rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 px-3 py-1.5 text-sm text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All priorities</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
        </div>

        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {selected.size} selected
            </span>
            <Button
              size="sm"
              variant="primary"
              onClick={() => setShowConvertModal(true)}
              leftIcon={<ShoppingCart className="w-3.5 h-3.5" />}
            >
              Convert to PO
            </Button>
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                if (selected.size === 1) {
                  const item = items.find(i => i.id === Array.from(selected)[0])
                  if (item) setRemoveTarget(item)
                }
              }}
              disabled={selected.size !== 1}
              leftIcon={<Trash2 className="w-3.5 h-3.5" />}
            >
              Remove
            </Button>
          </div>
        )}
      </div>

      {/* ─── Table ───────────────────────────────────────────── */}
      {items.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
          <ListChecks className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">{t('selectorDashboard.selectionListIsEmpty')}</p>
          <p className="text-sm mt-1">{t('selectorDashboard.addItemsFromPatronRequests')}</p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                  />
                </th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Source</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Priority</th>
                <th className="text-right px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Price</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Added</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const price = getPrice(item)
                return (
                  <tr
                    key={item.id}
                    className={`border-b border-earth-100 dark:border-earth-700/50 transition-colors ${
                      selected.has(item.id) ? 'bg-lsc-rose/5 dark:bg-lsc-rose/10' : 'hover:bg-earth-50 dark:hover:bg-earth-700/30'
                    }`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(item.id)}
                        onChange={() => toggleOne(item.id)}
                        className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{item.author ?? '—'}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">{item.isbn ?? '—'}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60 text-xs">{item.source ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        item.priority === 'high' ? 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'
                          : item.priority === 'low' ? 'bg-earth-200 dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70'
                          : 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
                      }`}>
                        {item.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-lsc-dark dark:text-lsc-cream">
                      {price != null ? formatCurrency(price) : (
                        <span className="text-lsc-dark/30 dark:text-lsc-cream/60">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60">{formatDate(item.requested_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ─── Running total sticky bar ────────────────────────── */}
      {selected.size > 0 && (
        <div className="sticky bottom-4 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center justify-between shadow-lg">
          <span className="text-sm text-lsc-dark dark:text-lsc-cream">
            <strong>{selected.size}</strong> items selected
          </span>
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            Est. total: <strong className="text-lsc-rose">{formatCurrency(runningTotal)}</strong>
          </span>
        </div>
      )}

      {/* ─── Convert to PO modal ─────────────────────────────── */}
      <Modal
        isOpen={showConvertModal}
        onClose={() => setShowConvertModal(false)}
        title={t('selectorDashboard.convertToPurchaseOrder')}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowConvertModal(false)}>Cancel</Button>
            <Button
              onClick={() => convertMut.mutate()}
              isLoading={convertMut.isPending}
              disabled={!convertVendor || !convertFund}
            >
              Create Purchase Order
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Creating a PO for {selected.size} item{selected.size > 1 ? 's' : ''} ({formatCurrency(runningTotal)} estimated)
          </p>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Vendor</label>
            <select
              value={convertVendor ?? ''}
              onChange={e => setConvertVendor(Number(e.target.value) || null)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">Select vendor...</option>
              {(vendorsData?.items ?? []).map(v => (
                <option key={v.id} value={v.id}>{v.name} ({v.code})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Fund</label>
            <select
              value={convertFund ?? ''}
              onChange={e => setConvertFund(Number(e.target.value) || null)}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <option value="">Select fund...</option>
              {(fundsData?.items ?? []).map(f => (
                <option key={f.id} value={f.id}>{f.name} ({f.code}) — {formatCurrency(f.available_amount)} avail</option>
              ))}
            </select>
          </div>
        </div>
      </Modal>

      {/* ─── Remove confirm ──────────────────────────────────── */}
      <ConfirmDialog
        isOpen={!!removeTarget}
        title="Remove Item"
        message={`Remove "${removeTarget?.title}" from selection list?`}
        confirmText="Yes, remove"
        confirmVariant="danger"
        onConfirm={() => { if (removeTarget) removeMut.mutate(removeTarget.id) }}
        onCancel={() => setRemoveTarget(null)}
      />
    </div>
  )
}
