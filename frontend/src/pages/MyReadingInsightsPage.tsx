/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  BarChart3, BookOpen, TrendingUp, Calendar, Award, Share2,
  Flame, Users, PieChart, ArrowRight
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { EmptyState } from '../components/ui/EmptyState'
import { useTranslation } from '@/i18n'

type InsightsTab = 'overview' | 'trends' | 'genres' | 'year-in-review'

export default function MyReadingInsightsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<InsightsTab>('overview')
  const [selectedYear] = useState(new Date().getFullYear())

  if (!isAuthenticated) {
    return (
      <div className="py-12 text-center">
        <BookOpen className="w-12 h-12 text-lsc-rose/30 mx-auto mb-4" />
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('myReadingInsights.signInToViewYour')}</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('myReadingInsights.trackYourReadingJourneyWith')}</p>
      </div>
    )
  }

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: BarChart3 },
    { id: 'trends' as const, label: 'Trends', icon: TrendingUp },
    { id: 'genres' as const, label: 'Genre Map', icon: PieChart },
    { id: 'year-in-review' as const, label: 'Year in Review', icon: Award },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            My Reading Insights
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Discover patterns and trends in your reading journey, {user?.first_name}.
          </p>
        </div>
        <Link
          to="/reading-challenge"
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose/10 hover:bg-lsc-rose/20 text-lsc-rose rounded-xl text-sm font-medium transition-colors"
        >
          <Award className="w-4 h-4" />
          Reading Challenge
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 bg-lsc-white dark:bg-earth-800 rounded-xl p-1.5 shadow-sm border border-lsc-border dark:border-earth-700">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-lsc-rose text-white'
                  : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Summary Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-lsc-rose/10 flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-lsc-rose" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Books This Year</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">0</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {selectedYear}
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-status-success-100 dark:bg-status-success-900/30 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Avg / Month</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">0</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                books per month
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-status-warning-100 dark:bg-status-warning-900/30 flex items-center justify-center">
                  <Flame className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Current Streak</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">0</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                days
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-category-100 dark:bg-category-900/30 flex items-center justify-center">
                  <Users className="w-5 h-5 text-category-600 dark:text-category-400" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Unique Authors</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">0</p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                authors explored
              </p>
            </div>
          </div>

          {/* Reading Activity Heatmap Placeholder */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-4">
              Reading Activity
            </h3>
            <EmptyState
              icon={Calendar}
              title={t('myReadingInsights.yourReadingActivityWillAppear')}
              description="Check out books from the library to start building your reading heatmap."
              primaryAction={{ label: 'Browse Catalog', href: '/catalog' }}
              size="sm"
              showTip
            />
          </div>

          {/* Quick Links */}
          <div className="grid sm:grid-cols-2 gap-4">
            <Link
              to="/reading-challenge"
              className="flex items-center gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
            >
              <div className="w-10 h-10 rounded-xl bg-lsc-rose/10 flex items-center justify-center">
                <Award className="w-5 h-5 text-lsc-rose" />
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">Reading Challenge</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('myReadingInsights.trackAchievementsAndEarnBadges')}</p>
              </div>
              <ArrowRight className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
            </Link>
            <Link
              to="/account"
              className="flex items-center gap-4 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors group"
            >
              <div className="w-10 h-10 rounded-xl bg-lsc-rose/10 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-lsc-rose" />
              </div>
              <div className="flex-1">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">Checkout History</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('myReadingInsights.viewYourFullBorrowingHistory')}</p>
              </div>
              <ArrowRight className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
            </Link>
          </div>
        </div>
      )}

      {/* Trends Tab */}
      {activeTab === 'trends' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-4">
            Monthly Reading Velocity
          </h3>
          <EmptyState
            icon={TrendingUp}
            title={t('myReadingInsights.yourReadingTrendsWillAppear')}
            description="As you check out and return books, we'll chart your reading velocity over time."
            primaryAction={{ label: 'Browse Catalog', href: '/catalog' }}
            size="md"
          />
        </div>
      )}

      {/* Genres Tab */}
      {activeTab === 'genres' && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream mb-4">
            Genre Breakdown
          </h3>
          <EmptyState
            icon={PieChart}
            title={t('myReadingInsights.yourGenreMapWillAppear')}
            description="Discover which genres you gravitate toward most. Every checkout adds a data point."
            primaryAction={{ label: 'Browse Catalog', href: '/catalog' }}
            size="md"
          />
        </div>
      )}

      {/* Year in Review Tab */}
      {activeTab === 'year-in-review' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-lsc-rose/10 via-category-50 to-lsc-cream dark:from-lsc-rose/20 dark:via-category-900/20 dark:to-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center">
            <Award className="w-16 h-16 text-lsc-rose mx-auto mb-4" />
            <h3 className="font-serif font-bold text-2xl text-lsc-dark dark:text-lsc-cream mb-2">
              {selectedYear - 1} Year in Review
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mx-auto mb-6">
              Your personalized reading year in review will be available once you have checkout history.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link
                to="/catalog"
                className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 transition-colors"
              >
                <BookOpen className="w-5 h-5" />
                Start Reading
              </Link>
              <button
                className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors"
                disabled
              >
                <Share2 className="w-5 h-5" />
                Share
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
