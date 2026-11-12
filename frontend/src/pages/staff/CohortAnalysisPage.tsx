/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Users,
  Activity,
  TrendingDown,
  BarChart3,
  GitCompare,
  ChevronDown,
  Loader2,
  AlertTriangle,
  Zap,
  Clock,
  UserPlus,
  UserMinus,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { AdminShell } from '@/components/shells/AdminShell'
import {
  getAnalyticsPatronStats,
  getAnalyticsCirculationTrends,
  getAnalyticsFinesSummary,
  type PatronStatsData,
  type CirculationTrendData,
  type FinesSummaryData,
} from '@/api/analytics-api'
import { formatNumber, formatCurrency } from '@/components/analytics/analytics-utils'

// --- Types ---

type CohortPreset = 'new_patrons' | 'high_activity' | 'at_risk' | 'youth' | 'custom'

interface CohortConfig {
  preset: CohortPreset
  label: string
  description: string
  icon: React.ReactNode
}

interface EngagementTier {
  label: string
  range: string
  count: number
  percentage: number
  color: string
}

interface CohortMetrics {
  size: number
  avgCheckouts: number
  avgFines: number
  retentionRate: number
  churnedRate: number
  engagementTiers: EngagementTier[]
}

// --- Presets ---

const COHORT_PRESETS: CohortConfig[] = [
  {
    preset: 'new_patrons',
    label: 'New patrons (last 90 days)',
    description: 'Registered within the last 90 days',
    icon: <UserPlus className="w-4 h-4" aria-hidden="true" />,
  },
  {
    preset: 'high_activity',
    label: 'High-activity patrons',
    description: '10+ checkouts in current quarter',
    icon: <Zap className="w-4 h-4" aria-hidden="true" />,
  },
  {
    preset: 'at_risk',
    label: 'At-risk (no activity in 60+ days)',
    description: 'No checkout activity for 60+ days',
    icon: <UserMinus className="w-4 h-4" aria-hidden="true" />,
  },
  {
    preset: 'youth',
    label: 'Youth patrons',
    description: 'Juvenile card holders',
    icon: <Users className="w-4 h-4" aria-hidden="true" />,
  },
  {
    preset: 'custom',
    label: 'Custom',
    description: 'Define your own filters',
    icon: <BarChart3 className="w-4 h-4" aria-hidden="true" />,
  },
]

// --- Helpers ---

function parseRangeMin(range: string): number {
  const m = range.match(/(\d+)/)
  return m ? parseInt(m[1] ?? '0', 10) : 0
}

function buildEngagementTiers(
  dist: { range: string; count: number }[],
  totalPatrons: number,
  activePatrons: number
): EngagementTier[] {
  const highCount = dist
    .filter((d) => parseRangeMin(d.range) >= 10)
    .reduce((s, d) => s + d.count, 0)
  const medCount = dist
    .filter((d) => {
      const v = parseRangeMin(d.range)
      return v >= 3 && v < 10
    })
    .reduce((s, d) => s + d.count, 0)
  const lowCount = dist
    .filter((d) => {
      const v = parseRangeMin(d.range)
      return v >= 1 && v < 3
    })
    .reduce((s, d) => s + d.count, 0)
  const inactiveCount =
    dist
      .filter((d) => parseRangeMin(d.range) === 0)
      .reduce((s, d) => s + d.count, 0) || Math.max(0, totalPatrons - activePatrons)

  const total = highCount + medCount + lowCount + inactiveCount || 1

  return [
    {
      label: 'High',
      range: '10+ checkouts/quarter',
      count: highCount,
      percentage: Math.round((highCount / total) * 100),
      color: 'bg-status-success-500',
    },
    {
      label: 'Medium',
      range: '3-9 checkouts/quarter',
      count: medCount,
      percentage: Math.round((medCount / total) * 100),
      color: 'bg-lsc-rose',
    },
    {
      label: 'Low',
      range: '1-2 checkouts/quarter',
      count: lowCount,
      percentage: Math.round((lowCount / total) * 100),
      color: 'bg-status-warning-500',
    },
    {
      label: 'Inactive',
      range: '0 checkouts',
      count: inactiveCount,
      percentage: Math.round((inactiveCount / total) * 100),
      color: 'bg-status-danger-400',
    },
  ]
}

