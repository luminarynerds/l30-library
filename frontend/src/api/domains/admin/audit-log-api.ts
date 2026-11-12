/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Audit Log API Service
 *
 * Provides functions for viewing privacy audit logs.
 * All endpoints require STAFF, ADMIN, or SUPER_ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export interface PrivacyAuditLog {
  id: number
  user_id: number
  user_email: string | null
  action: string
  resource_type: string | null
  resource_id: number | null
  old_privacy: string | null
  new_privacy: string | null
  ip_address: string | null
  created_at: string
  reverted_from_log_id?: number | null
}

export interface CanRevertResponse {
  can_revert: boolean
  reason?: string
}

export interface RevertResponse {
  success: boolean
  message: string
  new_audit_log_id?: number
}

export interface PrivacyAuditLogsResponse {
  total: number
  page: number
  page_size: number
  total_pages: number
  logs: PrivacyAuditLog[]
}

export interface StaffAuditLog {
  id: number
  admin_id: number | null
  admin_email: string | null
  action: string
  target_user_id: number | null
  target_user_email: string | null
  ip_address: string | null
  resource_type?: string | null
  resource_id?: number | null
  old_privacy?: string | null
  new_privacy?: string | null
  user_agent?: string | null
  created_at: string
}

export interface StaffAuditLogsResponse {
  total: number
  page: number
  page_size: number
  total_pages: number
  logs: StaffAuditLog[]
}

export interface AuditLogFilters {
  user_id?: number
  user_email?: string
  resource_type?: string
  action?: string
  days_back?: number
  page?: number
  page_size?: number
}

export interface StaffAuditLogFilters {
  admin_id?: number
  admin_email?: string
  action?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

// ==================== API Functions ====================

export async function getPrivacyAuditLogs(
  token: string,
  filters?: AuditLogFilters
): Promise<PrivacyAuditLogsResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.user_id) params.set('user_id', filters.user_id.toString())
    if (filters?.user_email) params.set('user_email', filters.user_email)
    if (filters?.resource_type) params.set('resource_type', filters.resource_type)
    if (filters?.action) params.set('action', filters.action)
    if (filters?.days_back) params.set('days_back', filters.days_back.toString())
    if (filters?.page) params.set('page', filters.page.toString())
    if (filters?.page_size) params.set('page_size', filters.page_size.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PrivacyAuditLogsResponse>(
      `/admin/audit/privacy-changes${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch audit logs')
    }
    throw error
  }
}

export async function getStaffAuditLogs(
  token: string,
  filters?: StaffAuditLogFilters
): Promise<StaffAuditLogsResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.admin_id) params.set('admin_id', filters.admin_id.toString())
    if (filters?.admin_email) params.set('admin_email', filters.admin_email)
    if (filters?.action) params.set('action', filters.action)
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    if (filters?.page) params.set('page', filters.page.toString())
    if (filters?.page_size) params.set('page_size', filters.page_size.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<StaffAuditLogsResponse>(
      `/admin/audit/staff-activity${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff audit logs')
    }
    throw error
  }
}

export async function getUserPrivacyChanges(
  token: string,
  userId: number,
  options?: {
    days_back?: number
    page?: number
    page_size?: number
  }
): Promise<PrivacyAuditLogsResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.days_back) params.set('days_back', options.days_back.toString())
    if (options?.page) params.set('page', options.page.toString())
    if (options?.page_size) params.set('page_size', options.page_size.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PrivacyAuditLogsResponse>(
      `/admin/audit/privacy-changes/user/${userId}${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch user privacy changes')
    }
    throw error
  }
}

export async function getPrivacyChangesByType(
  token: string,
  resourceType: string,
  options?: {
    days_back?: number
    page?: number
    page_size?: number
  }
): Promise<PrivacyAuditLogsResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.days_back) params.set('days_back', options.days_back.toString())
    if (options?.page) params.set('page', options.page.toString())
    if (options?.page_size) params.set('page_size', options.page_size.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PrivacyAuditLogsResponse>(
      `/admin/audit/privacy-changes/by-type/${encodeURIComponent(resourceType)}${queryString}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch privacy changes by type')
    }
    throw error
  }
}

export async function checkCanRevert(
  token: string,
  auditLogId: number
): Promise<CanRevertResponse> {
  try {
    return await fetchApi<CanRevertResponse>(
      `/admin/audit/privacy-changes/${auditLogId}/can-revert`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check revert status')
    }
    throw error
  }
}

