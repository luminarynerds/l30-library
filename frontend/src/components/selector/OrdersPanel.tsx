/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button } from '../ui'
import ConfirmDialog from '../ConfirmDialog'
import StatusBadge from '../acquisition/StatusBadge'
import { ShoppingCart, FileText, Mail, Package, Eye, EyeOff, Loader2 } from 'lucide-react'
import {
  getPurchaseOrders as getPOs,
  emailPurchaseOrderToVendor,
  submitPOForApproval,
} from '../../api/domains/admin/acquisition-po-api'
import type { PurchaseOrderResponse } from '../../api/domains/admin/acquisition-po-api'
import { useTranslation } from '@/i18n'

function formatCurrency(n: number | null | undefined): string {
  if (n == null) return '—'
  return `$${n.toFixed(2)}`
}

export function OrdersPanel() {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [showCompleted, setShowCompleted] = useState(false)
  const [emailTarget, setEmailTarget] = useState<PurchaseOrderResponse | null>(null)

  const { data: posData, isLoading } = useQuery({
    queryKey: ['selectors', 'orders'],
    queryFn: () => getPOs(),
  })

  const emailMut = useMutation({
    mutationFn: (poId: number) => emailPurchaseOrderToVendor(poId),
    onSuccess: () => {
      toast.success(t('selectorDashboard.poEmailedToVendor'))
      setEmailTarget(null)
      queryClient.invalidateQueries({ queryKey: ['selectors', 'orders'] })
    },
    onError: () => toast.error(t('selectorDashboard.failedToEmailVendor')),
  })

  const submitForApprovalMut = useMutation({
    mutationFn: (poId: number) => submitPOForApproval(poId),
    onSuccess: () => {
      toast.success(t('toast.selectorDashboard.submittedForApproval'))
      queryClient.invalidateQueries({ queryKey: ['selectors', 'orders'] })
    },
    onError: () => toast.error(t('toast.selectorDashboard.failedToSubmit')),
  })

  if (isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
  }

  const allOrders = posData?.items ?? []
  const activeStatuses = ['draft', 'pending_approval', 'approved', 'submitted', 'partially_received']
  const statusGroups: { label: string; statuses: string[] }[] = [
    { label: 'Drafts', statuses: ['draft'] },
    { label: 'Pending Approval', statuses: ['pending_approval'] },
    { label: 'Approved', statuses: ['approved'] },
    { label: 'Submitted / In Transit', statuses: ['submitted', 'partially_received'] },
  ]

  if (showCompleted) {
    statusGroups.push({ label: 'Completed', statuses: ['received', 'cancelled'] })
  }

  const filteredOrders = showCompleted ? allOrders : allOrders.filter(o => activeStatuses.includes(o.status))

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => setShowCompleted(prev => !prev)}
          className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
        >
          {showCompleted ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {showCompleted ? 'Hide completed' : 'Show completed'}
        </button>
      </div>

      {filteredOrders.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
          <ShoppingCart className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">No purchase orders</p>
          <p className="text-sm mt-1">{t('selectorDashboard.convertSelectionListItemsTo')}</p>
        </div>
      ) : (
        statusGroups.map(group => {
          const groupOrders = allOrders.filter(o => group.statuses.includes(o.status))
          if (groupOrders.length === 0) return null
          return (
            <div key={group.label}>
              <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{group.label}</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {groupOrders.map(po => (
                  <div
                    key={po.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{po.po_number}</p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{po.vendor_name ?? 'No vendor'}</p>
                      </div>
                      <StatusBadge status={po.status} size="sm" />
                    </div>
                    <div className="flex items-center justify-between text-sm mb-3">
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/60">{po.total_items} items</span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{formatCurrency(po.total_amount)}</span>
                    </div>
                    <div className="flex gap-2">
                      {po.status === 'draft' && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => submitForApprovalMut.mutate(po.id)}
                          isLoading={submitForApprovalMut.isPending && submitForApprovalMut.variables === po.id}
                          leftIcon={<FileText className="w-3.5 h-3.5" />}
                          fullWidth
                        >
                          Submit for Approval
                        </Button>
                      )}
                      {po.status === 'approved' && (
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => setEmailTarget(po)}
                          leftIcon={<Mail className="w-3.5 h-3.5" />}
                          fullWidth
                        >
                          Send to Vendor
                        </Button>
                      )}
                      {po.status === 'submitted' && (
                        <Button
                          size="sm"
                          variant="secondary"
                          leftIcon={<Package className="w-3.5 h-3.5" />}
                          fullWidth
                          disabled
                        >
                          Receive (use Acquisitions page)
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })
      )}

      {/* ─── Email vendor confirm ────────────────────────────── */}
      <ConfirmDialog
        isOpen={!!emailTarget}
        title="Send to Vendor"
        message={`Email PO ${emailTarget?.po_number ?? ''} to ${emailTarget?.vendor_name ?? 'vendor'}?`}
        confirmText="Yes, send"
        confirmVariant="primary"
        onConfirm={() => { if (emailTarget) emailMut.mutate(emailTarget.id) }}
        onCancel={() => setEmailTarget(null)}
        loading={emailMut.isPending}
      />
    </div>
  )
}
