/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { CalendarDays, Plus, Loader2, X } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import { AdminShell } from '../components/shells/AdminShell'

type PtoType = 'vacation' | 'sick' | 'personal' | 'bereavement' | 'medical' | 'jury_duty'
type PtoStatus = 'draft' | 'submitted' | 'approved' | 'denied' | 'cancelled'

const PTO_TYPES: { value: PtoType; label: string }[] = [
  { value: 'vacation', label: 'Vacation' },
  { value: 'sick', label: 'Sick' },
  { value: 'personal', label: 'Personal' },
  { value: 'bereavement', label: 'Bereavement' },
  { value: 'medical', label: 'Medical' },
  { value: 'jury_duty', label: 'Jury duty' },
]
const TYPE_LABEL: Record<string, string> = Object.fromEntries(PTO_TYPES.map((t) => [t.value, t.label]))

interface PtoBalance {
  id: number
  pto_type: PtoType
  annual_allotment: number
  accrued_days: number
  used_days: number
  pending_days: number
  carryover_days: number
  year: number
}

interface PtoRequest {
  id: number
  start_date: string
  end_date: string
  pto_type: PtoType
  status: PtoStatus
  reason?: string | null
  number_of_days: number
  denial_reason?: string | null
}

const STATUS_BADGE: Record<PtoStatus, string> = {
  draft: 'bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-100',
  submitted: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
  approved: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
  denied: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200',
  cancelled: 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-300',
}

const available = (b: PtoBalance) =>
  Math.max(0, b.accrued_days + b.carryover_days - b.used_days - b.pending_days)

const fmtDate = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const EMPTY_FORM = { start_date: '', end_date: '', pto_type: 'vacation' as PtoType, reason: '', coverage_notes: '' }

