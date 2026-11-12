/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Admin UI for the data-driven patron home page (PR B of the redesign).
 * Three tabs: Hero, Shelves, Page config. All content rendered on `/`
 * comes from the rows this page edits — see PR #670.
 */
import { useState } from 'react'
import { Home, Star, LayoutGrid, Settings } from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import { useTranslation } from '@/i18n'
import { HeroPickList } from '../components/admin/home/HeroPickList'
import { ShelfList } from '../components/admin/home/ShelfList'
import { PageConfigEditor } from '../components/admin/home/PageConfigEditor'
import PageContainer from '@/components/layout/PageContainer'

type Tab = 'hero' | 'shelves' | 'page'

export default function AdminHomePage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('hero')

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'hero', label: t('admin.adminHomePage.tabs.hero', 'Hero'), icon: Star },
    { id: 'shelves', label: t('admin.adminHomePage.tabs.shelves', 'Shelves'), icon: LayoutGrid },
    { id: 'page', label: t('admin.adminHomePage.tabs.page', 'Page'), icon: Settings },
  ]

  return (
    <AdminShell
      title={t('admin.adminHomePage.title', 'Home Page')}
      subtitle={t(
        'admin.adminHomePage.subtitle',
        'Curate the hero pick, shelves, and page chrome shown on the patron home page.'
      )}
      icon={<Home className="w-6 h-6 text-lsc-rose" />}
    >
      <PageContainer>
        <div
          role="tablist"
          aria-label={t('admin.adminHomePage.tablistLabel', 'Home page sections')}
          className="flex gap-1 border-b border-lsc-border dark:border-earth-700 mb-6"
        >
          {tabs.map((tEntry) => {
            const Icon = tEntry.icon
            const active = tab === tEntry.id
            return (
              <button
                key={tEntry.id}
                id={`home-tab-${tEntry.id}-trigger`}
                role="tab"
                aria-selected={active}
                aria-controls={`home-tab-${tEntry.id}`}
                onClick={() => setTab(tEntry.id)}
                className={`inline-flex items-center gap-1.5 px-4 py-2 -mb-px text-sm font-medium border-b-2 transition-colors ${
                  active
                    ? 'border-lsc-rose text-lsc-rose'
                    : 'border-transparent text-earth-600 dark:text-earth-300 hover:text-lsc-dark dark:hover:text-lsc-cream'
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                {tEntry.label}
              </button>
            )
          })}
        </div>

        <div
          id={`home-tab-${tab}`}
          role="tabpanel"
          aria-labelledby={`home-tab-${tab}-trigger`}
        >
          {tab === 'hero' && <HeroPickList />}
          {tab === 'shelves' && <ShelfList />}
          {tab === 'page' && <PageConfigEditor />}
        </div>
      </PageContainer>
    </AdminShell>
  )
}
