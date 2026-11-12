/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { t } from '../../i18n'
import { useQuery } from '@tanstack/react-query'
import { Library, RefreshCw, DollarSign, BookOpen, Calendar, TrendingUp, TrendingDown, Save, Check } from 'lucide-react'
import { AdminShell } from '../../components/shells'
import { useAuth } from '../../contexts/AuthContext'
import {
  getAnalyticsCollectionUsage,
  getAnalyticsCollectionDetails,
  type CollectionUsageData,
  type CollectionDetailsData,
} from '../../api/analytics-api'
import { formatNumber, formatCurrency } from '../../components/analytics/analytics-utils'
import { getCurrentLocale } from '@/i18n'

// --- Date range presets ---

type PresetKey = '7d' | '30d' | '90d' | 'ytd' | 'custom'

const PRESETS: { key: PresetKey; label: string }[] = [
  { key: '7d', label: '7 days' },
  { key: '30d', label: '30 days' },
  { key: '90d', label: '90 days' },
  { key: 'ytd', label: 'YTD' },
  { key: 'custom', label: 'Custom' },
]

function presetToDates(key: PresetKey): { start: string; end: string } {
  const today = new Date()
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const end = fmt(today)

  switch (key) {
    case '7d': {
      const s = new Date(today)
      s.setDate(s.getDate() - 7)
      return { start: fmt(s), end }
    }
    case '30d': {
      const s = new Date(today)
      s.setDate(s.getDate() - 30)
      return { start: fmt(s), end }
    }
    case '90d': {
      const s = new Date(today)
      s.setDate(s.getDate() - 90)
      return { start: fmt(s), end }
    }
    case 'ytd':
      return { start: `${today.getFullYear()}-01-01`, end }
    case 'custom':
    default:
      return { start: fmt(new Date(today.getFullYear(), today.getMonth() - 1, today.getDate())), end }
  }
}

// --- Saved view (localStorage) ---

const SAVED_VIEW_KEY = 'l30:collection-analytics-view'

interface SavedView {
  preset: PresetKey
  customStart: string
  customEnd: string
}

function loadSavedView(): SavedView | null {
  try {
    const raw = localStorage.getItem(SAVED_VIEW_KEY)
    return raw ? (JSON.parse(raw) as SavedView) : null
  } catch {
    return null
  }
}

function saveView(view: SavedView) {
  localStorage.setItem(SAVED_VIEW_KEY, JSON.stringify(view))
}

// --- Condition colors ---

const CONDITION_CLASSES: Record<string, string> = {
  new: 'bg-status-success-500',
  good: 'bg-lsc-gold',
  fair: 'bg-status-warning-400',
  poor: 'bg-status-warning-600',
  damaged: 'bg-status-danger-500',
}

const CONDITION_ORDER = ['new', 'good', 'fair', 'poor', 'damaged']

// --- Component ---

