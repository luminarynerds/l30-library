/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  Edit,
  Trash2,
  Lock,
  Unlock,
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Users,
  UserX,
  Plus,
  KeyRound,
  MailCheck,
  MailX,
} from 'lucide-react'
import type { AdminUser } from '../../api/staff-api'
import RoleBadge from './RoleBadge'
import UserAvatar from './UserAvatar'
import { t } from '@/i18n'

interface UserTableProps {
  users: AdminUser[]
  loading: boolean
  searchQuery: string
  // Pagination
  currentPage: number
  totalPages: number
  hasNextPage: boolean
  hasPrevPage: boolean
  startItem: number
  endItem: number
  totalUsers: number
  // Callbacks
  onEdit: (user: AdminUser) => void
  onDelete: (userId: number, userName: string) => void
  onLock: (userId: number, userName: string, isLocking: boolean) => void
  onPasswordReset: (userId: number, userName: string, userEmail: string) => void
  onNextPage: () => void
  onPrevPage: () => void
  onClearSearch: () => void
  onAddUser: () => void
  onResendInvite: (userId: number) => void
  onRevokeInvite: (userId: number, userName: string) => void
}

const UserTable: React.FC<UserTableProps> = ({
  users,
  loading,
  searchQuery,
  currentPage,
  totalPages,
  hasNextPage,
  hasPrevPage,
  startItem,
  endItem,
  totalUsers,
  onEdit,
  onDelete,
  onLock,
  onPasswordReset,
  onNextPage,
  onPrevPage,
  onClearSearch,
  onAddUser,
  onResendInvite,
  onRevokeInvite,
}) => {
  // Loading State
  if (loading) {
    return (
      <div role="status" aria-live="polite" className="flex justify-center items-center py-16">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-lsc-rose motion-safe:animate-spin mx-auto mb-4" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Loading users...
          </p>
        </div>
      </div>
    )
  }

  // Empty State
  if (users.length === 0) {
    return (
      <div className="text-center py-20 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
        <div className="relative inline-block mb-6">
          <div className="w-24 h-24 bg-lsc-cream dark:bg-earth-700 rounded-full flex items-center justify-center">
            {searchQuery ? (
              <UserX className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70" />
            ) : (
              <Users className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70" />
            )}
          </div>
          {searchQuery && (
            <div className="absolute -bottom-1 -right-1 w-8 h-8 bg-status-warning-100 dark:bg-status-warning-900/50 rounded-full flex items-center justify-center">
              <Search className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400" />
            </div>
          )}
        </div>
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          {searchQuery ? 'No matching users found' : 'No users yet'}
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-md mx-auto">
          {searchQuery
            ? `We could not find any users matching "${searchQuery}". Try adjusting your search terms or clearing the filter.`
            : 'Get started by adding your first user to the system. Users can be patrons, staff members, or administrators.'}
        </p>
        {searchQuery ? (
          <button
            onClick={onClearSearch}
            className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors duration-200"
          >
            <Search className="w-5 h-5" />
            Clear search
          </button>
        ) : (
          <button
            onClick={onAddUser}
            className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors duration-200"
          >
            <Plus className="w-5 h-5" />
            Add first user
          </button>
        )}
      </div>
    )
  }

  return (
    <>
      {/* Table Container */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden shadow-sm">
        {/* Desktop Table */}
        <div className="hidden md:block overflow-x-auto overflow-y-auto max-h-[calc(100vh-200px)]">
          <table className="w-full" aria-label={t('aria.userTable.userAccountsManagement')}>
            <thead className="sticky top-0 z-10">
              <tr className="bg-lsc-cream/95 dark:bg-earth-700/95 backdrop-blur-sm border-b border-lsc-border dark:border-earth-700 shadow-sm">
                <th scope="col" className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  User
                </th>
                <th scope="col" className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Role
                </th>
                <th scope="col" className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Status
                </th>
                <th scope="col" className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Created
                </th>
                <th scope="col" className="px-6 py-4 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user, idx) => (
                <tr
                  key={user.id}
                  className={`border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50 transition-colors ${
                    idx % 2 === 0
                      ? 'bg-lsc-white dark:bg-earth-800'
                      : 'bg-lsc-cream/20 dark:bg-earth-700/30'
                  }`}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <UserAvatar user={user} />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={user.first_name || user.last_name ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : user.email}>
                          {user.first_name || user.last_name
                            ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                            : user.email}
                        </p>
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={user.email}>
                          {user.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <RoleBadge role={user.role} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        aria-hidden="true"
                        className={`w-2 h-2 rounded-full ${
                          user.is_active
                            ? 'bg-status-success-500'
                            : 'bg-status-danger-500'
                        }`}
                      />
                      <span
                        className={`${
                          user.is_active
                            ? 'text-status-success-700 dark:text-status-success-400'
                            : 'text-status-danger-700 dark:text-status-danger-400'
                        }`}
                      >
                        {user.is_active
                          ? 'Active'
                          : 'Inactive'}
                      </span>
                      {!user.is_active && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 border border-status-warning-300 dark:border-status-warning-700">
                          Pending invite
                        </span>
                      )}
                      {user.is_locked && (
                        <span className="text-status-warning-700 dark:text-status-warning-400 text-xs">
                          (Locked)
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      {!user.is_active && (
                        <>
                          <button
                            onClick={() => onResendInvite(user.id)}
                            className="p-2 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 rounded-lg transition-colors text-status-success-600 dark:text-status-success-400"
                            aria-label={`Resend invitation to ${user.email}`}
                            title="Resend invitation"
                          >
                            <MailCheck className="w-5 h-5" aria-hidden="true" />
                          </button>
                          <button
                            onClick={() => onRevokeInvite(user.id, `${user.first_name} ${user.last_name}`.trim() || user.email)}
                            className="p-2 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors text-status-danger-600 dark:text-status-danger-400"
                            aria-label={`Revoke invitation for ${user.email}`}
                            title="Revoke invitation"
                          >
                            <MailX className="w-5 h-5" aria-hidden="true" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => onEdit(user)}
                        className="p-2 hover:bg-lsc-rose/20 rounded-lg transition-colors text-lsc-rose"
                        aria-label={`Edit user ${user.first_name || ''} ${user.last_name || user.email}`.trim()}
                      >
                        <Edit className="w-5 h-5" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() =>
                          onLock(
                            user.id,
                            `${user.first_name} ${user.last_name}`.trim() || user.email,
                            !user.is_locked,
                          )
                        }
                        className={`p-2 rounded-lg transition-colors ${
                          user.is_locked
                            ? 'hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 text-status-success-600 dark:text-status-success-400'
                            : 'hover:bg-status-warning-100 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-400'
                        }`}
                        aria-label={
                          user.is_locked ? `Unlock account for ${user.email}` : `Lock account for ${user.email}`
                        }
                      >
                        {user.is_locked ? (
                          <Unlock className="w-5 h-5" aria-hidden="true" />
                        ) : (
                          <Lock className="w-5 h-5" aria-hidden="true" />
                        )}
                      </button>
                      <button
                        onClick={() =>
                          onPasswordReset(
                            user.id,
                            `${user.first_name} ${user.last_name}`.trim() || user.email,
                            user.email,
                          )
                        }
                        disabled={user.is_locked}
                        className={`p-2 rounded-lg transition-colors ${
                          user.is_locked
                            ? 'opacity-50 cursor-not-allowed text-lsc-dark/70 dark:text-lsc-cream/70'
                            : 'hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
                        }`}
                        aria-label={
                          user.is_locked
                            ? `Cannot send password reset to locked account ${user.email}`
                            : `Send password reset for ${user.email}`
                        }
                        aria-disabled={user.is_locked}
                      >
                        <KeyRound className="w-5 h-5" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() =>
                          onDelete(
                            user.id,
                            `${user.first_name} ${user.last_name}`.trim() || user.email,
                          )
                        }
                        className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors text-status-danger-600 dark:text-status-danger-400"
                        aria-label={`Delete user ${user.first_name || ''} ${user.last_name || user.email}`.trim()}
                      >
                        <Trash2 className="w-5 h-5" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards */}
        <div className="md:hidden divide-y divide-earth-200 dark:divide-earth-700">
          {users.map((user) => (
            <div
              key={user.id}
              className="p-4 space-y-3 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50 transition-colors"
            >
              <div className="flex items-start gap-3">
                <UserAvatar user={user} size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={user.first_name || user.last_name ? `${user.first_name || ''} ${user.last_name || ''}`.trim() : user.email}>
                        {user.first_name || user.last_name
                          ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                          : user.email}
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={user.email}>
                        {user.email}
                      </p>
                    </div>
                    <RoleBadge role={user.role} />
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center gap-2">
                  <div
                    aria-hidden="true"
                    className={`w-2 h-2 rounded-full ${
                      user.is_active ? 'bg-status-success-500' : 'bg-status-danger-500'
                    }`}
                  />
                  <span
                    className={`${
                      user.is_active
                        ? 'text-status-success-700 dark:text-status-success-400'
                        : 'text-status-danger-700 dark:text-status-danger-400'
                    }`}
                  >
                    {user.is_active ? 'Active' : 'Inactive'}
                    {user.is_locked && ' (Locked)'}
                  </span>
                  {!user.is_active && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 border border-status-warning-300 dark:border-status-warning-700">
                      Pending invite
                    </span>
                  )}
                </div>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  {new Date(user.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="flex flex-wrap gap-2 pt-2 border-t border-lsc-border dark:border-earth-700">
                {!user.is_active && (
                  <>
                    <button
                      onClick={() => onResendInvite(user.id)}
                      className="flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 rounded-lg transition-colors text-status-success-600 dark:text-status-success-400 text-sm font-medium flex items-center justify-center gap-2"
                    >
                      <MailCheck className="w-4 h-4" />
                      Resend
                    </button>
                    <button
                      onClick={() => onRevokeInvite(user.id, `${user.first_name} ${user.last_name}`.trim() || user.email)}
                      className="flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors text-status-danger-600 dark:text-status-danger-400 text-sm font-medium flex items-center justify-center gap-2"
                    >
                      <MailX className="w-4 h-4" />
                      Revoke
                    </button>
                  </>
                )}
                <button
                  onClick={() => onEdit(user)}
                  className="flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 hover:bg-lsc-rose/20 rounded-lg transition-colors text-lsc-rose text-sm font-medium flex items-center justify-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  Edit
                </button>
                <button
                  onClick={() =>
                    onLock(
                      user.id,
                      `${user.first_name} ${user.last_name}`.trim() || user.email,
                      !user.is_locked,
                    )
                  }
                  className={`flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2 ${
                    user.is_locked
                      ? 'hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 text-status-success-600 dark:text-status-success-400'
                      : 'hover:bg-status-warning-100 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/30 text-status-warning-600 dark:text-status-warning-400'
                  }`}
                >
                  {user.is_locked ? (
                    <>
                      <Unlock className="w-4 h-4" />
                      Unlock
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4" />
                      Lock
                    </>
                  )}
                </button>
                <button
                  onClick={() =>
                    onPasswordReset(
                      user.id,
                      `${user.first_name} ${user.last_name}`.trim() || user.email,
                      user.email,
                    )
                  }
                  disabled={user.is_locked}
                  className={`flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 rounded-lg transition-colors text-sm font-medium flex items-center justify-center gap-2 ${
                    user.is_locked
                      ? 'opacity-50 cursor-not-allowed text-lsc-dark/70 dark:text-lsc-cream/70'
                      : 'hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
                  }`}
                  title={
                    user.is_locked
                      ? 'Cannot send password reset to locked account'
                      : 'Send password reset'
                  }
                >
                  <KeyRound className="w-4 h-4" />
                  Reset
                </button>
                <button
                  onClick={() =>
                    onDelete(
                      user.id,
                      `${user.first_name} ${user.last_name}`.trim() || user.email,
                    )
                  }
                  className="flex-1 min-w-[calc(50%-0.25rem)] px-3 py-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors text-status-danger-600 dark:text-status-danger-400 text-sm font-medium flex items-center justify-center gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pagination */}
      <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Showing {startItem} to {endItem} of {totalUsers} users
        </p>

        <div className="flex gap-2">
          <button
            onClick={onPrevPage}
            disabled={!hasPrevPage}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            <span className="hidden sm:inline">Previous</span>
          </button>

          <div className="flex items-center gap-2 px-4">
            <span className="text-sm text-lsc-dark dark:text-lsc-cream font-medium">
              Page {currentPage} of {totalPages}
            </span>
          </div>

          <button
            onClick={onNextPage}
            disabled={!hasNextPage}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </>
  )
}

export default UserTable
