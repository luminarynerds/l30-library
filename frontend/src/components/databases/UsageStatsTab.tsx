/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BarChart3, Download, RefreshCw, Save } from 'lucide-react'
import toast from 'react-hot-toast'

import {
  addUsageStats,
  getSubscriptions,
  getUsageReportPreview,
  getUsageStats,
  type CreateUsageStatsRequest,
  type DatabaseSubscription,
  type DatabaseUsageStats,
  downloadUsageReport,
} from '../../api/databases-api'

const MONTH_LABELS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

interface UsageStatsTabProps {
  isAdmin: boolean
}

export function UsageStatsTab({ isAdmin }: UsageStatsTabProps): React.ReactElement {
  const queryClient = useQueryClient()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState<number>(currentYear)
  const [selectedSubId, setSelectedSubId] = useState<number | null>(null)

  const { data: subscriptions, isLoading: subsLoading } = useQuery({
    queryKey: ['database-subscriptions', 'usage-tab'],
    queryFn: () => getSubscriptions({ include_inactive: true }),
  })

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['usage-report-preview', year],
    queryFn: () => getUsageReportPreview(year),
  })

  if (subsLoading) {
    return (
      <div className="flex justify-center py-12">
        <RefreshCw
          className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin"
          aria-hidden="true"
        />
      </div>
    )
  }

  const subs = subscriptions ?? []
  const selectedSub = subs.find((s) => s.id === selectedSubId) ?? null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            COUNTER R5 Usage Statistics
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Enter monthly usage from vendor reports, then export the annual DR_D1
            for state library filings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" htmlFor="usage-year">
            Year
          </label>
          <select
            id="usage-year"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-earth-300 bg-white px-3 py-2 text-sm dark:border-earth-700 dark:bg-earth-900 dark:text-lsc-cream"
          >
            {Array.from({ length: 5 }, (_, i) => currentYear - i).map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => {
              downloadUsageReport(year, 'tsv').catch((err) => {
                console.error('Usage report download failed:', err)
              })
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-4 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 dark:bg-lsc-rose-light dark:text-lsc-dark"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download DR_D1 ({year})
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        <SubscriptionList
          subscriptions={subs}
          selectedId={selectedSubId}
          onSelect={setSelectedSubId}
        />

        <div className="space-y-6">
          {selectedSub ? (
            <UsageStatsForm
              subscription={selectedSub}
              year={year}
              onSaved={() => {
                queryClient.invalidateQueries({ queryKey: ['usage-report-preview', year] })
                queryClient.invalidateQueries({
                  queryKey: ['usage-stats', selectedSub.id, year],
                })
              }}
              disabled={!isAdmin}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-earth-300 p-8 text-center text-sm text-lsc-dark/60 dark:border-earth-700 dark:text-lsc-cream/60">
              Select a database on the left to enter monthly usage.
            </div>
          )}

          <UsageReportPreviewTable report={report} isLoading={reportLoading} year={year} />
        </div>
      </div>
    </div>
  )
}

interface SubscriptionListProps {
  subscriptions: DatabaseSubscription[]
  selectedId: number | null
  onSelect: (id: number) => void
}

