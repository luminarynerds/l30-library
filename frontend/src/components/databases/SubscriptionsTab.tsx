/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  Database,
  Plus,
  Search,
  Calendar,
  ExternalLink,
  Edit,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import ConfirmDialog from '@/components/ConfirmDialog'
import { CrudTable, StatusBadge, type CrudTableColumn, type CrudTableAction } from '@/components/admin'
import { getCategoryDisplayName, type DatabaseSubscription, type SubscriptionStatus, type DatabaseCategory } from '../../api/databases-api'
import { useTranslation } from '@/i18n'
import { CATEGORY_OPTIONS, subscriptionStatusTone } from './databases-data'
import { parseDate } from '@/utils/format-utils'

interface SubscriptionsTabProps {
  subscriptions: DatabaseSubscription[] | undefined
  isLoading: boolean
  searchQuery: string
  setSearchQuery: (value: string) => void
  statusFilter: SubscriptionStatus | ''
  setStatusFilter: (value: SubscriptionStatus | '') => void
  categoryFilter: DatabaseCategory | ''
  setCategoryFilter: (value: DatabaseCategory | '') => void
  isAdmin: boolean
  onDelete: (id: number) => void
  onEdit: (sub: DatabaseSubscription) => void
  onCreate: () => void
}

export function SubscriptionsTab({
  subscriptions,
  isLoading,
  searchQuery,
  setSearchQuery,
  statusFilter,
  setStatusFilter,
  categoryFilter,
  setCategoryFilter,
  isAdmin,
  onDelete,
  onEdit,
  onCreate,
}: SubscriptionsTabProps): React.ReactElement {
  const { t } = useTranslation()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)
  const [pendingDeleteName, setPendingDeleteName] = useState('')

  const columns: CrudTableColumn<DatabaseSubscription>[] = [
    {
      key: 'database',
      header: 'Database',
      render: (sub) => (
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          <div>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{sub.name}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {sub.vendor?.name || 'No vendor'}
            </p>
          </div>
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category',
      render: (sub) => (
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {getCategoryDisplayName(sub.category)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (sub) => (
        <StatusBadge
          label={sub.status.replace('_', ' ')}
          tone={subscriptionStatusTone(sub.status)}
          size="sm"
        />
      ),
    },
    {
      key: 'expiration',
      header: 'Expiration',
      render: (sub) => (
        <>
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <span className="text-lsc-dark dark:text-lsc-cream">
              {parseDate(sub.subscription_end)?.toLocaleDateString() ?? '-'}
            </span>
          </div>
          {sub.days_until_expiry <= 60 && sub.days_until_expiry >= 0 && (
            <p className="text-xs text-status-warning-600 dark:text-status-warning-400 mt-1">
              {sub.days_until_expiry} days left
            </p>
          )}
        </>
      ),
    },
    {
      key: 'cost',
      header: 'Cost',
      render: (sub) => (
        <span className="text-lsc-dark dark:text-lsc-cream">
          {sub.annual_cost ? `$${parseFloat(sub.annual_cost).toLocaleString()}/yr` : '-'}
        </span>
      ),
    },
  ]

  const actions: CrudTableAction<DatabaseSubscription>[] = [
    {
      label: 'Open',
      icon: ExternalLink as LucideIcon,
      onClick: (sub) => window.open(sub.access_url, '_blank', 'noopener,noreferrer'),
      ariaLabel: (sub) => `Open ${sub.name} in new tab`,
    },
    {
      label: 'Edit',
      icon: Edit as LucideIcon,
      onClick: (sub) => onEdit(sub),
      tone: 'primary',
      ariaLabel: (sub) => `Edit ${sub.name}`,
    },
    ...(isAdmin
      ? [
          {
            label: 'Delete',
            icon: Trash2 as LucideIcon,
            onClick: (sub: DatabaseSubscription) => {
              setPendingDeleteId(sub.id)
              setPendingDeleteName(sub.name)
              setConfirmOpen(true)
            },
            tone: 'danger' as const,
            ariaLabel: (sub: DatabaseSubscription) => `Delete ${sub.name}`,
          },
        ]
      : []),
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70"
            aria-hidden="true"
          />
          <input
            type="text"
            placeholder={t('placeholder.adminDatabases.searchSubscriptions')}
            aria-label={t('aria.adminDatabases.searchSubscriptions')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as SubscriptionStatus | '')}
          className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="expiring_soon">Expiring Soon</option>
          <option value="expired">Expired</option>
          <option value="trial">Trial</option>
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as DatabaseCategory | '')}
          className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
        >
          <option value="">All Categories</option>
          {CATEGORY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={onCreate}
          className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add Subscription
        </button>
      </div>

      <CrudTable
        rows={subscriptions}
        columns={columns}
        actions={actions}
        getRowKey={(sub) => sub.id}
        loading={isLoading}
        emptyLabel="No subscriptions found."
        emptyIcon={Database}
        ariaLabel="Database subscriptions"
      />

      <ConfirmDialog
        isOpen={confirmOpen}
        title={`Delete ${pendingDeleteName}?`}
        message="This subscription will be permanently removed."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { if (pendingDeleteId !== null) onDelete(pendingDeleteId); setConfirmOpen(false); setPendingDeleteId(null); setPendingDeleteName('') }}
        onCancel={() => { setConfirmOpen(false); setPendingDeleteId(null); setPendingDeleteName('') }}
      />
    </div>
  )
}
