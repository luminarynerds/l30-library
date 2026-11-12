/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { AdminShell } from '../../../components/shells/AdminShell'
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog'
import { useAuth } from '../../../contexts/AuthContext'
import { t } from '../../../i18n'
import {
  approveFineWaiver,
  listPendingWaivers,
  rejectFineWaiver,
  type PendingWaiverListItem,
} from '../../../api/staff-api'

const ADMIN_ROLES = new Set(['admin', 'director', 'super_admin'])

function formatDateTime(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

interface PendingDecision {
  waiverId: number
  approve: boolean
  amount: number
  patronLabel: string
}

export default function PendingFineWaiversPage() {
  const { token, user } = useAuth()
  const isAdmin = !!user && ADMIN_ROLES.has(String(user.role).toLowerCase())

  const [items, setItems] = useState<PendingWaiverListItem[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set())
  const [pendingDecision, setPendingDecision] = useState<PendingDecision | null>(null)

  const reload = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await listPendingWaivers(token, { limit: 200 })
      setItems(data.waivers)
      setTotal(data.total_count)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load pending waivers')
    } finally {
      setIsLoading(false)
    }
  }, [token])

  useEffect(() => {
    reload()
  }, [reload])

  const setRowPending = (id: number, pending: boolean) => {
    setPendingIds((prev) => {
      const next = new Set(prev)
      if (pending) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const handleDecision = useCallback(
    async (waiverId: number, approve: boolean) => {
      if (!token) return
      setRowPending(waiverId, true)
      try {
        if (approve) {
          await approveFineWaiver(token, waiverId)
          toast.success('Waiver approved.')
        } else {
          await rejectFineWaiver(token, waiverId)
          toast.success('Waiver rejected.')
        }
        await reload()
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Decision failed')
      } finally {
        setRowPending(waiverId, false)
      }
    },
    [token, reload]
  )

  if (!isAdmin) {
    return (
      <AdminShell title="Pending Fine Waivers">
        <div
          role="alert"
          className="p-4 rounded-xl bg-status-warning-50 dark:bg-status-warning-900 text-status-warning-900 dark:text-status-warning-100"
        >
          You need administrator or director access to review fine waivers.
        </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="Pending Fine Waivers">
      <div className="flex items-center justify-between mb-4">
        <p role="status" aria-live="polite" aria-atomic="true" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {isLoading
            ? 'Loading…'
            : total === 0
              ? 'No waivers awaiting review.'
              : `${total} waiver${total === 1 ? '' : 's'} awaiting review.`}
        </p>
        <button
          type="button"
          onClick={() => reload()}
          className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800"
        >
          Refresh
        </button>
      </div>

      {items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700">
          <table className="w-full text-sm">
            <caption className="sr-only">Fine waivers awaiting approval</caption>
            <thead className="bg-lsc-cream/40 dark:bg-earth-900/40 text-left">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">When</th>
                <th scope="col" className="px-3 py-2 font-medium">Patron</th>
                <th scope="col" className="px-3 py-2 font-medium text-right">Amount</th>
                <th scope="col" className="px-3 py-2 font-medium">Reason</th>
                <th scope="col" className="px-3 py-2 font-medium">Requested by</th>
                <th scope="col" className="px-3 py-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => {
                const busy = pendingIds.has(row.waiver_id)
                return (
                  <tr
                    key={row.waiver_id}
                    className="border-t border-lsc-border dark:border-earth-700"
                  >
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatDateTime(row.requested_at)}
                    </td>
                    <td className="px-3 py-2">
                      {row.patron_name ?? `Patron #${row.patron_id ?? '—'}`}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">
                      ${Number(row.amount_waived).toFixed(2)}
                    </td>
                    <td className="px-3 py-2">{row.reason}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {row.waived_by_name ?? `User #${row.waived_by_user_id ?? '—'}`}
                    </td>
                    <td className="px-3 py-2 text-right space-x-2 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() =>
                          setPendingDecision({
                            waiverId: row.waiver_id,
                            approve: true,
                            amount: Number(row.amount_waived),
                            patronLabel: row.patron_name ?? `Patron #${row.patron_id ?? '—'}`,
                          })
                        }
                        disabled={busy}
                        className="px-3 py-1 rounded-lg bg-status-success-600 hover:bg-status-success-700 text-white disabled:opacity-50"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          setPendingDecision({
                            waiverId: row.waiver_id,
                            approve: false,
                            amount: Number(row.amount_waived),
                            patronLabel: row.patron_name ?? `Patron #${row.patron_id ?? '—'}`,
                          })
                        }
                        disabled={busy}
                        className="px-3 py-1 rounded-lg bg-status-danger-600 hover:bg-status-danger-700 text-white disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={!!pendingDecision}
        title={
          pendingDecision?.approve
            ? t('pendingFineWaivers.confirmApproveTitle', 'Approve waiver?')
            : t('pendingFineWaivers.confirmRejectTitle', 'Reject waiver?')
        }
        body={
          pendingDecision
            ? pendingDecision.approve
              ? t(
                  'pendingFineWaivers.confirmApproveBody',
                  'Approve waiver of {{amount}} for {{patron}}? This posts to their account.'
                )
                  .replace('{{amount}}', `$${pendingDecision.amount.toFixed(2)}`)
                  .replace('{{patron}}', pendingDecision.patronLabel)
              : t(
                  'pendingFineWaivers.confirmRejectBody',
                  'Reject waiver of {{amount}} for {{patron}}? The fine will remain on their account.'
                )
                  .replace('{{amount}}', `$${pendingDecision.amount.toFixed(2)}`)
                  .replace('{{patron}}', pendingDecision.patronLabel)
            : ''
        }
        confirmLabel={
          pendingDecision?.approve
            ? t('pendingFineWaivers.confirmApproveLabel', 'Approve waiver')
            : t('pendingFineWaivers.confirmRejectLabel', 'Reject waiver')
        }
        tone={pendingDecision?.approve ? 'default' : 'danger'}
        onConfirm={() => {
          if (!pendingDecision) return
          handleDecision(pendingDecision.waiverId, pendingDecision.approve)
          setPendingDecision(null)
        }}
        onCancel={() => setPendingDecision(null)}
      />
    </AdminShell>
  )
}