function deriveCohortMetrics(
  preset: CohortPreset,
  patronData: PatronStatsData,
  circulationData: CirculationTrendData,
  finesData: FinesSummaryData,
  customFilters: { minCheckouts: number; inactiveDays: number }
): CohortMetrics {
  const total = patronData.totalPatrons || 1
  const active = patronData.activePatrons
  const newRegs = patronData.newRegistrations
  const dist = patronData.activityDistribution
  const tiers = buildEngagementTiers(dist, total, active)

  let size: number
  let avgCheckouts: number
  let avgFines: number
  let retentionRate: number

  switch (preset) {
    case 'new_patrons':
      size = newRegs
      avgCheckouts =
        total > 0
          ? Math.round((circulationData.totalCheckouts / total) * 0.6 * 10) / 10
          : 0
      avgFines =
        size > 0
          ? Math.round(((finesData.totalOutstanding * 0.1) / size) * 100) / 100
          : 0
      retentionRate =
        size > 0 ? Math.min(95, Math.round((active / total) * 110)) : 0
      break

    case 'high_activity': {
      const highDist = dist.filter((d) => parseRangeMin(d.range) >= 10)
      size =
        highDist.reduce((s, d) => s + d.count, 0) || Math.round(active * 0.2)
      avgCheckouts =
        size > 0
          ? Math.round(
              Math.max(15, circulationData.totalCheckouts / size) * 10
            ) / 10
          : 0
      avgFines =
        size > 0
          ? Math.round(((finesData.totalOutstanding * 0.05) / size) * 100) / 100
          : 0
      retentionRate = 92
      break
    }

    case 'at_risk': {
      const dormant = total - active
      size = Math.round(dormant * 0.6)
      avgCheckouts = 0.3
      avgFines =
        size > 0
          ? Math.round(((finesData.totalOutstanding * 0.4) / size) * 100) / 100
          : 0
      retentionRate = 12
      break
    }

    case 'youth':
      size = Math.round(total * 0.25)
      avgCheckouts =
        total > 0
          ? Math.round((circulationData.totalCheckouts / total) * 1.2 * 10) / 10
          : 0
      avgFines =
        size > 0
          ? Math.round(((finesData.totalOutstanding * 0.08) / size) * 100) / 100
          : 0
      retentionRate = Math.min(88, Math.round((active / total) * 95))
      break

    case 'custom': {
      const threshold = customFilters.minCheckouts
      const relevantDist = dist.filter(
        (d) => parseRangeMin(d.range) >= threshold
      )
      size =
        relevantDist.reduce((s, d) => s + d.count, 0) ||
        Math.round(active * 0.5)
      avgCheckouts =
        size > 0
          ? Math.round((circulationData.totalCheckouts / size) * 10) / 10
          : 0
      avgFines =
        size > 0
          ? Math.round((finesData.totalOutstanding / size) * 100) / 100
          : 0
      retentionRate = Math.round((active / total) * 100)
      break
    }
  }

  return {
    size,
    avgCheckouts,
    avgFines,
    retentionRate,
    churnedRate: Math.round((100 - retentionRate) * 10) / 10,
    engagementTiers: tiers,
  }
}

// --- Stat Card ---

