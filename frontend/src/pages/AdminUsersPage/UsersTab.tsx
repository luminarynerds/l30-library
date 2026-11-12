/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  Search,
  Plus,
  Download,
  Loader2,
  AlertCircle,
  Mail,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import UserStatsCards from './UserStatsCards'
import UserTable from './UserTable'
import type { useUsersAdmin } from './useUsersAdmin'

type UsersAdminReturn = ReturnType<typeof useUsersAdmin>

interface UsersTabProps {
  usersAdmin: UsersAdminReturn
  onInviteStaff: () => void
}

const UsersTab: React.FC<UsersTabProps> = ({ usersAdmin, onInviteStaff }) => {
  const { t } = useTranslation()
  const {
    users,
    loading,
    error,
    searchQuery,
    currentPage,
    totalUsers,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    showAddModal: _showAddModal,
    selectedUserIds,
    exportLoading,
    stats,
    statsLoading,
    totalPages,
    hasNextPage,
    hasPrevPage,
    startItem,
    endItem,
    setSearchQuery,
    setShowAddModal,
    setEditingUser,
    setDeleteConfirm,
    setLockConfirm,
    setPasswordResetConfirm,
    setError,
    fetchUsers,
    handleNextPage,
    handlePrevPage,
    handleExport,
    handleResendInvite,
    setRevokeConfirm,
  } = usersAdmin

  return (
    <>
      {/* Stats Dashboard */}
      <UserStatsCards stats={stats} statsLoading={statsLoading} />

      {/* Top Controls */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('admin.adminUsers.searchByEmailOrName')}
            aria-label={t('admin.adminUsers.searchByEmailOrName2')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        {/* Export Button */}
        <button
          onClick={handleExport}
          disabled={exportLoading}
          className="flex items-center gap-2 px-6 py-3 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-semibold rounded-xl transition-colors duration-200 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          title={selectedUserIds.size > 0 ? `Export ${selectedUserIds.size} selected user(s)` : 'Export all users matching current filters'}
        >
          {exportLoading ? (
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
          ) : (
            <Download className="w-5 h-5" />
          )}
          <span className="hidden sm:inline">
            {exportLoading
              ? 'Exporting...'
              : selectedUserIds.size > 0
                ? `Export (${selectedUserIds.size})`
                : 'Export'}
          </span>
        </button>

        {/* Invite Staff Button */}
        <button
          onClick={onInviteStaff}
          className="flex items-center gap-2 px-6 py-3 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream font-semibold rounded-xl transition-colors duration-200 whitespace-nowrap"
        >
          <Mail className="w-5 h-5" />
          <span className="hidden sm:inline">Invite Staff</span>
        </button>

        {/* Add User Button */}
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors duration-200 whitespace-nowrap"
        >
          <Plus className="w-5 h-5" />
          <span className="hidden sm:inline">Add User</span>
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-8 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-status-danger-800 dark:text-status-danger-300 font-medium">Error</p>
            <p className="text-status-danger-700 dark:text-status-danger-400 text-sm">{error}</p>
          </div>
          <button
            onClick={() => {
              setError(null)
              fetchUsers(currentPage, searchQuery)
            }}
            className="text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 font-medium text-sm whitespace-nowrap"
          >
            Retry
          </button>
        </div>
      )}

      {/* User Table */}
      <UserTable
        users={users}
        loading={loading}
        searchQuery={searchQuery}
        currentPage={currentPage}
        totalPages={totalPages}
        hasNextPage={hasNextPage}
        hasPrevPage={hasPrevPage}
        startItem={startItem}
        endItem={endItem}
        totalUsers={totalUsers}
        onEdit={(user) => setEditingUser(user)}
        onDelete={(userId, userName) => setDeleteConfirm({ userId, userName })}
        onLock={(userId, userName, isLocking) => setLockConfirm({ userId, userName, isLocking })}
        onPasswordReset={(userId, userName, userEmail) => setPasswordResetConfirm({ userId, userName, userEmail })}
        onNextPage={handleNextPage}
        onPrevPage={handlePrevPage}
        onClearSearch={() => setSearchQuery('')}
        onAddUser={() => setShowAddModal(true)}
        onResendInvite={handleResendInvite}
        onRevokeInvite={(userId, userName) => setRevokeConfirm({ userId, userName })}
      />
    </>
  )
}

export default UsersTab