export default function CollectionAnalyticsPage() {
  const { token } = useAuth()
  const saved = useState<SavedView | null>(loadSavedView)[0]
  const [preset, setPreset] = useState<PresetKey>(saved?.preset ?? '30d')
  const [customStart, setCustomStart] = useState(saved?.customStart ?? '')
  const [customEnd, setCustomEnd] = useState(saved?.customEnd ?? '')
  const [viewSaved, setViewSaved] = useState(false)

  const handleSaveView = () => {
    saveView({ preset, customStart, customEnd })
    setViewSaved(true)
    setTimeout(() => setViewSaved(false), 2000)
  }

  const { start: startDate, end: endDate } = useMemo(() => {
    if (preset === 'custom' && customStart && customEnd) {
      return { start: customStart, end: customEnd }
    }
    return presetToDates(preset)
  }, [preset, customStart, customEnd])

  const usageQuery = useQuery({
    queryKey: ['collection-analytics', 'usage', startDate, endDate],
    queryFn: () => getAnalyticsCollectionUsage(token!, startDate, endDate),
    enabled: !!token,
    staleTime: 2 * 60 * 1000,
  })

  const detailsQuery = useQuery({
    queryKey: ['collection-analytics', 'details', startDate, endDate],
    queryFn: () => getAnalyticsCollectionDetails(token!, startDate, endDate),
    enabled: !!token,
    staleTime: 2 * 60 * 1000,
  })

  const isLoading = usageQuery.isLoading || detailsQuery.isLoading
  const error = usageQuery.error || detailsQuery.error
  const usage = usageQuery.data
  const details = detailsQuery.data

  const handleRefresh = () => {
    void usageQuery.refetch()
    void detailsQuery.refetch()
  }

  return (
    <AdminShell
      title="Collection Analytics"
      subtitle="Usage metrics, condition trends, and cost efficiency"
      icon={<Library className="w-6 h-6 text-lsc-rose" />}
      loading={isLoading && !usage && !details}
      error={error ? 'Failed to load collection analytics' : null}
      actions={
        <button
          onClick={handleRefresh}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      }
    >
      {/* Date range selector */}
      <div className="flex flex-wrap items-center gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            onClick={() => setPreset(p.key)}
            aria-pressed={preset === p.key}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              preset === p.key
                ? 'bg-lsc-rose text-white'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
            }`}
          >
            {p.label}
          </button>
        ))}
        {preset === 'custom' && (
          <div className="flex items-center gap-2 ml-2">
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              aria-label={t('aria.collectionAnalytics.startDate', 'Start date')}
              className="px-2 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
            <span className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">to</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              aria-label={t('aria.collectionAnalytics.endDate', 'End date')}
              className="px-2 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        )}
        <span role="status" aria-live="polite" className="ml-auto">
          <button
            type="button"
            onClick={handleSaveView}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose hover:text-lsc-rose transition-colors"
          >
            {viewSaved ? (
              <Check className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Save className="w-4 h-4" aria-hidden="true" />
            )}
            {viewSaved ? 'Saved' : 'Save this view'}
          </button>
        </span>
      </div>

      {/* Stats Cards */}
      {(usage || details) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Items" value={formatNumber(details?.totalItems ?? usage?.totalTitles ?? 0)} icon={<Library className="w-5 h-5" />} />
          <StatCard label="Avg Checkouts / Item" value={(details?.avgCheckoutsPerItem ?? usage?.turnoverRate ?? 0).toFixed(2)} icon={<BookOpen className="w-5 h-5" />} />
          <StatCard label="Never Circulated" value={formatNumber(usage?.neverCirculated ?? 0)} icon={<Calendar className="w-5 h-5" />} accent />
          <StatCard label="Avg Age (years)" value={details?.avgAgeYears?.toFixed(1) ?? '--'} icon={<Calendar className="w-5 h-5" />} />
        </div>
      )}

      {/* Format Distribution */}
      {usage && usage.byCategory.length > 0 && (
        <Section title="Format Distribution">
          <FormatBars categories={usage.byCategory} />
        </Section>
      )}

      {/* Condition Distribution */}
      {details && Object.keys(details.byCondition).length > 0 && (
        <Section title="Condition Distribution">
          <ConditionBar byCondition={details.byCondition} />
        </Section>
      )}

      {/* Most / Least Circulated */}
      <div className="grid lg:grid-cols-2 gap-6">
        {details && details.topCirculated.length > 0 && (
          <Section title="Most Circulated" icon={<TrendingUp className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />}>
            <CirculationTable items={details.topCirculated} />
          </Section>
        )}
        {details && details.leastCirculated.length > 0 && (
          <Section title="Least Circulated" icon={<TrendingDown className="w-5 h-5 text-status-warning-500" />}>
            <CirculationTable items={details.leastCirculated} />
          </Section>
        )}
      </div>

      {/* Cost Efficiency */}
      {details && details.costEfficiency.copiesWithCost > 0 && (
        <Section title="Cost Efficiency" icon={<DollarSign className="w-5 h-5 text-lsc-rose" />}>
          <CostEfficiencyPanel cost={details.costEfficiency} />
        </Section>
      )}
    </AdminShell>
  )
}

// --- Sub-components ---

function StatCard({ label, value, icon, accent }: { label: string; value: string; icon: React.ReactNode; accent?: boolean }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lsc-rose">{icon}</span>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      </div>
      <p className={`text-2xl font-bold ${accent ? 'text-status-warning-500' : 'text-lsc-dark dark:text-lsc-cream'}`}>
        {value}
      </p>
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  )
}

function FormatBars({ categories }: { categories: CollectionUsageData['byCategory'] }) {
  const max = Math.max(...categories.map((c) => c.titles), 1)
  return (
    <div className="space-y-3">
      {categories.map((cat) => (
        <div key={cat.category} className="flex items-center gap-3">
          <span className="w-24 text-sm text-right text-lsc-dark/70 dark:text-lsc-cream/70 capitalize flex-shrink-0">
            {cat.category}
          </span>
          <div className="flex-1 h-6 bg-earth-100 dark:bg-earth-700 rounded overflow-hidden">
            <div
              className="h-full bg-lsc-rose rounded transition-all"
              style={{ width: `${(cat.titles / max) * 100}%` }}
            />
          </div>
          <span className="w-16 text-sm text-right font-medium text-lsc-dark dark:text-lsc-cream flex-shrink-0">
            {formatNumber(cat.titles)}
          </span>
        </div>
      ))}
    </div>
  )
}

function ConditionBar({ byCondition }: { byCondition: Record<string, number> }) {
  const total = Object.values(byCondition).reduce((s, v) => s + v, 0)
  if (total === 0) return null

  const ordered = CONDITION_ORDER.filter((c) => byCondition[c])

  return (
    <div>
      {/* Stacked bar */}
      <div className="h-8 flex rounded overflow-hidden mb-4">
        {ordered.map((cond) => {
          const count = byCondition[cond] ?? 0
          const pct = (count / total) * 100
          return (
            <div
              key={cond}
              className={`transition-all ${CONDITION_CLASSES[cond] ?? 'bg-earth-400'}`}
              style={{
                width: `${pct}%`,
                minWidth: pct > 0 ? '2px' : 0,
              }}
              title={`${cond}: ${formatNumber(count)} (${pct.toFixed(1)}%)`}
            />
          )
        })}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {ordered.map((cond) => {
          const count = byCondition[cond] ?? 0
          const pct = ((count / total) * 100).toFixed(1)
          return (
            <div key={cond} className="flex items-center gap-2 text-sm">
              <span
                className={`w-3 h-3 rounded-sm flex-shrink-0 ${CONDITION_CLASSES[cond] ?? 'bg-earth-400'}`}
              />
              <span className="capitalize text-lsc-dark/70 dark:text-lsc-cream/70">{cond}</span>
              <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                {formatNumber(count)} ({pct}%)
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CirculationTable({ items }: { items: CollectionDetailsData['topCirculated'] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm table-fixed">
        <colgroup>
          <col className="w-[42%]" />
          <col className="w-[28%]" />
          <col className="w-[15%]" />
          <col className="w-[15%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-lsc-border dark:border-earth-700">
            <th scope="col" className="text-left p-2 font-semibold text-lsc-dark dark:text-lsc-cream">Title</th>
            <th scope="col" className="text-left p-2 font-semibold text-lsc-dark dark:text-lsc-cream">Author</th>
            <th scope="col" className="text-right p-2 font-semibold text-lsc-dark dark:text-lsc-cream">Checkouts</th>
            <th scope="col" className="text-right p-2 font-semibold text-lsc-dark dark:text-lsc-cream">Last Checkout</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr
              key={item.catalogItemId}
              className={idx % 2 === 0 ? 'bg-lsc-cream/30 dark:bg-earth-700/30' : ''}
            >
              <td className="p-2 text-lsc-dark dark:text-lsc-cream font-medium truncate" title={item.title}>
                {item.title}
              </td>
              <td className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 truncate">
                {item.author ?? '--'}
              </td>
              <td className="p-2 text-right font-medium text-lsc-rose">
                {formatNumber(item.checkoutCount)}
              </td>
              <td className="p-2 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                {item.lastCheckout
                  ? new Date(item.lastCheckout).toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric', year: '2-digit' })
                  : '--'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CostEfficiencyPanel({ cost }: { cost: CollectionDetailsData['costEfficiency'] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Replacement Cost</p>
        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          {formatCurrency(cost.totalReplacementCost)}
        </p>
      </div>
      <div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Items with Cost Data</p>
        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          {formatNumber(cost.copiesWithCost)}
        </p>
      </div>
      <div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Circulations (costed items)</p>
        <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          {formatNumber(cost.checkoutsOfCostedItems)}
        </p>
      </div>
      <div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Avg Cost / Circulation</p>
        <p className="text-xl font-bold text-lsc-rose">
          {cost.avgCostPerCirculation !== null ? formatCurrency(cost.avgCostPerCirculation) : 'N/A'}
        </p>
      </div>
    </div>
  )
}
