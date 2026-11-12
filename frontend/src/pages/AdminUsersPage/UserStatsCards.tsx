/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  Users,
  UserCheck,
  UserPlus,
  Lock,
} from 'lucide-react'
import type { UserStats } from '../../api/staff-api'

interface UserStatsCardsProps {
  stats: UserStats | null
  statsLoading: boolean
}

const StatCardSkeleton: React.FC = () => (
  <div className="motion-safe:animate-pulse">
    <div className="flex items-center gap-3 mb-3">
      <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-700 rounded-xl" />
      <div className="h-4 bg-lsc-cream dark:bg-earth-700 rounded w-20" />
    </div>
    <div className="h-8 bg-lsc-cream dark:bg-earth-700 rounded w-16" />
  </div>
)

const UserStatsCards: React.FC<UserStatsCardsProps> = ({ stats, statsLoading }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {/* Total Users */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 shadow-sm">
        {statsLoading ? (
          <StatCardSkeleton />
        ) : (
          <>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-earth-100 dark:bg-earth-800/30 rounded-xl flex items-center justify-center">
                <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                Total Users
              </span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats?.total_users?.toLocaleString() ?? '0'}
            </p>
          </>
        )}
      </div>

      {/* Active Users */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 shadow-sm">
        {statsLoading ? (
          <StatCardSkeleton />
        ) : (
          <>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-status-success-100 dark:bg-status-success-900/30 rounded-xl flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
              </div>
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                Active Users
              </span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats?.active_users?.toLocaleString() ?? '0'}
            </p>
          </>
        )}
      </div>

      {/* New This Month */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 shadow-sm">
        {statsLoading ? (
          <StatCardSkeleton />
        ) : (
          <>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-category-100 dark:bg-category-900/30 rounded-xl flex items-center justify-center">
                <UserPlus className="w-5 h-5 text-category-600 dark:text-category-400" />
              </div>
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                New This Month
              </span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats?.new_this_month?.toLocaleString() ?? '0'}
            </p>
          </>
        )}
      </div>

      {/* Locked Accounts */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 shadow-sm">
        {statsLoading ? (
          <StatCardSkeleton />
        ) : (
          <>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-xl flex items-center justify-center">
                <Lock className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
              </div>
              <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                Locked Accounts
              </span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {stats?.locked_accounts?.toLocaleString() ?? '0'}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export default UserStatsCards
