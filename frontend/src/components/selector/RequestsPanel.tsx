/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { Button } from '../ui'
import { Inbox, X, Plus, Loader2 } from 'lucide-react'
import {
  getReviewQueue,
  approveRequest,
  declineRequest,
  getDeclineTemplates,
} from '../../api/purchase-requests-api'
import type { PurchaseRequestStaff } from '../../api/purchase-requests-api'
import {
  getSelectionList,
  addToSelectionList,
  checkISBNInCatalog,
} from '../../api/domains/admin/acquisition-api'
import type { CatalogCheckResult } from '../../api/domains/admin/acquisition-api'
import { useTranslation, getCurrentLocale } from '@/i18n'

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: 'numeric' })
}

export function RequestsPanel({ token }: { token: string | null }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [declineTarget, setDeclineTarget] = useState<PurchaseRequestStaff | null>(null)
  const [declineReason, setDeclineReason] = useState('')

  const { data: queue, isLoading } = useQuery({
    queryKey: ['selectors', 'requests', page],
    queryFn: () => getReviewQueue(token!, page, 'pending'),
    enabled: !!token,
  })

  const { data: templates } = useQuery({
    queryKey: ['selectors', 'decline-templates'],
    queryFn: () => getDeclineTemplates(token!),
    enabled: !!token && !!declineTarget,
  })

  // Selection list for dup checking
  const { data: selList } = useQuery({
    queryKey: ['selectors', 'selection-list'],
    queryFn: () => getSelectionList({ per_page: 200 }),
  })

  // Catalog dup checks for visible ISBNs
  const visibleIsbns = useMemo(
    () => (queue?.items ?? []).map(r => r.isbn).filter((isbn): isbn is string => !!isbn),
    [queue]
  )

  const { data: catalogChecks } = useQuery({
    queryKey: ['selectors', 'catalog-checks', visibleIsbns],
    queryFn: async () => {
      const results: Record<string, CatalogCheckResult> = {}
      await Promise.all(
        visibleIsbns.map(async isbn => {
          try {
            results[isbn] = await checkISBNInCatalog(isbn)
          } catch { /* skip */ }
        })
      )
      return results
    },
    enabled: visibleIsbns.length > 0,
    staleTime: 60_000,
  })

  // Check selection list for dups client-side
  const onSelectionList = useMemo(() => {
    const titles = new Set((selList?.items ?? []).map(i => i.title.toLowerCase()))
    const isbns = new Set((selList?.items ?? []).filter(i => i.isbn).map(i => i.isbn!))
    return (req: PurchaseRequestStaff) => {
      if (req.isbn && isbns.has(req.isbn)) return true
      return titles.has(req.title.toLowerCase())
    }
  }, [selList])

  const quickAddMut = useMutation({
    mutationFn: async (req: PurchaseRequestStaff) => {
      await approveRequest(req.id, token!)
      const data: Parameters<typeof addToSelectionList>[0] = {
        title: req.title,
        source: 'patron_request',
        notes: `From patron request #${req.id}`,
      }
      if (req.author) data.author = req.author
      if (req.isbn) data.isbn = req.isbn
      if (req.publisher) data.publisher = req.publisher
      if (req.publication_year) data.publication_year = req.publication_year
      return addToSelectionList(data)
    },
    onSuccess: () => {
      toast.success(t('selectorDashboard.approvedAndAddedToSelection'))
      queryClient.invalidateQueries({ queryKey: ['selectors'] })
    },
    onError: () => toast.error(t('toast.selectorDashboard.failedToQuickadd')),
  })

  const declineMut = useMutation({
    mutationFn: () => declineRequest(declineTarget!.id, token!, declineReason),
    onSuccess: () => {
      toast.success(t('toast.selectorDashboard.requestDeclined'))
      setDeclineTarget(null)
      setDeclineReason('')
      queryClient.invalidateQueries({ queryKey: ['selectors'] })
    },
    onError: () => toast.error(t('toast.selectorDashboard.failedToDecline')),
  })

  if (isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" /></div>
  }

  const items = queue?.items ?? []

  return (
    <div className="space-y-4">
      {items.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/60">
          <Inbox className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg font-medium">No pending requests</p>
          <p className="text-sm mt-1">{t('selectorDashboard.allPatronPurchaseRequestsHave')}</p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Patron</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Submitted</th>
                <th className="text-left px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                <th className="text-right px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map(req => {
                const inCatalog = req.isbn && catalogChecks?.[req.isbn]?.in_catalog
                const onList = onSelectionList(req)
                return (
                  <tr
                    key={req.id}
                    className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-all duration-200"
                  >
                    <td className="px-4 py-3 text-lsc-dark dark:text-lsc-cream">{req.patron_name ?? '—'}</td>
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{req.title}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{req.author ?? '—'}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">{req.isbn ?? '—'}</td>
                    <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/60">{formatDate(req.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1.5 flex-wrap">
                        {inCatalog && (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-earth-200 dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">
                            In catalog
                          </span>
                        )}
                        {onList && (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300">
                            On list
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => quickAddMut.mutate(req)}
                          isLoading={quickAddMut.isPending && quickAddMut.variables?.id === req.id}
                          leftIcon={<Plus className="w-3.5 h-3.5" />}
                        >
                          Quick Add
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => { setDeclineTarget(req); setDeclineReason('') }}
                          leftIcon={<X className="w-3.5 h-3.5" />}
                        >
                          Decline
                        </Button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {queue && queue.total > queue.per_page && (
        <div className="flex justify-center gap-2 mt-4">
          <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            Previous
          </Button>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 flex items-center px-3">
            Page {page} of {Math.ceil(queue.total / queue.per_page)}
          </span>
          <Button size="sm" variant="secondary" disabled={page >= Math.ceil(queue.total / queue.per_page)} onClick={() => setPage(p => p + 1)}>
            Next
          </Button>
        </div>
      )}

      {/* Decline modal */}
      <Modal
        isOpen={!!declineTarget}
        onClose={() => setDeclineTarget(null)}
        title={`Decline: ${declineTarget?.title ?? ''}`}
        size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeclineTarget(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => declineMut.mutate()} isLoading={declineMut.isPending} disabled={!declineReason.trim()}>
              Decline Request
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {templates && templates.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Quick reasons</label>
              <div className="flex flex-wrap gap-2">
                {templates.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setDeclineReason(t.message)}
                    className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                      declineReason === t.message
                        ? 'border-lsc-rose bg-lsc-rose/10 text-lsc-rose'
                        : 'border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reason</label>
            <textarea
              value={declineReason}
              onChange={e => setDeclineReason(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              placeholder={t('selectorDashboard.enterTheReasonForDeclining')}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
