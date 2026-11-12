/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Leaf, Zap, Car, Smartphone, TrendingDown } from 'lucide-react'
import api from '@/lib/api-client'
import PageContainer from '@/components/layout/PageContainer'

interface PublicSummary {
  month: string
  total_co2_grams: number
  total_requests: number
  avg_co2_per_page_grams: number
  benchmark_avg_grams: number
  pct_cleaner_than_average: number
  equivalent_km_driven: number
  equivalent_smartphone_charges: number
}

export default function SustainabilityPage() {
  const [summary, setSummary] = useState<PublicSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<PublicSummary>('/carbon-metrics/public-summary')
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <PageContainer className="py-12">
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-status-success-100 dark:bg-status-success-900/30 mb-4">
          <Leaf className="w-8 h-8 text-status-success-600 dark:text-status-success-400" />
        </div>
        <h1 className="font-serif text-3xl font-bold text-lsc-dark dark:text-lsc-cream mb-3">
          Digital Sustainability
        </h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl mx-auto">
          We believe in transparency about our digital carbon footprint.
          Here's how our website impacts the environment and what we're doing about it.
        </p>
      </div>

      {loading ? (
        <div className="text-center py-8 text-lsc-dark/50 dark:text-lsc-cream/50">
          Loading sustainability data...
        </div>
      ) : summary ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 text-center">
              <TrendingDown className="w-6 h-6 text-status-success-600 dark:text-status-success-400 mx-auto mb-2" />
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {summary.pct_cleaner_than_average.toFixed(0)}%
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                cleaner than average website
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 text-center">
              <Zap className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400 mx-auto mb-2" />
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {summary.avg_co2_per_page_grams < 0.01
                  ? '<0.01g'
                  : `${summary.avg_co2_per_page_grams.toFixed(2)}g`}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                CO<sub>2</sub> per page view (avg: {summary.benchmark_avg_grams}g)
              </p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 text-center">
              <Leaf className="w-6 h-6 text-status-success-600 dark:text-status-success-400 mx-auto mb-2" />
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {(summary.total_co2_grams / 1000).toFixed(2)}kg
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                total CO<sub>2</sub> this month ({summary.month})
              </p>
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 mb-12">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              What does that mean?
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <Car className="w-5 h-5 text-lsc-dark/50 dark:text-lsc-cream/50 shrink-0" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Equivalent to driving <strong>{summary.equivalent_km_driven} km</strong>
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-lsc-dark/50 dark:text-lsc-cream/50 shrink-0" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Or charging a phone <strong>{summary.equivalent_smartphone_charges} times</strong>
                </span>
              </div>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-8 text-center mb-12">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Sustainability data is being collected. Check back soon!
          </p>
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
          How we minimize our footprint
        </h2>
        <ul className="space-y-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <li className="flex items-start gap-2">
            <Leaf className="w-4 h-4 text-status-success-500 shrink-0 mt-0.5" />
            <span><strong>Efficient code:</strong> Optimized builds with tree-shaking, code splitting, and lazy loading reduce transfer sizes.</span>
          </li>
          <li className="flex items-start gap-2">
            <Leaf className="w-4 h-4 text-status-success-500 shrink-0 mt-0.5" />
            <span><strong>Dark mode:</strong> OLED-friendly dark theme reduces display energy on modern screens.</span>
          </li>
          <li className="flex items-start gap-2">
            <Leaf className="w-4 h-4 text-status-success-500 shrink-0 mt-0.5" />
            <span><strong>Minimal JavaScript:</strong> Server-side rendering where possible, progressive enhancement for interactivity.</span>
          </li>
          <li className="flex items-start gap-2">
            <Leaf className="w-4 h-4 text-status-success-500 shrink-0 mt-0.5" />
            <span><strong>Optimized images:</strong> Modern formats (WebP, AVIF), responsive sizing, and lazy loading.</span>
          </li>
          <li className="flex items-start gap-2">
            <Leaf className="w-4 h-4 text-status-success-500 shrink-0 mt-0.5" />
            <span><strong>Caching:</strong> Aggressive browser caching means repeat visits transfer almost no data.</span>
          </li>
        </ul>
      </div>

      <div className="mt-8 text-xs text-lsc-dark/40 dark:text-lsc-cream/40 text-center">
        <p>
          Calculated using the Sustainable Web Design model v4.
          Carbon intensity: US grid average (0.494 kgCO<sub>2</sub>/kWh).
        </p>
      </div>
    </PageContainer>
  )
}