export default function StaffPtoPage() {
  const [balances, setBalances] = useState<PtoBalance[] | null>(null)
  const [requests, setRequests] = useState<PtoRequest[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [b, r] = await Promise.all([
        api.get(`${API_BASE}/pto/balance`) as Promise<PtoBalance[]>,
        api.get(`${API_BASE}/pto/requests`) as Promise<PtoRequest[]>,
      ])
      setBalances(b)
      setRequests(r)
    } catch {
      setBalances([])
      setRequests([])
      toast.error('Could not load your PTO. Try again.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const submit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (new Date(form.end_date) < new Date(form.start_date)) {
        toast.error('End date cannot be before the start date.')
        return
      }
      setSubmitting(true)
      try {
        await api.post(`${API_BASE}/pto/requests`, {
          start_date: form.start_date,
          end_date: form.end_date,
          pto_type: form.pto_type,
          reason: form.reason || null,
          coverage_notes: form.coverage_notes || null,
        })
        toast.success('Request submitted.')
        setForm(EMPTY_FORM)
        setShowForm(false)
        load()
      } catch {
        toast.error('Could not submit the request.')
      } finally {
        setSubmitting(false)
      }
    },
    [form, load],
  )

  const cancel = useCallback(
    async (id: number) => {
      try {
        await api.delete(`${API_BASE}/pto/requests/${id}`)
        toast.success('Request cancelled.')
        load()
      } catch {
        toast.error('Could not cancel the request.')
      }
    },
    [load],
  )

  return (
    <AdminShell
      title="Paid Time Off"
      subtitle="See your balances, request time off, and track your requests."
      icon={<CalendarDays className="h-8 w-8" />}
      maxWidth="max-w-5xl"
    >
      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
          <span className="sr-only">Loading your PTO</span>
        </div>
      ) : (
        <div className="space-y-8">
          <section aria-labelledby="pto-balances-heading">
            <h2 id="pto-balances-heading" className="text-lg font-semibold mb-3 text-lsc-dark dark:text-lsc-cream">
              Your balances
            </h2>
            {balances && balances.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {balances.map((b) => (
                  <div
                    key={b.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4"
                  >
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{TYPE_LABEL[b.pto_type] ?? b.pto_type}</div>
                    <p className="text-2xl font-bold text-lsc-rose">
                      {available(b).toLocaleString()} <span className="text-base font-medium">days available</span>
                    </p>
                    <dl className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-0.5">
                      <div className="flex justify-between"><dt>Accrued</dt><dd>{b.accrued_days.toLocaleString()}</dd></div>
                      <div className="flex justify-between"><dt>Used</dt><dd>{b.used_days.toLocaleString()}</dd></div>
                      <div className="flex justify-between"><dt>Pending</dt><dd>{b.pending_days.toLocaleString()}</dd></div>
                      {b.carryover_days > 0 && (
                        <div className="flex justify-between"><dt>Carryover</dt><dd>{b.carryover_days.toLocaleString()}</dd></div>
                      )}
                    </dl>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No PTO balances are set up for your account yet.</p>
            )}
          </section>

          <section aria-labelledby="pto-requests-heading">
            <div className="flex items-center justify-between mb-3">
              <h2 id="pto-requests-heading" className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Your requests
              </h2>
              <button
                type="button"
                onClick={() => setShowForm((v) => !v)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-lsc-rose px-3 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                aria-expanded={showForm}
              >
                {showForm ? <X className="h-4 w-4" aria-hidden="true" /> : <Plus className="h-4 w-4" aria-hidden="true" />}
                {showForm ? 'Close' : 'Request time off'}
              </button>
            </div>

            {showForm && (
              <form
                onSubmit={submit}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4 mb-4 space-y-4"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="pto-start" className="block text-sm font-medium mb-1 text-lsc-dark dark:text-lsc-cream">Start date</label>
                    <input
                      id="pto-start" type="date" required value={form.start_date}
                      onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                      className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label htmlFor="pto-end" className="block text-sm font-medium mb-1 text-lsc-dark dark:text-lsc-cream">End date</label>
                    <input
                      id="pto-end" type="date" required value={form.end_date}
                      onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                      className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="pto-type" className="block text-sm font-medium mb-1 text-lsc-dark dark:text-lsc-cream">Type</label>
                  <select
                    id="pto-type" value={form.pto_type}
                    onChange={(e) => setForm((f) => ({ ...f, pto_type: e.target.value as PtoType }))}
                    className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-lsc-dark dark:text-lsc-cream"
                  >
                    {PTO_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label htmlFor="pto-reason" className="block text-sm font-medium mb-1 text-lsc-dark dark:text-lsc-cream">Reason <span className="font-normal text-lsc-dark/60 dark:text-lsc-cream/60">(optional)</span></label>
                  <input
                    id="pto-reason" type="text" value={form.reason}
                    onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                    className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="pto-coverage" className="block text-sm font-medium mb-1 text-lsc-dark dark:text-lsc-cream">Coverage notes <span className="font-normal text-lsc-dark/60 dark:text-lsc-cream/60">(optional)</span></label>
                  <textarea
                    id="pto-coverage" rows={2} value={form.coverage_notes}
                    onChange={(e) => setForm((f) => ({ ...f, coverage_notes: e.target.value }))}
                    className="w-full rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <button
                  type="submit" disabled={submitting}
                  className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-4 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                >
                  {submitting && <Loader2 className="h-4 w-4 motion-safe:animate-spin" aria-hidden="true" />}
                  Submit request
                </button>
              </form>
            )}

            {requests && requests.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-lsc-border dark:border-earth-700">
                <table className="w-full text-sm">
                  <caption className="sr-only">Your paid time off requests</caption>
                  <thead className="bg-earth-50 dark:bg-earth-800 text-left text-lsc-dark/70 dark:text-lsc-cream/70">
                    <tr>
                      <th scope="col" className="px-4 py-2 font-medium">Dates</th>
                      <th scope="col" className="px-4 py-2 font-medium">Type</th>
                      <th scope="col" className="px-4 py-2 font-medium">Days</th>
                      <th scope="col" className="px-4 py-2 font-medium">Status</th>
                      <th scope="col" className="px-4 py-2 font-medium"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                    {requests.map((r) => (
                      <tr key={r.id} className="text-lsc-dark dark:text-lsc-cream">
                        <td className="px-4 py-2">{fmtDate(r.start_date)} &ndash; {fmtDate(r.end_date)}</td>
                        <td className="px-4 py-2">{TYPE_LABEL[r.pto_type] ?? r.pto_type}</td>
                        <td className="px-4 py-2">{r.number_of_days.toLocaleString()}</td>
                        <td className="px-4 py-2">
                          <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[r.status]}`}>
                            {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
                          </span>
                          {r.status === 'denied' && r.denial_reason && (
                            <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">{r.denial_reason}</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right">
                          {(r.status === 'submitted' || r.status === 'draft') && (
                            <button
                              type="button" onClick={() => cancel(r.id)}
                              className="text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-status-danger-500 rounded"
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">You have no PTO requests yet.</p>
            )}
          </section>
        </div>
      )}
    </AdminShell>
  )
}