export async function revertAuditAction(
  token: string,
  auditLogId: number
): Promise<RevertResponse> {
  try {
    return await fetchApi<RevertResponse>(
      `/admin/audit/privacy-changes/${auditLogId}/revert`,
      { token, method: 'POST' }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to revert action')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getActionLabel(action: string): string {
  const labels: Record<string, string> = {
    PRIVACY_CHANGE_READING_LIST: 'Reading List Privacy Change',
    PRIVACY_CHANGE_STRAIN_LIST: 'Strain List Privacy Change',
    PRIVACY_CHANGE_FAVORITES: 'Favorites Privacy Change',
    PRIVACY_CHANGE_GENERIC: 'Privacy Change',
  }
  return labels[action] || action.replace(/_/g, ' ').toLowerCase()
}

export function getStaffActionLabel(action: string): string {
  const labels: Record<string, string> = {
    CREATE_USER: 'Created user',
    UPDATE_USER: 'Updated user',
    DELETE_USER: 'Deleted user',
    LOCK_USER: 'Locked user',
    UNLOCK_USER: 'Unlocked user',
    ACTIVATE_USER: 'Activated user',
    DEACTIVATE_USER: 'Deactivated user',
    RESET_PASSWORD: 'Reset user password',
    CHANGE_ROLE: 'Changed user role',
    BULK_LOCK: 'Bulk lock',
    BULK_UNLOCK: 'Bulk unlock',
    BULK_ACTIVATE: 'Bulk activate',
    BULK_DEACTIVATE: 'Bulk deactivate',
    BULK_DELETE: 'Bulk delete',
    GDPR_DELETION_REQUESTED: 'GDPR deletion requested',
    GDPR_DELETION_CANCELLED: 'GDPR deletion cancelled',
    GDPR_DELETION_COMPLETED: 'GDPR deletion completed',
    GDPR_DATA_EXPORTED: 'GDPR data exported',
    STAFF_INITIATED_DELETION: 'Staff-initiated deletion',
    CHILD_TO_ADULT_TRANSITION: 'Child to adult transition',
    PATRON_MERGE: 'Patron merge',
    REVERT_USER_UPDATE: 'Reverted user update',
    REVERT_LOCK_USER: 'Reverted lock',
    REVERT_UNLOCK_USER: 'Reverted unlock',
    REVERT_PRIVACY_CHANGE: 'Reverted privacy change',
    REVERT_PATRON_MERGE: 'Reverted patron merge',
    PRIVACY_CHANGE_READING_LIST: 'Reading list privacy change',
    PRIVACY_CHANGE_STRAIN_LIST: 'Strain list privacy change',
    PRIVACY_CHANGE_FAVORITES: 'Favorites privacy change',
    PRIVACY_CHANGE_GENERIC: 'Privacy change',
  }
  return labels[action] || action.replace(/_/g, ' ').toLowerCase()
}

export function getResourceTypeLabel(resourceType: string | null): string {
  if (!resourceType) return 'Unknown'
  const labels: Record<string, string> = {
    reading_list: 'Reading List',
    strain_list: 'Strain List',
    favorites: 'Favorites',
  }
  return labels[resourceType] || resourceType.replace(/_/g, ' ')
}

export function getPrivacyLabel(privacy: string | null): string {
  if (!privacy) return 'Unknown'
  const labels: Record<string, string> = {
    private: 'Private',
    public: 'Public',
    friends: 'Friends Only',
  }
  return labels[privacy] || privacy
}

/**
 * Available resource types for filtering
 */
export const RESOURCE_TYPES = [
  { value: 'reading_list', label: 'Reading Lists' },
  { value: 'strain_list', label: 'Strain Lists' },
  { value: 'favorites', label: 'Favorites' },
]

/**
 * Available audit actions for filtering
 */
export const AUDIT_ACTIONS = [
  { value: 'PRIVACY_CHANGE_READING_LIST', label: 'Reading List Privacy' },
  { value: 'PRIVACY_CHANGE_STRAIN_LIST', label: 'Strain List Privacy' },
  { value: 'PRIVACY_CHANGE_FAVORITES', label: 'Favorites Privacy' },
  { value: 'PRIVACY_CHANGE_GENERIC', label: 'Generic Privacy' },
]

/**
 * Staff audit actions for filtering
 */
export const STAFF_AUDIT_ACTIONS = [
  { value: 'CREATE_USER', label: 'Create user' },
  { value: 'UPDATE_USER', label: 'Update user' },
  { value: 'DELETE_USER', label: 'Delete user' },
  { value: 'LOCK_USER', label: 'Lock user' },
  { value: 'UNLOCK_USER', label: 'Unlock user' },
  { value: 'ACTIVATE_USER', label: 'Activate user' },
  { value: 'DEACTIVATE_USER', label: 'Deactivate user' },
  { value: 'RESET_PASSWORD', label: 'Reset password' },
  { value: 'CHANGE_ROLE', label: 'Change role' },
  { value: 'BULK_LOCK', label: 'Bulk lock' },
  { value: 'BULK_UNLOCK', label: 'Bulk unlock' },
  { value: 'BULK_ACTIVATE', label: 'Bulk activate' },
  { value: 'BULK_DEACTIVATE', label: 'Bulk deactivate' },
  { value: 'BULK_DELETE', label: 'Bulk delete' },
  { value: 'GDPR_DELETION_REQUESTED', label: 'GDPR deletion requested' },
  { value: 'GDPR_DELETION_CANCELLED', label: 'GDPR deletion cancelled' },
  { value: 'GDPR_DELETION_COMPLETED', label: 'GDPR deletion completed' },
  { value: 'GDPR_DATA_EXPORTED', label: 'GDPR data exported' },
  { value: 'STAFF_INITIATED_DELETION', label: 'Staff-initiated deletion' },
  { value: 'CHILD_TO_ADULT_TRANSITION', label: 'Child to adult transition' },
  { value: 'PATRON_MERGE', label: 'Patron merge' },
  { value: 'REVERT_USER_UPDATE', label: 'Revert user update' },
  { value: 'REVERT_LOCK_USER', label: 'Revert lock user' },
  { value: 'REVERT_UNLOCK_USER', label: 'Revert unlock user' },
  { value: 'REVERT_PRIVACY_CHANGE', label: 'Revert privacy change' },
  { value: 'REVERT_PATRON_MERGE', label: 'Revert patron merge' },
  { value: 'PRIVACY_CHANGE_READING_LIST', label: 'Reading list privacy change' },
  { value: 'PRIVACY_CHANGE_STRAIN_LIST', label: 'Strain list privacy change' },
  { value: 'PRIVACY_CHANGE_FAVORITES', label: 'Favorites privacy change' },
  { value: 'PRIVACY_CHANGE_GENERIC', label: 'Generic privacy change' },
]