function SubscriptionList({
  subscriptions,
  selectedId,
  onSelect,
}: SubscriptionListProps): React.ReactElement {
  if (subscriptions.length === 0) {
    return (
      <div className="rounded-lg border border-earth-200 bg-white p-4 text-sm text-lsc-dark/70 dark:border-earth-700 dark:bg-earth-900 dark:text-lsc-cream/70">
        No subscriptions to report on. Create a subscription first.
      </div>
    )
  }
  return (
    <div className="rounded-lg border border-earth-200 bg-white dark:border-earth-700 dark:bg-earth-900">
      <div className="border-b border-earth-200 px-4 py-2 text-sm font-medium text-lsc-dark dark:border-earth-700 dark:text-lsc-cream">
        Databases ({subscriptions.length})
      </div>
      <ul className="max-h-96 overflow-y-auto">
        {subscriptions.map((sub) => (
          <li key={sub.id}>
            <button
              type="button"
              onClick={() => onSelect(sub.id)}
              className={`w-full px-4 py-2 text-left text-sm transition-colors ${
                selectedId === sub.id
                  ? 'bg-lsc-rose/10 text-lsc-dark dark:bg-lsc-rose-light/10 dark:text-lsc-cream'
                  : 'text-lsc-dark/80 hover:bg-earth-50 dark:text-lsc-cream/80 dark:hover:bg-earth-800'
              }`}
            >
              {sub.name}
              {sub.vendor?.name && (
                <span className="ml-2 text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                  {sub.vendor.name}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

interface UsageStatsFormProps {
  subscription: DatabaseSubscription
  year: number
  onSaved: () => void
  disabled: boolean
}

const METRIC_FIELDS: Array<{ key: keyof CreateUsageStatsRequest; label: string }> = [
  { key: 'searches_regular', label: 'Searches (Regular)' },
  { key: 'searches_federated', label: 'Searches (Federated)' },
  { key: 'searches_automated', label: 'Searches (Automated)' },
  { key: 'total_item_requests', label: 'Total Item Requests' },
  { key: 'unique_item_requests', label: 'Unique Item Requests' },
  { key: 'total_item_investigations', label: 'Total Item Investigations' },
  { key: 'unique_item_investigations', label: 'Unique Item Investigations' },
  { key: 'no_license', label: 'No License (Turnaways)' },
]

function UsageStatsForm({
  subscription,
  year,
  onSaved,
  disabled,
}: UsageStatsFormProps): React.ReactElement {
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1)

  const { data: existingStats } = useQuery({
    queryKey: ['usage-stats', subscription.id, year],
    queryFn: () => getUsageStats(subscription.id, year),
  })

  const current = useMemo<DatabaseUsageStats | undefined>(
    () => existingStats?.find((s) => s.stat_month === month),
    [existingStats, month],
  )

  const [form, setForm] = useState<Partial<Record<keyof CreateUsageStatsRequest, number>>>({})

  // Reset form when month/subscription changes; prefill with existing values.
  useEffect(() => {
    if (current) {
      const next: Partial<Record<keyof CreateUsageStatsRequest, number>> = {}
      METRIC_FIELDS.forEach(({ key }) => {
        next[key] = (current as unknown as Record<string, number>)[key] ?? 0
      })
      setForm(next)
    } else {
      setForm({})
    }
  }, [current, month])

  const mutation = useMutation({
    mutationFn: (payload: CreateUsageStatsRequest) =>
      addUsageStats(subscription.id, payload),
    onSuccess: () => {
      toast.success('Usage stats saved')
      onSaved()
    },
    onError: () => {
      toast.error('Failed to save usage stats')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (disabled) return
    const payload: CreateUsageStatsRequest = {
      stat_year: year,
      stat_month: month,
      data_source: 'manual',
      ...Object.fromEntries(
        METRIC_FIELDS.map(({ key }) => [key, form[key] ?? 0]),
      ),
    } as CreateUsageStatsRequest
    mutation.mutate(payload)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-earth-200 bg-white p-4 dark:border-earth-700 dark:bg-earth-900"
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream">
            {subscription.name}
          </h3>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            {current ? 'Editing existing month' : 'New entry'}
            {'. Saves overwrite existing values for this month.'}
          </p>
        </div>
        <select
          aria-label="Month"
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="rounded-lg border border-earth-300 bg-white px-2 py-1 text-sm dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream"
        >
          {MONTH_LABELS.map((label, idx) => (
            <option key={label} value={idx + 1}>
              {label} {year}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {METRIC_FIELDS.map(({ key, label }) => (
          <label
            key={key}
            className="flex flex-col gap-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80"
          >
            <span>{label}</span>
            <input
              type="number"
              min={0}
              disabled={disabled}
              value={form[key] ?? 0}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  [key]: Number(e.target.value) || 0,
                }))
              }
              className="rounded-lg border border-earth-300 bg-white px-3 py-2 text-sm dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream"
            />
          </label>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={disabled || mutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-lsc-rose px-4 py-2 text-sm font-medium text-white hover:bg-lsc-rose/90 disabled:opacity-50 dark:bg-lsc-rose-light dark:text-lsc-dark"
        >
          <Save className="h-4 w-4" aria-hidden="true" />
          {mutation.isPending ? 'Saving...' : 'Save Month'}
        </button>
      </div>
    </form>
  )
}

interface UsageReportPreviewTableProps {
  report: Awaited<ReturnType<typeof getUsageReportPreview>> | undefined
  isLoading: boolean
  year: number
}

function UsageReportPreviewTable({
  report,
  isLoading,
  year,
}: UsageReportPreviewTableProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-earth-200 bg-white p-8 text-center dark:border-earth-700 dark:bg-earth-900">
        <RefreshCw
          className="mx-auto h-6 w-6 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin"
          aria-hidden="true"
        />
      </div>
    )
  }
  if (!report || report.rows.length === 0) {
    return (
      <div className="rounded-lg border border-earth-200 bg-white p-8 text-center text-sm text-lsc-dark/60 dark:border-earth-700 dark:bg-earth-900 dark:text-lsc-cream/60">
        No usage data entered for {year} yet.
      </div>
    )
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-earth-200 bg-white dark:border-earth-700 dark:bg-earth-900">
      <div className="flex items-center gap-2 border-b border-earth-200 px-4 py-2 text-sm font-medium text-lsc-dark dark:border-earth-700 dark:text-lsc-cream">
        <BarChart3 className="h-4 w-4" aria-hidden="true" />
        {year} Annual Rollup (DR_D1)
      </div>
      <table className="min-w-full text-sm">
        <thead className="bg-earth-50 text-left text-xs uppercase tracking-wide text-lsc-dark/60 dark:bg-earth-800 dark:text-lsc-cream/60">
          <tr>
            <th className="px-4 py-2">Database</th>
            <th className="px-4 py-2 text-right">Searches</th>
            <th className="px-4 py-2 text-right">Item Requests</th>
            <th className="px-4 py-2 text-right">Investigations</th>
            <th className="px-4 py-2 text-right">No License</th>
            <th className="px-4 py-2 text-right">Cost/Use</th>
          </tr>
        </thead>
        <tbody>
          {report.rows.map((row) => {
            const searches =
              row.searches_regular + row.searches_federated + row.searches_automated
            return (
              <tr
                key={row.subscription_id}
                className="border-t border-earth-100 dark:border-earth-800"
              >
                <td className="px-4 py-2">
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream">
                    {row.database}
                  </div>
                  {row.publisher && (
                    <div className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                      {row.publisher}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2 text-right">{searches.toLocaleString()}</td>
                <td className="px-4 py-2 text-right">
                  {row.total_item_requests.toLocaleString()}
                </td>
                <td className="px-4 py-2 text-right">
                  {row.total_item_investigations.toLocaleString()}
                </td>
                <td className="px-4 py-2 text-right">{row.no_license.toLocaleString()}</td>
                <td className="px-4 py-2 text-right text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {row.cost_per_use ? `$${row.cost_per_use}` : '-'}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot className="bg-earth-50 dark:bg-earth-800">
          <tr>
            <td className="px-4 py-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              Totals
            </td>
            <td className="px-4 py-2 text-right text-sm font-medium">
              {(
                (report.totals.Searches_Regular ?? 0) +
                (report.totals.Searches_Federated ?? 0) +
                (report.totals.Searches_Automated ?? 0)
              ).toLocaleString()}
            </td>
            <td className="px-4 py-2 text-right text-sm font-medium">
              {(report.totals.Total_Item_Requests ?? 0).toLocaleString()}
            </td>
            <td className="px-4 py-2 text-right text-sm font-medium">
              {(report.totals.Total_Item_Investigations ?? 0).toLocaleString()}
            </td>
            <td className="px-4 py-2 text-right text-sm font-medium">
              {(report.totals.No_License ?? 0).toLocaleString()}
            </td>
            <td className="px-4 py-2"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
