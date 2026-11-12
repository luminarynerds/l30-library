/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Users, BookOpen, Handshake, Building2, DollarSign, Library,
  Loader2, TrendingUp, Calendar, Repeat,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { AdminShell } from '../components/shells/AdminShell'
import { getCommunityDashboard, getCommunityTrends, type CategoryMetrics, type TransactionalMetrics } from '../api/community-outcomes-api'
import { listBranches } from '@/api/branch-api'
import { useTranslation } from '@/i18n'

type PresetKey = 'last30' | 'mtd' | 'qtd' | 'ytd' | 'lastFy' | 'custom'

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function presetRange(key: PresetKey): { start: string; end: string } {
  const now = new Date()
  const end = isoDate(now)
  switch (key) {
    case 'last30': {
      const s = new Date(now)
      s.setDate(s.getDate() - 30)
      return { start: isoDate(s), end }
    }
    case 'mtd':
      return { start: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`, end }
    case 'qtd': {
      const qMonth = Math.floor(now.getMonth() / 3) * 3
      return { start: `${now.getFullYear()}-${String(qMonth + 1).padStart(2, '0')}-01`, end }
    }
    case 'ytd':
      return { start: `${now.getFullYear()}-01-01`, end }
    case 'lastFy': {
      const fyStart = now.getMonth() >= 6 ? now.getFullYear() : now.getFullYear() - 1
      return { start: `${fyStart}-07-01`, end: `${fyStart + 1}-06-30` }
    }
    default:
      return { start: `${now.getFullYear()}-01-01`, end }
  }
}

const CATEGORY_CONFIG: Record<string, { label: string; icon: React.ElementType; headline: string }> = {
  program_reach: { label: 'Program Reach', icon: Users, headline: 'total_participants' },
  educational: { label: 'Educational Outcomes', icon: BookOpen, headline: 'active_programs' },
  partnerships: { label: 'Community Partnerships', icon: Handshake, headline: 'active_partnerships' },
  space_utilization: { label: 'Space Utilization', icon: Building2, headline: 'total_events' },
  cost_effectiveness: { label: 'Cost Effectiveness', icon: DollarSign, headline: 'cost_per_attendee' },
  collection_impact: { label: 'Collection Impact', icon: Library, headline: 'total_checkouts' },
}

const TRANSACTIONAL_LABELS: Array<{ key: keyof TransactionalMetrics; label: string }> = [
  { key: 'checkouts', label: 'Checkouts' },
  { key: 'returns', label: 'Returns' },
  { key: 'renewals', label: 'Renewals' },
  { key: 'holds_placed', label: 'Holds Placed' },
  { key: 'holds_filled', label: 'Holds Filled' },
]

function TransactionalStrip({ metrics }: { metrics: TransactionalMetrics }) {
  return (
    <div className="bg-lsc-cream/60 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-4 mb-6">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
          <Repeat size={16} />
          Transactional Volume
        </h3>
        {TRANSACTIONAL_LABELS.map(({ key, label }) => (
          <span key={key} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {label}{' '}
            <span className="font-bold text-lsc-dark dark:text-lsc-cream">
              {metrics[key].toLocaleString()}
            </span>
          </span>
        ))}
      </div>
      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
        High-volume, low-touch work. The categories below are what it exists to support.
      </p>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-3 border border-lsc-border dark:border-earth-700">
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
    </div>
  )
}

function CategoryCard({
  category,
  metrics,
  trendData,
}: {
  category: string
  metrics: CategoryMetrics
  trendData?: Array<{ period: string; value: number }>
}) {
  const config = CATEGORY_CONFIG[category]
  if (!config) return null
  const Icon = config.icon

  const formatValue = (key: string, val: unknown): string => {
    if (typeof val === 'number') {
      if (key.includes('cost')) return `$${val}`
      if (key.includes('rate')) return `${val}%`
      return val.toLocaleString()
    }
    return String(val ?? '\u2014')
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5">
      <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 flex items-center gap-2">
        <Icon size={16} />
        {config.label}
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
        {Object.entries(metrics)
          .filter(([, v]) => typeof v === 'number')
          .map(([key, val]) => (
            <StatCard
              key={key}
              label={key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              value={formatValue(key, val)}
            />
          ))}
      </div>
      {trendData && trendData.length > 1 && (
        <div className="h-32">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData}>
              <XAxis dataKey="period" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} width={40} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#e97316" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default function CommunityOutcomesDashboardPage() {
  const { t } = useTranslation()
  const [preset, setPreset] = useState<PresetKey>('ytd')
  const [branchId, setBranchId] = useState<number | undefined>()

  const range = useMemo(() => presetRange(preset), [preset])

  const { data: branches } = useQuery({
    queryKey: ['branches'],
    queryFn: () => listBranches(),
  })

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['community-dashboard', range.start, range.end, branchId],
    queryFn: () => getCommunityDashboard({
      start_date: range.start,
      end_date: range.end,
      branch_id: branchId,
    }),
  })

  const { data: trendData } = useQuery({
    queryKey: ['community-trends-all', branchId],
    queryFn: async () => {
      const results: Record<string, Array<{ period: string; value: number }>> = {}
      for (const cat of Object.keys(CATEGORY_CONFIG)) {
        const trends = await getCommunityTrends(cat, 12, branchId)
        const config = CATEGORY_CONFIG[cat]
        if (!config) continue
        results[cat] = trends.map((t) => ({
          period: t.period,
          value: (t.metrics[config.headline] as number) ?? 0,
        }))
      }
      return results
    },
  })

  const presets: { key: PresetKey; label: string }[] = [
    { key: 'last30', label: 'Last 30 Days' },
    { key: 'mtd', label: 'MTD' },
    { key: 'qtd', label: 'QTD' },
    { key: 'ytd', label: 'YTD' },
    { key: 'lastFy', label: 'Last FY' },
  ]

  void t

  return (
    <AdminShell
      title="Community Activity"
      subtitle="Cross-cutting impact metrics across all library programs and services."
      icon={<TrendingUp size={28} />}
    >
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1">
          {presets.map((p) => (
            <button
              key={p.key}
              onClick={() => setPreset(p.key)}
              className={`px-3 py-1.5 text-sm rounded-lg border ${
                preset === p.key
                  ? 'bg-lsc-rose text-white border-lsc-rose'
                  : 'border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        {branches && branches.length > 1 && (
          <select
            value={branchId ?? ''}
            onChange={(e) => setBranchId(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-1.5 text-sm border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            <option value="">All Branches</option>
            {branches.map((b: { id: number; name: string }) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        )}
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto">
          <Calendar size={12} className="inline mr-1" />
          {range.start} to {range.end}
        </span>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="motion-safe:animate-spin text-lsc-rose" size={32} />
        </div>
      ) : dashboard ? (
        <>
        {dashboard.transactional && <TransactionalStrip metrics={dashboard.transactional} />}
        <div className="grid md:grid-cols-2 gap-6">
          {Object.keys(CATEGORY_CONFIG).map((cat) => (
            <CategoryCard
              key={cat}
              category={cat}
              metrics={dashboard.categories[cat] || {}}
              trendData={trendData?.[cat]}
            />
          ))}
        </div>
        </>
      ) : (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-12">
          No data available for the selected period.
        </p>
      )}
    </AdminShell>
  )
}
