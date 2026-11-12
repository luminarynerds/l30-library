/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import {
  BookOpen, Users, TrendingUp, BarChart3, Library,
  ArrowRight,
} from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "@/i18n"
import { fetchApi } from "@/lib/api-client"
import StandardPageLayout from "@/components/StandardPageLayout"

interface PublicOverview {
  total_items_in_collection: number
  total_cardholders: number
  checkouts_today: number
  checkouts_this_month: number
  checkouts_this_year: number
  active_checkouts: number
}

interface MonthlyTrendsResponse {
  trends: { month: string; checkouts: number }[]
}

interface PopularItemsResponse {
  items: { id: number; title: string; author: string; checkout_count: number }[]
  period_days: number
}

export default function AboutStatsContent(): React.ReactElement {
  const { t } = useTranslation()

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["publicStatsOverview"],
    queryFn: () => fetchApi<PublicOverview>("/public/stats/overview"),
    staleTime: 5 * 60 * 1000,
  })

  const { data: trendsData, isLoading: trendsLoading } = useQuery({
    queryKey: ["publicStatsTrends"],
    queryFn: () => fetchApi<MonthlyTrendsResponse>("/public/stats/monthly-trends", { params: { months: 12 } }),
    staleTime: 5 * 60 * 1000,
  })

  const { data: popularData } = useQuery({
    queryKey: ["publicStatsPopular"],
    queryFn: () => fetchApi<PopularItemsResponse>("/public/stats/popular-items", { params: { limit: 10, days: 30 } }),
    staleTime: 5 * 60 * 1000,
  })

  const trends = trendsData?.trends ?? []
  const popular = popularData?.items ?? []
  const isLoading = overviewLoading && trendsLoading

  const formatNumber = (n: number) => n.toLocaleString()

  const heroStats = overview
    ? [
        { label: t("publicStats.collection", "Items in collection (live)"), value: formatNumber(overview.total_items_in_collection), icon: Library },
        { label: t("publicStats.cardholders", "Active cardholders (live)"), value: formatNumber(overview.total_cardholders), icon: Users },
        { label: t("publicStats.checkoutsToday", "Checkouts today (live)"), value: formatNumber(overview.checkouts_today), icon: BookOpen },
        { label: t("publicStats.checkoutsYear", "Checkouts year-to-date (live)"), value: formatNumber(overview.checkouts_this_year), icon: TrendingUp },
      ]
    : []

  const maxCheckouts = Math.max(...trends.map((t) => t.checkouts), 1)

  return (
    <StandardPageLayout
      title={t("publicStats.title", "Library By the Numbers")}
      subtitle={t("publicStats.subtitle", "See how our community uses the library")}
      icon={BarChart3}
      isLoading={isLoading}
    >
      {/* Hero Stats */}
      {overview && (
        <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-3">
          {heroStats.map((stat) => {
            const Icon = stat.icon
            return (
              <div key={stat.label} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
                <Icon className="w-8 h-8 text-library-600 mx-auto mb-3" aria-hidden="true" />
                <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
                <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{stat.label}</p>
              </div>
            )
          })}
        </div>
        <p className="text-xs text-earth-600 dark:text-earth-400 text-center mb-12">
          These counts update every night from our catalog. They reflect circulating items today, not lifetime totals.
        </p>
        </>
      )}

      {/* Secondary stats */}
      {overview && (
        <div className="grid grid-cols-2 gap-6 mb-12">
          <div className="bg-sage-50 dark:bg-sage-900/30 rounded-xl border border-sage-200 dark:border-sage-800 p-6 text-center">
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{formatNumber(overview.checkouts_this_month)}</p>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t("publicStats.checkoutsMonth", "Checkouts This Month")}</p>
          </div>
          <div className="bg-sage-50 dark:bg-sage-900/30 rounded-xl border border-sage-200 dark:border-sage-800 p-6 text-center">
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{formatNumber(overview.active_checkouts)}</p>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t("publicStats.activeCheckouts", "Currently Checked Out")}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Monthly Trends */}
        {trends.length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-6">
              {t("publicStats.monthlyTrends", "Monthly Checkouts")}
            </h2>
            <div className="space-y-3">
              {trends.map((trend) => {
                const pct = (trend.checkouts / maxCheckouts) * 100
                const monthLabel = new Date(trend.month + "-01").toLocaleDateString(undefined, { year: "2-digit", month: "short" })
                return (
                  <div key={trend.month} className="flex items-center gap-3">
                    <span className="text-xs text-earth-600 dark:text-earth-400 w-16 text-right font-mono">
                      {monthLabel}
                    </span>
                    <div className="flex-1 bg-earth-100 dark:bg-earth-700 rounded-full h-6 overflow-hidden">
                      <div
                        className="bg-library-500 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 w-12 text-right">
                      {formatNumber(trend.checkouts)}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Popular Items */}
        {popular.length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-6">
              {t("publicStats.popularItems", "Most Popular This Month")}
            </h2>
            <ol className="space-y-3">
              {popular.map((item, idx) => (
                <li key={item.id} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-library-100 dark:bg-library-900/30 text-library-700 dark:text-library-300 text-xs font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/catalog/${item.id}`}
                      className="text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:text-library-600 transition-colors truncate block"
                      title={item.title}
                    >
                      {item.title}
                    </Link>
                    {item.author && (
                      <p className="text-xs text-earth-600 dark:text-earth-400">{item.author}</p>
                    )}
                  </div>
                  <span className="text-xs text-earth-600 dark:text-earth-400 flex-shrink-0">
                    {item.checkout_count} checkouts
                  </span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {/* CTA */}
      <div className="mt-12 text-center bg-library-50 dark:bg-library-900/20 rounded-xl border border-library-200 dark:border-library-800 p-8">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {t("publicStats.joinCta", "Join Our Community")}
        </h2>
        <p className="text-earth-600 dark:text-earth-400 mb-4">
          {t("publicStats.joinCtaDescription", "Get a library card and start exploring our collection today.")}
        </p>
        <Link
          to="/card-application"
          className="inline-flex items-center gap-2 px-6 py-3 bg-library-600 hover:bg-library-700 text-white rounded-lg transition-colors font-medium"
        >
          {t("publicStats.getCard", "Get a Library Card")}
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </StandardPageLayout>
  )
}
