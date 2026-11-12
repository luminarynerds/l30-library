/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, BarChart3, Building2, Settings, FileSpreadsheet } from 'lucide-react'
import toast from 'react-hot-toast'

import { useAuth } from '../contexts/AuthContext'
import { AdminShell } from '../components/shells'
import {
  getDashboard,
  getSubscriptions,
  getDatabaseVendors,
  getProxyConfigs,
  deleteSubscription,
  type DatabaseSubscription,
  type SubscriptionStatus,
  type DatabaseCategory,
} from '../api/databases-api'
import { useTranslation } from '@/i18n'
import { AdminTabs } from '@/components/admin'
import { DashboardTab } from '../components/databases/DashboardTab'
import { SubscriptionsTab } from '../components/databases/SubscriptionsTab'
import { VendorsTab } from '../components/databases/VendorsTab'
import { ProxyConfigTab } from '../components/databases/ProxyConfigTab'
import { UsageStatsTab } from '../components/databases/UsageStatsTab'
import { EditSubscriptionModal } from '../components/databases/EditSubscriptionModal'

type TabType = 'dashboard' | 'subscriptions' | 'vendors' | 'proxy' | 'usage'

export default function AdminDatabasesPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<SubscriptionStatus | ''>('')
  const [categoryFilter, setCategoryFilter] = useState<DatabaseCategory | ''>('')
  const [editingSub, setEditingSub] = useState<DatabaseSubscription | null>(null)
  const [showSubModal, setShowSubModal] = useState(false)

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['database-dashboard'],
    queryFn: getDashboard,
    enabled: activeTab === 'dashboard',
  })

  const { data: subscriptions, isLoading: subscriptionsLoading } = useQuery({
    queryKey: ['database-subscriptions', statusFilter, categoryFilter],
    queryFn: () =>
      getSubscriptions({
        ...(statusFilter ? { status_filter: statusFilter } : {}),
        ...(categoryFilter ? { category: categoryFilter } : {}),
        include_inactive: true,
      }),
    enabled: activeTab === 'subscriptions',
  })

  const { data: vendors, isLoading: vendorsLoading } = useQuery({
    queryKey: ['database-vendors'],
    queryFn: getDatabaseVendors,
    enabled: activeTab === 'vendors' || activeTab === 'subscriptions',
  })

  const { data: proxyConfigs, isLoading: proxyLoading } = useQuery({
    queryKey: ['proxy-configs'],
    queryFn: getProxyConfigs,
    enabled: activeTab === 'proxy',
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['database-subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['database-dashboard'] })
      toast.success(t('toast.adminDatabases.subscriptionDeleted'))
    },
    onError: () => {
      toast.error(t('admin.adminDatabases.failedToDeleteSubscription'))
    },
  })

  const filteredSubscriptions = subscriptions?.filter((sub) =>
    sub.name.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const tabs = [
    { id: 'dashboard' as const, label: 'Dashboard', icon: BarChart3 },
    { id: 'subscriptions' as const, label: 'Subscriptions', icon: Database },
    { id: 'vendors' as const, label: 'Vendors', icon: Building2 },
    { id: 'proxy' as const, label: 'Proxy Config', icon: Settings },
    { id: 'usage' as const, label: 'Usage Reports', icon: FileSpreadsheet },
  ]

  const handleOpenEdit = (sub: DatabaseSubscription) => {
    setEditingSub(sub)
    setShowSubModal(true)
  }

  const handleOpenCreate = () => {
    setEditingSub(null)
    setShowSubModal(true)
  }

  const handleCloseModal = () => {
    setShowSubModal(false)
    setEditingSub(null)
  }

  return (
    <AdminShell
      title="Database Management"
      subtitle="Manage database subscriptions, vendors, and proxy configuration."
      icon={<Database className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light" />}
    >
      <div className="mb-6">
        <AdminTabs tabs={tabs} active={activeTab} onChange={setActiveTab} ariaLabel="Database views" />
      </div>

      {activeTab === 'dashboard' && (
        <DashboardTab dashboard={dashboard} isLoading={dashboardLoading} />
      )}

      {activeTab === 'subscriptions' && (
        <SubscriptionsTab
          subscriptions={filteredSubscriptions}
          isLoading={subscriptionsLoading}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          categoryFilter={categoryFilter}
          setCategoryFilter={setCategoryFilter}
          isAdmin={isAdmin}
          onDelete={(id) => deleteMutation.mutate(id)}
          onEdit={handleOpenEdit}
          onCreate={handleOpenCreate}
        />
      )}

      {activeTab === 'vendors' && (
        <VendorsTab vendors={vendors} isLoading={vendorsLoading} isAdmin={isAdmin} />
      )}

      {activeTab === 'proxy' && (
        <ProxyConfigTab configs={proxyConfigs} isLoading={proxyLoading} isAdmin={isAdmin} />
      )}

      {activeTab === 'usage' && <UsageStatsTab isAdmin={isAdmin} />}

      <EditSubscriptionModal
        isOpen={showSubModal}
        onClose={handleCloseModal}
        subscription={editingSub}
        vendors={vendors}
      />
    </AdminShell>
  )
}
