/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import {
  Book,
  Headphones,
  Film,
  Music,
  Newspaper,
  DollarSign,
  Clock,
  Users,
  Leaf,
  ThumbsUp,
  ThumbsDown,
  Info,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Scale,
  FileText,
} from 'lucide-react'
import {
  getMaterialCosts,
  getCostSummary,
  type MaterialCostComparisonResponse,
  type CostComparisonSummary,
  type MaterialFormatCosts,
  type CostFactor,
} from '../api/material-cost-api'
import { useTranslation } from '@/i18n'

// Category icons mapping
const categoryIcons: Record<string, React.ElementType> = {
  Books: Book,
  Audiobooks: Headphones,
  Video: Film,
  Music: Music,
  Periodicals: Newspaper,
}

// Format a decimal string as currency
function formatCurrency(value: string): string {
  const num = parseFloat(value)
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num)
}

// Cost range display component
function CostRange({ factor }: { factor: CostFactor }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-700 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between mb-2">
        <h5 className="font-medium text-lsc-dark dark:text-lsc-cream">{factor.name}</h5>
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{factor.unit}</span>
      </div>
      <div className="flex items-baseline gap-1 mb-2">
        <span className="text-lg font-semibold text-lsc-rose dark:text-lsc-rose-light">
          {formatCurrency(factor.low_estimate)}
        </span>
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">-</span>
        <span className="text-lg font-semibold text-lsc-rose dark:text-lsc-rose-light">
          {formatCurrency(factor.high_estimate)}
        </span>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{factor.description}</p>
      {factor.notes && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 italic">{factor.notes}</p>
      )}
    </div>
  )
}

