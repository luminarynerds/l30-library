/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import {
  searchUsers,
  deleteUser,
  lockUser,
  unlockUser,
  getUserStats,
  exportUsersCSV,
  sendPasswordReset,
  resendStaffInvite,
  revokeStaffInvite,
  type AdminUser,
  type UserStats,
  type UserSearchFilters,
} from '../../api/staff-api'
import toast from 'react-hot-toast'
import { getStoredPageSize } from './constants'

export interface DeleteConfirm {
  userId: number
  userName: string
}

export interface LockConfirm {
  userId: number
  userName: string
  isLocking: boolean
}

export interface PasswordResetConfirm {
  userId: number
  userName: string
  userEmail: string
}

export interface RevokeConfirm {
  userId: number
  userName: string
}

export function useUsersAdmin() {
  const { token } = useAuth()

  // Users tab state
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter] = useState('')
  const [statusFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)
  const [pageSize] = useState<number>(getStoredPageSize)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirm | null>(null)
  const [lockConfirm, setLockConfirm] = useState<LockConfirm | null>(null)
  const [passwordResetConfirm, setPasswordResetConfirm] = useState<PasswordResetConfirm | null>(null)
  const [revokeConfirm, setRevokeConfirm] = useState<RevokeConfirm | null>(null)

  // Bulk selection state (dead state, kept for export compatibility)
  const [selectedUserIds] = useState<Set<number>>(new Set())

  // Export state
  const [exportLoading, setExportLoading] = useState(false)

  // Sort state (dead state, kept for fetchUsers signature compatibility)
  const [sortField] = useState<'name' | 'email' | 'role' | 'created_at' | 'last_login' | null>(null)
  const [sortDirection] = useState<'asc' | 'desc'>('asc')

  // Stats state
  const [stats, setStats] = useState<UserStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // Fetch user stats
  const fetchStats = useCallback(async () => {
    if (!token) return
    try {
      setStatsLoading(true)
      const result = await getUserStats(token)
      setStats(result)
    } catch (_err) {
      // Silently fail for stats - not critical
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
    } finally {
      setStatsLoading(false)
    }
  }, [token])

  // Load stats on mount
  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  // Fetch users
  const fetchUsers = useCallback(
    async (
      page = 1,
      query = '',
      perPage = pageSize,
      sortBy: typeof sortField = sortField,
      sortOrder: typeof sortDirection = sortDirection,
      role: string = roleFilter,
      status: string = statusFilter
    ) => {
      if (!token) return

      try {
        setLoading(true)
        setError(null)
        const filters: UserSearchFilters = {
          ...(query && { search: query }),
          ...(role && { role }),
          ...(status && { status }),
          ...(sortBy && { sort_by: sortBy }),
          ...(sortBy && { sort_order: sortOrder }),
        }
        const result = await searchUsers(token, filters, page, perPage)
        setUsers(result.users)
        setTotalUsers(result.total)
        setCurrentPage(result.page)
      } catch (_err) {
        const message = _err instanceof Error ? _err.message : 'Failed to fetch users'
        setError(message)
        toast.error(message)
      } finally {
        setLoading(false)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, pageSize, sortField, sortDirection]
  )

  // Initial load
  useEffect(() => {
    fetchUsers(1, searchQuery)
  }, [fetchUsers, searchQuery])

  // Handle search with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUsers(1, searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, fetchUsers])

  // Handle pagination
  const handleNextPage = () => {
    if (currentPage * pageSize < totalUsers) {
      fetchUsers(currentPage + 1, searchQuery)
    }
  }

  const handlePrevPage = () => {
    if (currentPage > 1) {
      fetchUsers(currentPage - 1, searchQuery)
    }
  }

  // Handle user deletion
  const handleDeleteUser = async () => {
    if (!deleteConfirm || !token) return

    try {
      await deleteUser(token, deleteConfirm.userId)
      toast.success('User deleted successfully')
      setDeleteConfirm(null)
      fetchUsers(currentPage, searchQuery)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to delete user'
      toast.error(message)
    }
  }

  // Handle lock/unlock
  const handleLockToggle = async () => {
    if (!lockConfirm || !token) return

    try {
      const action = lockConfirm.isLocking ? lockUser : unlockUser
      await action(token, lockConfirm.userId)
      toast.success(
        lockConfirm.isLocking ? 'User account locked' : 'User account unlocked'
      )
      setLockConfirm(null)
      fetchUsers(currentPage, searchQuery)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to update user'
      toast.error(message)
    }
  }

  // Handle password reset
  const handlePasswordReset = async () => {
    if (!passwordResetConfirm || !token) return

    try {
      const result = await sendPasswordReset(token, passwordResetConfirm.userId)
      toast.success(result.message)
      setPasswordResetConfirm(null)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to send password reset'
      toast.error(message)
    }
  }

  // Handle resend invite
  const handleResendInvite = async (userId: number) => {
    if (!token) return
    try {
      await resendStaffInvite(userId)
      toast.success('Invitation resent')
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to resend invitation'
      toast.error(message)
    }
  }

  // Handle revoke invite
  const handleRevokeInvite = async () => {
    if (!revokeConfirm || !token) return
    try {
      await revokeStaffInvite(revokeConfirm.userId)
      toast.success('Invitation revoked')
      setRevokeConfirm(null)
      fetchUsers(currentPage, searchQuery)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to revoke invitation'
      toast.error(message)
    }
  }

  // Handle user creation success
  const handleUserAdded = () => {
    setShowAddModal(false)
    fetchUsers(1, searchQuery)
  }

  // Handle user edit success
  const handleUserUpdated = () => {
    setEditingUser(null)
    fetchUsers(currentPage, searchQuery)
  }

  // Handle CSV export
  const handleExport = async () => {
    if (!token) return

    try {
      setExportLoading(true)
      const options = {
        ...(searchQuery && { search: searchQuery }),
        ...(selectedUserIds.size > 0 && { userIds: Array.from(selectedUserIds) }),
      }
      await exportUsersCSV(token, options)
      toast.success(
        selectedUserIds.size > 0
          ? `Exported ${selectedUserIds.size} selected user(s)`
          : 'Users exported successfully'
      )
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to export users'
      toast.error(message)
    } finally {
      setExportLoading(false)
    }
  }

  const totalPages = Math.ceil(totalUsers / pageSize)
  const hasNextPage = currentPage < totalPages
  const hasPrevPage = currentPage > 1
  const startItem = totalUsers > 0 ? (currentPage - 1) * pageSize + 1 : 0
  const endItem = Math.min(currentPage * pageSize, totalUsers)

  return {
    // State
    users,
    loading,
    error,
    searchQuery,
    currentPage,
    totalUsers,
    pageSize,
    showAddModal,
    editingUser,
    deleteConfirm,
    lockConfirm,
    passwordResetConfirm,
    selectedUserIds,
    exportLoading,
    stats,
    statsLoading,
    // Pagination derived
    totalPages,
    hasNextPage,
    hasPrevPage,
    startItem,
    endItem,
    // Setters
    setSearchQuery,
    setShowAddModal,
    setEditingUser,
    setDeleteConfirm,
    setLockConfirm,
    setPasswordResetConfirm,
    setError,
    // Handlers
    fetchUsers,
    handleNextPage,
    handlePrevPage,
    handleDeleteUser,
    handleLockToggle,
    handlePasswordReset,
    handleResendInvite,
    handleRevokeInvite,
    handleUserAdded,
    handleUserUpdated,
    handleExport,
    // Revoke invite
    revokeConfirm,
    setRevokeConfirm,
  }
}
