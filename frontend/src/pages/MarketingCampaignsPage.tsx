/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId } from 'react'
import {
  BarChart3,
  Tag,
  AlertCircle,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { AnalyticsTab } from '../components/marketing/AnalyticsTab'
import { InterestsTab } from '../components/marketing/InterestsTab'
import PageContainer from '@/components/layout/PageContainer'

type TabId = 'interests' | 'analytics'

interface Tab {
  id: TabId
  label: string
  icon: React.ElementType
}

const tabs: Tab[] = [
  { id: 'interests', label: 'Interest Categories', icon: Tag },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
]

export default function MarketingCampaignsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabId>('interests')
  const tablistId = useId()

  if (!user || !token || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('marketingCampaigns.staffOrAdminAccessRequired')}</p>
        </PageContainer>
      </div>
    )
  }

  return (
    <AdminShell title="Marketing">
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-8">
        <PageContainer>
          <div className="mb-8">
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Marketing
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage newsletter interest categories and marketing analytics
            </p>
          </div>

          <div
            role="tablist"
            aria-label="Marketing sections"
            id={tablistId}
            className="flex gap-2 mb-6 overflow-x-auto pb-2"
          >
            {tabs.map((tab) => {
              const selected = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  id={`${tablistId}-${tab.id}`}
                  role="tab"
                  aria-selected={selected}
                  aria-controls={`${tablistId}-${tab.id}-panel`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-colors whitespace-nowrap ${
                    selected
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              )
            })}
          </div>

          <div
            role="tabpanel"
            id={`${tablistId}-${activeTab}-panel`}
            aria-labelledby={`${tablistId}-${activeTab}`}
            tabIndex={0}
          >
            {activeTab === 'interests' && <InterestsTab token={token!} />}
            {activeTab === 'analytics' && <AnalyticsTab token={token!} />}
          </div>
        </PageContainer>
      </div>
    </AdminShell>
  )
}
