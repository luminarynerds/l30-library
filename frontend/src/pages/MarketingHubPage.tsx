/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useId } from 'react'
import { Link } from 'react-router-dom'
import {
  Sparkles, Clock, BarChart3, AlertCircle,
  LayoutGrid, Megaphone, Heart, Users, TrendingUp, ChevronRight, Tag,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import AIContentGenerator from '@/components/marketing/AIContentGenerator'
import { useTranslation } from '@/i18n'
import { StaffLayout } from '@/components/staff/StaffLayout'
import StatsHeader from '@/components/marketing-hub/StatsHeader'
import { HistoryTab } from '@/components/marketing-hub/HistoryTab'
import { AnalyticsTab } from '@/components/marketing-hub/AnalyticsTab'
import {
  useOrganizationFeatures,
  type OrganizationFeatures,
} from '@/contexts/OrganizationFeaturesContext'
import PageContainer from '@/components/layout/PageContainer'

type TabId = 'create' | 'history' | 'analytics' | 'directory'

interface Tab {
  id: TabId
  labelKey: string
  fallbackLabel: string
  icon: React.ElementType
}

const allTabs: Tab[] = [
  { id: 'create', labelKey: 'marketingHub.tabCreate', fallbackLabel: 'Create', icon: Sparkles },
  { id: 'history', labelKey: 'marketingHub.tabHistory', fallbackLabel: 'History', icon: Clock },
  { id: 'analytics', labelKey: 'marketingHub.tabAnalytics', fallbackLabel: 'Analytics', icon: BarChart3 },
  { id: 'directory', labelKey: 'marketingHub.tabDirectory', fallbackLabel: 'Directory', icon: LayoutGrid },
]

interface DirectoryItem {
  label: string
  path: string
  description: string
  icon: React.ElementType
  featureFlag?: keyof OrganizationFeatures
}

interface DirectoryCategory {
  title: string
  items: DirectoryItem[]
}

// Directory entries folded in from the former MarketingHubNavigationPage.
// The self-referential "Marketing Hub" entry was dropped (this IS the hub).
const DIRECTORY_CATEGORIES: DirectoryCategory[] = [
  {
    title: 'Outreach',
    items: [
      { label: 'Interest Categories', path: '/staff/marketing', description: 'Newsletter interest categories patrons can subscribe to', icon: Tag, featureFlag: 'outreach_enabled' },
      { label: 'Outreach', path: '/staff/outreach', description: 'Community engagement and partnerships', icon: Heart, featureFlag: 'outreach_enabled' },
      { label: 'Social Sharing', path: '/staff/admin/social-sharing', description: 'Social media configuration', icon: Users },
    ],
  },
  {
    title: 'Analytics',
    items: [
      { label: 'Sharing Analytics', path: '/staff/admin/analytics/sharing', description: 'Content sharing metrics and trends', icon: BarChart3 },
      { label: 'Journey Analytics', path: '/staff/admin/analytics/journeys', description: 'Patron journey funnel analysis', icon: TrendingUp, featureFlag: 'outreach_enabled' },
    ],
  },
]

export default function MarketingHubPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const aiEnabled = isFeatureEnabled('ai_tools_enabled')
  const [activeTab, setActiveTab] = useState<TabId>(aiEnabled ? 'create' : 'directory')
  const tablistId = useId()

  // AI generator + History are AI-only surfaces; hide their tabs when ai_tools_enabled is off.
  const tabs = useMemo(
    () => allTabs.filter((tab) => aiEnabled || (tab.id !== 'create' && tab.id !== 'history')),
    [aiEnabled],
  )

  const enabledCategories = useMemo(() => {
    return DIRECTORY_CATEGORIES.map((cat) => ({
      ...cat,
      items: cat.items.filter((item) => !item.featureFlag || isFeatureEnabled(item.featureFlag)),
    })).filter((cat) => cat.items.length > 0)
  }, [isFeatureEnabled])

  if (!user || !token || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle aria-hidden="true" className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4 opacity-90" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            {t('marketingHub.staffOrAdminAccessRequired')}
          </p>
        </PageContainer>
      </div>
    )
  }

  return (
    <StaffLayout title="Marketing Hub">
      <PageContainer className="py-8">
        <StatsHeader token={token} onSelectTab={(id) => setActiveTab(id as TabId)} />

        {/* Tabs */}
        <div
          role="tablist"
          aria-label="Marketing Hub sections"
          id={tablistId}
          className="flex gap-2 mb-6 overflow-x-auto pb-2"
        >
          {tabs.map((tab) => {
            const selected = activeTab === tab.id
            const label = t(tab.labelKey, tab.fallbackLabel)
            return (
              <button
                key={tab.id}
                id={`${tablistId}-${tab.id}`}
                role="tab"
                type="button"
                aria-selected={selected}
                aria-controls={`${tablistId}-${tab.id}-panel`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose ${
                  selected
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700'
                }`}
              >
                <tab.icon aria-hidden="true" className="w-4 h-4" />
                {label}
              </button>
            )
          })}
        </div>

        {/* Tab Panels */}
        <div
          role="tabpanel"
          id={`${tablistId}-${activeTab}-panel`}
          aria-labelledby={`${tablistId}-${activeTab}`}
          tabIndex={0}
          className="focus:outline-none"
        >
          {activeTab === 'create' && aiEnabled && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <AIContentGenerator />
            </div>
          )}
          {activeTab === 'history' && aiEnabled && <HistoryTab token={token} />}
          {activeTab === 'analytics' && <AnalyticsTab token={token} />}
          {activeTab === 'directory' && (
            <DirectoryPanel categories={enabledCategories} />
          )}
        </div>
      </PageContainer>
    </StaffLayout>
  )
}

function DirectoryPanel({ categories }: { categories: DirectoryCategory[] }): React.ReactElement {
  if (categories.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        No additional marketing tools are enabled for your library.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {categories.map((category) => (
        <section
          key={category.title}
          aria-labelledby={`directory-cat-${category.title}`}
          className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden"
        >
          <div className="px-5 py-4 flex items-center gap-3 border-b border-lsc-border dark:border-earth-700">
            <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 p-2 rounded-lg flex-shrink-0">
              <Megaphone aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
            </div>
            <div className="min-w-0 flex-1">
              <h2
                id={`directory-cat-${category.title}`}
                className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                {category.title}
              </h2>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                {category.items.length} tool{category.items.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <ul className="divide-y divide-lsc-border/50 dark:divide-earth-700/50">
            {category.items.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className="flex items-center justify-between px-5 py-3 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors group focus:outline-none focus:ring-2 focus:ring-inset focus:ring-lsc-rose"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Icon aria-hidden="true" className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
                          {item.label}
                        </p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 truncate">
                          {item.description}
                        </p>
                      </div>
                    </div>
                    <ChevronRight aria-hidden="true" className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose flex-shrink-0 ml-2 transition-colors" />
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
    </div>
  )
}
