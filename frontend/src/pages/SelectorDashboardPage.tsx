/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AdminShell } from '../components/shells/AdminShell'
import { StatCard, StatGrid } from '../components/ui'
import { useAuth } from '../contexts/AuthContext'
import {
  Inbox, Lightbulb, ListChecks, ShoppingCart,
} from 'lucide-react'
import {
  getFulfillmentStats,
} from '../api/purchase-requests-api'
import {
  getSelectionList,
  getCollectionIntelligenceReport,
} from '../api/domains/admin/acquisition-api'
import {
  getPurchaseOrders as getPOs,
} from '../api/domains/admin/acquisition-po-api'
import { t } from '@/i18n'
import { RequestsPanel } from '../components/selector/RequestsPanel'
import { IntelligencePanel } from '../components/selector/IntelligencePanel'
import { SelectionListPanel } from '../components/selector/SelectionListPanel'
import { OrdersPanel } from '../components/selector/OrdersPanel'

// ─── Tab type ───────────────────────────────────────────────────
type SelectorTab = 'requests' | 'intelligence' | 'selection' | 'orders'

const TAB_CONFIG: { id: SelectorTab; label: string; icon: React.ElementType }[] = [
  { id: 'requests', label: 'Requests', icon: Inbox },
  { id: 'intelligence', label: 'Intelligence', icon: Lightbulb },
  { id: 'selection', label: 'Selection List', icon: ListChecks },
  { id: 'orders', label: 'Orders', icon: ShoppingCart },
]

// ═══════════════════════════════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════
export default function SelectorDashboardPage(): React.ReactElement {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState<SelectorTab>('requests')

  // ─── Summary queries ──────────────────────────────────────────
  const { data: fulfillmentStats } = useQuery({
    queryKey: ['selectors', 'requests-summary'],
    queryFn: () => getFulfillmentStats(token!),
    enabled: !!token,
  })

  const { data: selectionData } = useQuery({
    queryKey: ['selectors', 'selection-list'],
    queryFn: () => getSelectionList({ per_page: 200 }),
  })

  const { data: ordersData } = useQuery({
    queryKey: ['selectors', 'orders'],
    queryFn: () => getPOs(),
  })

  const { data: intelReport } = useQuery({
    queryKey: ['selectors', 'intelligence'],
    queryFn: () => getCollectionIntelligenceReport(),
    enabled: activeTab === 'intelligence',
    staleTime: 5 * 60 * 1000,
  })

  const requestCount = (fulfillmentStats?.pending_count ?? 0) + (fulfillmentStats?.under_review_count ?? 0)
  const selectionCount = selectionData?.total ?? 0
  const draftOrPendingCount = (ordersData?.items ?? []).filter(
    o => o.status === 'draft' || o.status === 'pending_approval'
  ).length
  const insightCount = intelReport
    ? Object.values(intelReport).reduce((sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0)
    : 0

  const scrollToTab = (tab: SelectorTab) => setActiveTab(tab)

  return (
    <AdminShell title="Selector Dashboard" subtitle="Collection development workflow">
      {/* ─── Summary bar ──────────────────────────────────────── */}
      <StatGrid columns={4}>
        <StatCard title="Patron Requests" value={requestCount} icon={Inbox} color="warning" onClick={() => scrollToTab('requests')} />
        <StatCard title="Selection List" value={selectionCount} icon={ListChecks} color="accent" onClick={() => scrollToTab('selection')} />
        <StatCard title="Active Orders" value={draftOrPendingCount} icon={ShoppingCart} color="success" onClick={() => scrollToTab('orders')} />
        <StatCard title="Insights" value={insightCount} icon={Lightbulb} color="category" onClick={() => scrollToTab('intelligence')} />
      </StatGrid>

      {/* ─── Tab bar ──────────────────────────────────────────── */}
      <div className="mt-6 border-b border-lsc-border dark:border-earth-700" role="tablist" aria-label={t('aria.selectorDashboard.selectorTabs')}>
        <div className="flex gap-1">
          {TAB_CONFIG.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={activeTab === id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === id
                  ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Tab panels ───────────────────────────────────────── */}
      <div className="mt-6" role="tabpanel">
        {activeTab === 'requests' && <RequestsPanel token={token} />}
        {activeTab === 'intelligence' && <IntelligencePanel report={intelReport ?? null} />}
        {activeTab === 'selection' && <SelectionListPanel />}
        {activeTab === 'orders' && <OrdersPanel />}
      </div>
    </AdminShell>
  )
}