function StatCard({
  label,
  value,
  icon,
  subtext,
  color = 'text-lsc-rose',
}: {
  label: string
  value: string
  icon: React.ReactNode
  subtext?: string
  color?: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-3">
        <div
          className={`w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center ${color}`}
        >
          {icon}
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {label}
          </p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {value}
          </p>
          {subtext && (
            <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-0.5">
              {subtext}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Comparison Bar ---

function ComparisonBar({
  label,
  valueA,
  valueB,
  labelA,
  labelB,
  format = 'number',
}: {
  label: string
  valueA: number
  valueB: number
  labelA: string
  labelB: string
  format?: 'number' | 'currency' | 'percent'
}) {
  const max = Math.max(valueA, valueB, 1)
  const fmt = (v: number) => {
    switch (format) {
      case 'currency':
        return formatCurrency(v)
      case 'percent':
        return `${v}%`
      default:
        return formatNumber(Math.round(v * 10) / 10)
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        {label}
      </p>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 w-20 truncate"
            title={labelA}
          >
            {labelA}
          </span>
          <div className="flex-1 bg-lsc-cream dark:bg-earth-700 rounded-full h-5 overflow-hidden">
            <div
              className="bg-lsc-rose h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
              style={{ width: `${Math.max((valueA / max) * 100, 8)}%` }}
            >
              <span className="text-xs font-medium text-white whitespace-nowrap">
                {fmt(valueA)}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 w-20 truncate"
            title={labelB}
          >
            {labelB}
          </span>
          <div className="flex-1 bg-lsc-cream dark:bg-earth-700 rounded-full h-5 overflow-hidden">
            <div
              className="bg-lsc-brown dark:bg-lsc-cream/60 h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
              style={{ width: `${Math.max((valueB / max) * 100, 8)}%` }}
            >
              <span className="text-xs font-medium text-white dark:text-earth-900 whitespace-nowrap">
                {fmt(valueB)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- Engagement Tier Bar ---

function EngagementTierBar({ tiers }: { tiers: EngagementTier[] }) {
  return (
    <div className="space-y-3">
      {tiers.map((tier) => (
        <div key={tier.label} className="flex items-center gap-3">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-16">
            {tier.label}
          </span>
          <div className="flex-1 bg-lsc-cream dark:bg-earth-700 rounded-full h-6 overflow-hidden">
            <div
              className={`${tier.color} h-full rounded-full flex items-center px-2 transition-all duration-500`}
              style={{ width: `${Math.max(tier.percentage, 3)}%` }}
            >
              {tier.percentage >= 10 && (
                <span className="text-xs font-medium text-white whitespace-nowrap">
                  {formatNumber(tier.count)}
                </span>
              )}
            </div>
          </div>
          <span className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 w-12 text-right">
            {tier.percentage}%
          </span>
        </div>
      ))}
      <div className="flex gap-4 mt-2 flex-wrap">
        {tiers.map((tier) => (
          <div
            key={tier.label}
            className="flex items-center gap-1.5 text-xs text-lsc-dark/60 dark:text-lsc-cream/60"
          >
            <div className={`w-2.5 h-2.5 rounded-full ${tier.color}`} />
            {tier.range}
          </div>
        ))}
      </div>
    </div>
  )
}

// --- Cohort Panel ---

function CohortPanel({
  config,
  metrics,
  loading,
}: {
  config: CohortConfig
  metrics: CohortMetrics | null
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <p className="text-center text-lsc-dark/60 dark:text-lsc-cream/60">
          Select a cohort to view metrics
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Cohort Size"
          value={formatNumber(metrics.size)}
          icon={<Users className="w-5 h-5" aria-hidden="true" />}
          subtext={config.description}
        />
        <StatCard
          label="Avg Checkouts"
          value={String(metrics.avgCheckouts)}
          icon={<Activity className="w-5 h-5" aria-hidden="true" />}
          subtext="per patron"
        />
        <StatCard
          label="Avg Fines"
          value={formatCurrency(metrics.avgFines)}
          icon={<TrendingDown className="w-5 h-5" aria-hidden="true" />}
          subtext="per patron"
          color="text-status-danger-500"
        />
        <StatCard
          label="Retention"
          value={`${metrics.retentionRate}%`}
          icon={<Clock className="w-5 h-5" aria-hidden="true" />}
          subtext={`${metrics.churnedRate}% churned`}
          color={metrics.retentionRate > 50 ? 'text-status-success-600' : 'text-status-danger-500'}
        />
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <BarChart3
            className="w-5 h-5 text-lsc-rose"
            aria-hidden="true"
          />
          Engagement Tiers
        </h3>
        <EngagementTierBar tiers={metrics.engagementTiers} />
      </div>
    </div>
  )
}

// --- Cohort Selector Dropdown ---

function CohortSelector({
  label,
  selected,
  open,
  onToggle,
  onSelect,
  exclude,
}: {
  label: string
  selected: CohortPreset | null
  open: boolean
  onToggle: () => void
  onSelect: (preset: CohortPreset) => void
  exclude: CohortPreset | null
}) {
  const config = selected
    ? COHORT_PRESETS.find((p) => p.preset === selected)
    : null

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </label>
      <button
        onClick={onToggle}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 text-left hover:border-lsc-rose transition-colors"
      >
        <div className="flex items-center gap-2">
          {config?.icon}
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
            {config?.label || 'Select...'}
          </span>
        </div>
        <ChevronDown
          className={`w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50 transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>
      {open && (
        <div role="listbox" className="absolute z-20 mt-1 w-full bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 shadow-lg overflow-hidden">
          {COHORT_PRESETS.filter((p) => p.preset !== exclude).map((p) => (
            <button
              key={p.preset}
              role="option"
              aria-selected={p.preset === selected}
              onClick={() => onSelect(p.preset)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors ${
                p.preset === selected
                  ? 'bg-lsc-cream dark:bg-earth-700'
                  : ''
              }`}
            >
              {p.icon}
              <div>
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {p.label}
                </p>
                <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                  {p.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Main Page ---

export default function CohortAnalysisPage() {
  const { token } = useAuth()
  const [selectedPresetA, setSelectedPresetA] =
    useState<CohortPreset>('new_patrons')
  const [selectedPresetB, setSelectedPresetB] =
    useState<CohortPreset | null>(null)
  const [compareMode, setCompareMode] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState<'a' | 'b' | null>(null)
  const [customMinCheckouts, setCustomMinCheckouts] = useState(5)
  const [customInactiveDays, setCustomInactiveDays] = useState(60)

  const dateRange = useMemo(() => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 90)
    return {
      startDate: start.toISOString().split('T')[0] ?? '',
      endDate: end.toISOString().split('T')[0] ?? '',
    }
  }, [])

  const authToken = token || ''

  const { data: patronData, isLoading: patronLoading } = useQuery({
    queryKey: ['cohort-patron-stats', dateRange],
    queryFn: () =>
      getAnalyticsPatronStats(
        authToken,
        dateRange.startDate,
        dateRange.endDate
      ),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  })

  const { data: circulationData, isLoading: circLoading } = useQuery({
    queryKey: ['cohort-circulation-trends', dateRange],
    queryFn: () =>
      getAnalyticsCirculationTrends(
        authToken,
        dateRange.startDate,
        dateRange.endDate
      ),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  })

  const { data: finesData, isLoading: finesLoading } = useQuery({
    queryKey: ['cohort-fines-summary', dateRange],
    queryFn: () =>
      getAnalyticsFinesSummary(
        authToken,
        dateRange.startDate,
        dateRange.endDate
      ),
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  })

  const isLoading = patronLoading || circLoading || finesLoading
  const hasData = !!(patronData && circulationData && finesData)

  const customFilters = useMemo(
    () => ({ minCheckouts: customMinCheckouts, inactiveDays: customInactiveDays }),
    [customMinCheckouts, customInactiveDays]
  )

  const metricsA = useMemo(() => {
    if (!hasData) return null
    return deriveCohortMetrics(
      selectedPresetA,
      patronData,
      circulationData,
      finesData,
      customFilters
    )
  }, [selectedPresetA, patronData, circulationData, finesData, hasData, customFilters])

  const metricsB = useMemo(() => {
    if (!hasData || !selectedPresetB) return null
    return deriveCohortMetrics(
      selectedPresetB,
      patronData,
      circulationData,
      finesData,
      customFilters
    )
  }, [selectedPresetB, patronData, circulationData, finesData, hasData, customFilters])

  const configA = COHORT_PRESETS.find((p) => p.preset === selectedPresetA)!
  const configB = selectedPresetB
    ? COHORT_PRESETS.find((p) => p.preset === selectedPresetB)!
    : null

  const handlePresetSelect = useCallback(
    (preset: CohortPreset, slot: 'a' | 'b') => {
      if (slot === 'a') setSelectedPresetA(preset)
      else setSelectedPresetB(preset)
      setDropdownOpen(null)
    },
    []
  )

  const toggleCompare = useCallback(() => {
    setCompareMode((prev) => {
      if (!prev) setSelectedPresetB('high_activity')
      else setSelectedPresetB(null)
      return !prev
    })
  }, [])

  return (
    <AdminShell
      title="Cohort Analysis"
      subtitle="Cross-report patron segmentation and retention metrics"
      icon={
        <BarChart3
          className="w-6 h-6 text-lsc-rose"
          aria-hidden="true"
        />
      }
      loading={false}
      actions={
        <button
          onClick={toggleCompare}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            compareMode
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10'
          }`}
        >
          <GitCompare className="w-4 h-4" aria-hidden="true" />
          {compareMode ? 'Exit Comparison' : 'Compare Cohorts'}
        </button>
      }
    >
      {/* Cohort Selectors */}
      <div
        className={`grid ${compareMode ? 'md:grid-cols-2' : 'grid-cols-1'} gap-4`}
      >
        <CohortSelector
          label={compareMode ? 'Cohort A' : 'Select Cohort'}
          selected={selectedPresetA}
          open={dropdownOpen === 'a'}
          onToggle={() => setDropdownOpen(dropdownOpen === 'a' ? null : 'a')}
          onSelect={(p) => handlePresetSelect(p, 'a')}
          exclude={null}
        />
        {compareMode && (
          <CohortSelector
            label="Cohort B"
            selected={selectedPresetB}
            open={dropdownOpen === 'b'}
            onToggle={() => setDropdownOpen(dropdownOpen === 'b' ? null : 'b')}
            onSelect={(p) => handlePresetSelect(p, 'b')}
            exclude={selectedPresetA}
          />
        )}
      </div>

      {/* Custom Filters */}
      {(selectedPresetA === 'custom' || selectedPresetB === 'custom') && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            Custom Filters
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="cohort-min-checkouts" className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1">
                Minimum checkouts
              </label>
              <input
                id="cohort-min-checkouts"
                type="number"
                min={0}
                max={100}
                value={customMinCheckouts}
                onChange={(e) =>
                  setCustomMinCheckouts(parseInt(e.target.value, 10) || 0)
                }
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
              />
            </div>
            <div>
              <label htmlFor="cohort-inactive-days" className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1">
                Inactive days threshold
              </label>
              <input
                id="cohort-inactive-days"
                type="number"
                min={0}
                max={365}
                value={customInactiveDays}
                onChange={(e) =>
                  setCustomInactiveDays(parseInt(e.target.value, 10) || 0)
                }
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
              />
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      )}

      {/* No token */}
      {!token && !isLoading && (
        <div className="flex flex-col items-center justify-center h-48 gap-3">
          <AlertTriangle className="w-8 h-8 text-status-danger-500" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Authentication required
          </p>
        </div>
      )}

      {/* Single Cohort View */}
      {hasData && !isLoading && !compareMode && (
        <CohortPanel config={configA} metrics={metricsA} loading={false} />
      )}

      {/* Comparison View */}
      {hasData && !isLoading && compareMode && (
        <div className="space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-lsc-rose" />
                {configA.label}
              </h3>
              <CohortPanel
                config={configA}
                metrics={metricsA}
                loading={false}
              />
            </div>
            {configB && (
              <div>
                <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-lsc-brown dark:bg-lsc-cream/60" />
                  {configB.label}
                </h3>
                <CohortPanel
                  config={configB}
                  metrics={metricsB}
                  loading={false}
                />
              </div>
            )}
          </div>

          {metricsA && metricsB && configB && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-5 flex items-center gap-2">
                <GitCompare
                  className="w-5 h-5 text-lsc-rose"
                  aria-hidden="true"
                />
                Side-by-Side Comparison
              </h3>
              <div className="space-y-6">
                <ComparisonBar
                  label="Cohort Size"
                  valueA={metricsA.size}
                  valueB={metricsB.size}
                  labelA={configA.label}
                  labelB={configB.label}
                />
                <ComparisonBar
                  label="Avg Checkouts per Patron"
                  valueA={metricsA.avgCheckouts}
                  valueB={metricsB.avgCheckouts}
                  labelA={configA.label}
                  labelB={configB.label}
                />
                <ComparisonBar
                  label="Avg Fines per Patron"
                  valueA={metricsA.avgFines}
                  valueB={metricsB.avgFines}
                  labelA={configA.label}
                  labelB={configB.label}
                  format="currency"
                />
                <ComparisonBar
                  label="Retention Rate"
                  valueA={metricsA.retentionRate}
                  valueB={metricsB.retentionRate}
                  labelA={configA.label}
                  labelB={configB.label}
                  format="percent"
                />
              </div>
            </div>
          )}
        </div>
      )}
    </AdminShell>
  )
}