// Format card component
function FormatCard({ format }: { format: MaterialFormatCosts }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-5 text-left hover:bg-sage-50 dark:hover:bg-earth-700 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
              {format.format_name}
            </h4>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {format.description}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('materialCostComparison.estTotalCostRange')}</div>
              <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                {formatCurrency(
                  (
                    parseFloat(format.acquisition_cost.low_estimate) +
                    parseFloat(format.processing_cost.low_estimate)
                  ).toString()
                )}{' '}
                -{' '}
                {formatCurrency(
                  (
                    parseFloat(format.acquisition_cost.high_estimate) +
                    parseFloat(format.processing_cost.high_estimate)
                  ).toString()
                )}
              </div>
            </div>
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            ) : (
              <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            )}
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-lsc-border dark:border-earth-700 p-5 space-y-6">
          {/* Cost breakdown */}
          <div>
            <h5 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-lsc-rose" />
              Cost Breakdown
            </h5>
            <div className="grid sm:grid-cols-2 gap-3">
              <CostRange factor={format.acquisition_cost} />
              <CostRange factor={format.processing_cost} />
              <CostRange factor={format.storage_cost} />
              <CostRange factor={format.maintenance_cost} />
            </div>
          </div>

          {/* Key metrics */}
          <div className="grid sm:grid-cols-3 gap-4">
            {format.typical_lifespan_years && (
              <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-700 rounded-lg border border-lsc-border dark:border-earth-700">
                <Clock className="w-5 h-5 text-sage-600 dark:text-sage-400 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    Typical Lifespan
                  </div>
                  <div className="text-lg font-semibold text-sage-600 dark:text-sage-400">
                    {format.typical_lifespan_years} years
                  </div>
                </div>
              </div>
            )}
            <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-700 rounded-lg border border-lsc-border dark:border-earth-700">
              <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5" />
              <div>
                <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Simultaneous Users
                </div>
                <div className="text-lg font-semibold text-lsc-rose dark:text-lsc-rose-light">
                  {format.simultaneous_users}
                </div>
              </div>
            </div>
            {format.licensing_model && (
              <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-700 rounded-lg border border-lsc-border dark:border-earth-700">
                <FileText className="w-5 h-5 text-category-600 dark:text-category-400 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    Licensing Model
                  </div>
                  <div className="text-sm text-category-600 dark:text-category-400">
                    {format.licensing_model}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Environmental note */}
          {format.environmental_notes && (
            <div className="flex items-start gap-3 p-4 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg border border-status-success-200 dark:border-status-success-800">
              <Leaf className="w-5 h-5 text-status-success-600 dark:text-status-success-400 mt-0.5 flex-shrink-0" />
              <div>
                <div className="text-sm font-medium text-status-success-800 dark:text-status-success-300 mb-1">
                  Environmental Considerations
                </div>
                <p className="text-sm text-status-success-700 dark:text-status-success-400">
                  {format.environmental_notes}
                </p>
              </div>
            </div>
          )}

          {/* Advantages and Limitations */}
          <div className="grid sm:grid-cols-2 gap-4">
            {format.advantages.length > 0 && (
              <div>
                <h6 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                  <ThumbsUp className="w-4 h-4 text-status-success-600" />
                  Advantages
                </h6>
                <ul className="space-y-1">
                  {format.advantages.map((adv, idx) => (
                    <li
                      key={idx}
                      className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2"
                    >
                      <span className="text-status-success-500 mt-1">+</span>
                      {adv}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {format.limitations.length > 0 && (
              <div>
                <h6 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                  <ThumbsDown className="w-4 h-4 text-status-warning-600" />
                  Limitations
                </h6>
                <ul className="space-y-1">
                  {format.limitations.map((lim, idx) => (
                    <li
                      key={idx}
                      className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-start gap-2"
                    >
                      <span className="text-status-warning-500 mt-1">-</span>
                      {lim}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Summary card component
function SummaryCard({ summary }: { summary: CostComparisonSummary }) {
  const { t } = useTranslation();
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">{summary.format_name}</h4>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Cost per circulation</span>
          <span className="font-semibold text-lsc-rose dark:text-lsc-rose-light">
            {formatCurrency(summary.avg_total_cost_per_circulation)}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Typical circulations</span>
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
            {summary.typical_circulations_per_copy}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('materialCostComparison.costPerUserSlot')}</span>
          <span className="font-medium text-lsc-dark dark:text-lsc-cream">
            {formatCurrency(summary.cost_per_simultaneous_user)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function MaterialCostComparisonPage(): React.ReactElement {
  const [data, setData] = useState<MaterialCostComparisonResponse | null>(null)
  const [summary, setSummary] = useState<CostComparisonSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const [costData, summaryData] = await Promise.all([getMaterialCosts(), getCostSummary()])
        setData(costData)
        setSummary(summaryData)
        if (costData.categories.length > 0) {
          setActiveCategory(costData.categories[0]!.category_name)
        }
      } catch (err: unknown) {
        setError('Failed to load cost comparison data')
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark">
        <div className="text-center">
          <div className="motion-safe:animate-spin rounded-full h-12 w-12 border-b-2 border-lsc-rose mx-auto mb-4"></div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading cost data...</p>
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-lsc-cream dark:bg-lsc-dark">
        <div className="text-center">
          <p className="text-status-danger-600 dark:text-status-danger-400">{error || 'Failed to load data'}</p>
        </div>
      </div>
    )
  }

  const activeTab = data.categories.find((c) => c.category_name === activeCategory)

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Header */}
      <header className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <div className="container mx-auto px-4 py-12 max-w-5xl">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-full flex items-center justify-center">
              <Scale className="w-6 h-6 text-lsc-rose" />
            </div>
            <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Material Cost Transparency
            </h1>
          </div>
          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-3xl">
            Understanding the true cost of library materials. This tool provides factual,
            unbiased cost breakdowns to help you understand the economics behind different
            formats.
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        {/* Methodology note */}
        <div className="bg-earth-50 dark:bg-earth-800/20 rounded-xl p-5 border border-lsc-border dark:border-earth-700 mb-8">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-serif font-semibold text-earth-800 dark:text-lsc-rose-light mb-1">
                About This Data
              </h3>
              <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">{data.methodology_note}</p>
              <div className="mt-3">
                <p className="text-xs text-lsc-rose dark:text-lsc-rose-light font-medium mb-1">
                  Data sources:
                </p>
                <ul className="text-xs text-lsc-rose dark:text-lsc-rose-light list-disc list-inside">
                  {data.data_sources.map((source, idx) => (
                    <li key={idx}>{source}</li>
                  ))}
                </ul>
              </div>
              <p className="text-xs text-earth-600 dark:text-lsc-rose-light mt-2">
                Last updated: {data.last_updated}
              </p>
            </div>
          </div>
        </div>

        {/* Quick Summary */}
        {summary.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-5 h-5 text-lsc-rose" />
              <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Quick Comparison
              </h2>
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Average cost-per-use estimates based on typical library usage patterns.
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {summary.map((s) => (
                <SummaryCard key={s.format_type} summary={s} />
              ))}
            </div>
          </section>
        )}

        {/* Category tabs */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            {data.categories.map((category) => {
              const Icon = categoryIcons[category.category_name] || Book
              const isActive = activeCategory === category.category_name
              return (
                <button
                  key={category.category_name}
                  onClick={() => setActiveCategory(category.category_name)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                    isActive
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-sage-50 dark:hover:bg-earth-700 border border-lsc-border dark:border-earth-700'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {category.category_name}
                </button>
              )
            })}
          </div>
        </div>

        {/* Active category content */}
        {activeTab && (
          <section>
            <div className="mb-6">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {activeTab.category_name}
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {activeTab.category_description}
              </p>
            </div>

            <div className="space-y-4">
              {activeTab.formats.map((format) => (
                <FormatCard key={format.format_type} format={format} />
              ))}
            </div>
          </section>
        )}

        {/* Footer note */}
        <footer className="mt-12 pt-8 border-t border-lsc-border dark:border-earth-700">
          <div className="bg-sage-50 dark:bg-sage-900/20 rounded-xl p-5">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              Why Transparency Matters
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Libraries make complex decisions about which formats to purchase based on many
              factors: cost, patron demand, accessibility, longevity, and licensing terms. By
              sharing this information openly, we hope to help you understand these trade-offs
              and participate in conversations about how your library spends its budget.
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
              Have questions about our collection decisions?{' '}
              <a href="/contact" className="text-lsc-rose hover:underline">
                Contact us
              </a>{' '}
              - we'd love to hear from you.
            </p>
          </div>
        </footer>
      </main>
    </div>
  )
}
