/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { buildQueryString, extractErrorMessage } from '@/lib/api-helpers'

// ==================== User Management Types ====================

export interface AdminUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role: 'super_admin' | 'admin' | 'staff' | 'teacher' | 'patron' | 'child' | 'bookmobile' | 'homebond'
  is_active: boolean
  is_locked: boolean
  created_at: string
  updated_at?: string | null
  // Contact info
  phone?: string | null
  address?: string | null
  // Library info
  library_card?: string | null
  // Account security
  failed_login_attempts: number
  locked_until?: string | null
  // Login tracking
  last_login?: string | null
  // Email verification
  email_verified: boolean
  // Teacher card linkage (set via PATCH /staff/patrons/{id}/teacher-card)
  school_id?: number | null
}

export interface UserSearchResult {
  users: AdminUser[]
  total: number
  page: number
  per_page: number
}

export interface CreateUserData {
  email: string
  password: string
  first_name?: string
  last_name?: string
  role: string
}

export interface UpdateUserData {
  email?: string
  first_name?: string
  last_name?: string
  role?: string
  is_active?: boolean
}

export interface UserSearchFilters {
  search?: string
  role?: string
  status?: string
  sort_by?: 'name' | 'email' | 'role' | 'created_at' | 'last_login'
  sort_order?: 'asc' | 'desc'
}

export interface UserStats {
  total_users: number
  active_users: number
  new_this_month: number
  locked_accounts: number
}

// ==================== Bulk User Action Types ====================

export interface BulkActionResponse {
  success: boolean
  processed: number
  skipped: number
  message: string
}

// ==================== User Export Types ====================

export interface ExportUsersOptions {
  search?: string
  role?: string
  status?: string
  userIds?: number[]
}

// ==================== Staff Management Types ====================

export interface StaffMember {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
  department?: string
  hire_date?: string
  phone?: string
  address?: string
  is_active: boolean
  permissions?: string[]
}

export interface StaffListResult {
  staff: StaffMember[]
  total: number
  page: number
  per_page: number
}

export interface Role {
  id: string
  name: string
  description?: string
  permissions: string[]  // Array of permission codes
}

export interface Permission {
  id: number
  code: string
  name: string
  description?: string | null
  category: string
}

export interface RolePermission {
  role_id: string
  permission_id: number
}

// Permission templates for common role configurations
export interface PermissionTemplate {
  id: string
  name: string
  description: string
  permissionCodes: string[]
}

// Pre-defined permission templates
export const PERMISSION_TEMPLATES: PermissionTemplate[] = [
  {
    id: 'full_circulation',
    name: 'Full Circulation Access',
    description: 'All checkout, return, hold, and renewal operations',
    permissionCodes: ['circulation.checkout', 'circulation.return', 'circulation.hold', 'circulation.renew', 'circulation.view'],
  },
  {
    id: 'catalog_management',
    name: 'Catalog Management',
    description: 'Add, edit, and manage catalog items',
    permissionCodes: ['catalog.view', 'catalog.create', 'catalog.update', 'catalog.delete'],
  },
  {
    id: 'patron_management',
    name: 'Patron Management',
    description: 'View and manage patron accounts',
    permissionCodes: ['patron.view', 'patron.create', 'patron.update', 'patron.block'],
  },
  {
    id: 'reports_readonly',
    name: 'Reports (Read Only)',
    description: 'View reports and analytics',
    permissionCodes: ['reports.view', 'analytics.view'],
  },
  {
    id: 'staff_basic',
    name: 'Basic Staff Access',
    description: 'Standard staff operations for daily work',
    permissionCodes: ['circulation.checkout', 'circulation.return', 'circulation.view', 'patron.view', 'catalog.view'],
  },
]

export interface ScheduleEntry {
  id: number
  staff_id: number
  date: string
  start_time: string
  end_time: string
  status: 'scheduled' | 'confirmed' | 'absent' | 'vacation'
}

export interface PerformanceMetric {
  id: number
  staff_id: number
  metric_name: string
  value: number | string
  date: string
  notes?: string
}

export interface PerformanceEvaluation {
  id: number
  staff_id: number
  evaluator_id: number
  rating: number
  feedback: string
  eval_date: string
  categories: {
    communication: number
    teamwork: number
    reliability: number
    customer_service: number
    technical_skills: number
  }
}

export interface Training {
  id: number
  staff_id: number
  training_name: string
  provider?: string
  completion_date?: string
  expiry_date?: string
  status: 'pending' | 'in_progress' | 'completed' | 'expired'
  certification_number?: string
}

export interface TrainingCompletionResult {
  trainings: Training[]
  total: number
  page: number
  per_page: number
}

export interface StaffPasswordResetResponse {
  message: string
  reset_link: string
}

// ==================== User Management Functions ====================

export async function getUserStats(token: string): Promise<UserStats> {
  try {
    return await fetchApi<UserStats>('/users/stats', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch user stats')
    }
    throw error
  }
}

export async function searchUsers(
  token: string,
  filters?: UserSearchFilters,
  page = 1,
  perPage = 20
): Promise<UserSearchResult> {
  try {
    const query = buildQueryString({
      search: filters?.search,
      role: filters?.role,
      status: filters?.status,
      sort_by: filters?.sort_by,
      sort_order: filters?.sort_order,
      page,
      limit: perPage,
    })
    return await fetchApi<UserSearchResult>(`/users${query}`, { token })
  } catch (error: unknown) {
    throw new Error(extractErrorMessage(error, 'Failed to fetch users'))
  }
}

export async function getUser(token: string, userId: number): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>(`/users/${userId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch user')
    }
    throw error
  }
}

export async function createUser(token: string, data: CreateUserData): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>('/users', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create user')
    }
    throw error
  }
}

export async function updateUser(token: string, userId: number, data: UpdateUserData): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>(`/users/${userId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update user')
    }
    throw error
  }
}

export async function deleteUser(token: string, userId: number): Promise<void> {
  try {
    await fetchApi<void>(`/users/${userId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete user')
    }
    throw error
  }
}

export async function lockUser(token: string, userId: number): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>(`/users/${userId}/lock`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to lock user')
    }
    throw error
  }
}

export async function unlockUser(token: string, userId: number): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>(`/users/${userId}/unlock`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to unlock user')
    }
    throw error
  }
}

export async function sendPasswordReset(token: string, userId: number): Promise<StaffPasswordResetResponse> {
  try {
    return await fetchApi<StaffPasswordResetResponse>(`/users/${userId}/reset-password`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send password reset')
    }
    throw error
  }
}

// ==================== Bulk User Actions ====================

export async function bulkLockUsers(token: string, userIds: number[]): Promise<BulkActionResponse> {
  try {
    return await fetchApi<BulkActionResponse>('/users/bulk-lock', {
      method: 'POST',
      token,
      body: { user_ids: userIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to lock users')
    }
    throw error
  }
}

export async function bulkUnlockUsers(token: string, userIds: number[]): Promise<BulkActionResponse> {
  try {
    return await fetchApi<BulkActionResponse>('/users/bulk-unlock', {
      method: 'POST',
      token,
      body: { user_ids: userIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to unlock users')
    }
    throw error
  }
}

export async function bulkActivateUsers(token: string, userIds: number[]): Promise<BulkActionResponse> {
  try {
    return await fetchApi<BulkActionResponse>('/users/bulk-activate', {
      method: 'POST',
      token,
      body: { user_ids: userIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to activate users')
    }
    throw error
  }
}

export async function bulkDeactivateUsers(token: string, userIds: number[]): Promise<BulkActionResponse> {
  try {
    return await fetchApi<BulkActionResponse>('/users/bulk-deactivate', {
      method: 'POST',
      token,
      body: { user_ids: userIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to deactivate users')
    }
    throw error
  }
}

export async function bulkDeleteUsers(token: string, userIds: number[]): Promise<BulkActionResponse> {
  try {
    return await fetchApi<BulkActionResponse>('/users/bulk-delete', {
      method: 'POST',
      token,
      body: { user_ids: userIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete users')
    }
    throw error
  }
}

// ==================== User Export Functions ====================

export async function exportUsersCSV(
  token: string,
  options: ExportUsersOptions = {}
): Promise<void> {
  const { API_BASE } = await import('../types')

  const query = buildQueryString({
    search: options.search,
    role: options.role,
    status: options.status,
    user_ids: options.userIds?.length ? options.userIds.join(',') : undefined,
  })

  const url = `${API_BASE}/users/export${query}`

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    credentials: 'include',
  })

  if (!response.ok) {
    let errorMessage = 'Failed to export users'
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorMessage
    } catch {
      // Ignore JSON parse errors
    }
    throw new Error(errorMessage)
  }

  // Get the filename from Content-Disposition header or generate one
  const contentDisposition = response.headers.get('Content-Disposition')
  let filename = `users-export-${new Date().toISOString().split('T')[0]}.csv`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  // Get the CSV content as blob
  const blob = await response.blob()

  // Create a download link and trigger the download
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

// ==================== Staff Management Functions ====================

// Staff List & Management
export async function listStaff(token: string, page = 1, perPage = 20, filters?: { department?: string; role?: string; search?: string }): Promise<StaffListResult> {
  try {
    const params = new URLSearchParams()
    const offset = (page - 1) * perPage
    params.set('limit', perPage.toString())
    params.set('offset', offset.toString())
    if (filters?.department) params.set('department', filters.department)
    if (filters?.role) params.set('role', filters.role)
    if (filters?.search) params.set('search', filters.search)
    // The /users endpoint responds with { users: [...] }; map it onto the
    // StaffListResult contract. This previously read a non-existent `.staff`,
    // so every caller got undefined -> empty dropdown / "reading 'is_active'".
    const res = await fetchApi<{ users?: StaffMember[]; staff?: StaffMember[]; total: number; page?: number; limit?: number; per_page?: number }>(`/users?${params}`, { token })
    return {
      staff: res.users ?? res.staff ?? [],
      total: res.total ?? 0,
      page: res.page ?? page,
      per_page: res.per_page ?? res.limit ?? perPage,
    }
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff')
    }
    throw error
  }
}

export async function getStaffMember(token: string, staffId: number): Promise<StaffMember> {
  try {
    return await fetchApi<StaffMember>(`/users/${staffId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff member')
    }
    throw error
  }
}

export async function createStaffMember(token: string, data: Partial<StaffMember>): Promise<StaffMember> {
  try {
    return await fetchApi<StaffMember>('/users', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create staff member')
    }
    throw error
  }
}

export async function updateStaffMember(token: string, staffId: number, data: Partial<StaffMember>): Promise<StaffMember> {
  try {
    return await fetchApi<StaffMember>(`/users/${staffId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update staff member')
    }
    throw error
  }
}

export async function deleteStaffMember(token: string, staffId: number): Promise<void> {
  try {
    await fetchApi<void>(`/users/${staffId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete staff member')
    }
    throw error
  }
}

// Roles Management
export async function listRoles(token: string): Promise<Role[]> {
  try {
    return await fetchApi<Role[]>('/roles', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch roles')
    }
    throw error
  }
}

export async function getRole(token: string, roleId: string): Promise<Role> {
  try {
    return await fetchApi<Role>(`/roles/${roleId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch role')
    }
    throw error
  }
}

export async function createRole(token: string, data: Partial<Role>): Promise<Role> {
  try {
    return await fetchApi<Role>('/roles', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create role')
    }
    throw error
  }
}

export async function updateRole(token: string, roleId: string, data: Partial<Role>): Promise<Role> {
  try {
    return await fetchApi<Role>(`/roles/${roleId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update role')
    }
    throw error
  }
}

export async function deleteRole(token: string, roleId: string): Promise<void> {
  try {
    await fetchApi<void>(`/roles/${roleId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete role')
    }
    throw error
  }
}

// Permissions Management
export async function listPermissions(token: string): Promise<Permission[]> {
  try {
    return await fetchApi<Permission[]>('/permissions', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch permissions')
    }
    throw error
  }
}

export async function assignPermissionToRole(token: string, roleId: string, permissionId: number): Promise<Role> {
  try {
    return await fetchApi<Role>(`/roles/${roleId}/permissions/${permissionId}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to assign permission')
    }
    throw error
  }
}

export async function removePermissionFromRole(token: string, roleId: string, permissionId: number): Promise<Role> {
  try {
    return await fetchApi<Role>(`/roles/${roleId}/permissions/${permissionId}`, {
      method: 'DELETE',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove permission')
    }
    throw error
  }
}

// Bulk permission operations for templates
export async function applyPermissionTemplate(
  token: string,
  roleId: string,
  permissionCodes: string[],
  allPermissions: Permission[]
): Promise<Role> {
  // Map permission codes to IDs
  const permissionMap = new Map(allPermissions.map(p => [p.code, p.id]))

  // Get current role permissions
  const role = await getRole(token, roleId)
  const currentCodes = new Set(role.permissions)

  // Add missing permissions from template
  for (const code of permissionCodes) {
    if (!currentCodes.has(code)) {
      const permissionId = permissionMap.get(code)
      if (permissionId) {
        await assignPermissionToRole(token, roleId, permissionId)
      }
    }
  }

  // Return updated role
  return getRole(token, roleId)
}

// Schedule Management
export async function listSchedules(token: string, staffId?: number, page = 1, perPage = 20): Promise<{ schedules: ScheduleEntry[]; total: number; page: number; per_page: number }> {
  try {
    const params = new URLSearchParams()
    params.set('page', page.toString())
    params.set('per_page', perPage.toString())
    if (staffId) params.set('staff_id', staffId.toString())
    return await fetchApi<{ schedules: ScheduleEntry[]; total: number; page: number; per_page: number }>(`/staff/schedules?${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch schedules')
    }
    throw error
  }
}

export async function createSchedule(token: string, data: Partial<ScheduleEntry>): Promise<ScheduleEntry> {
  try {
    return await fetchApi<ScheduleEntry>('/staff/schedules', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create schedule')
    }
    throw error
  }
}

export async function updateSchedule(token: string, scheduleId: number, data: Partial<ScheduleEntry>): Promise<ScheduleEntry> {
  try {
    return await fetchApi<ScheduleEntry>(`/staff/schedules/${scheduleId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update schedule')
    }
    throw error
  }
}

export async function deleteSchedule(token: string, scheduleId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/schedules/${scheduleId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete schedule')
    }
    throw error
  }
}

// Performance Management
export async function listPerformanceMetrics(token: string, staffId: number, page = 1, perPage = 20): Promise<{ metrics: PerformanceMetric[]; total: number; page: number; per_page: number }> {
  try {
    const params = new URLSearchParams()
    params.set('page', page.toString())
    params.set('per_page', perPage.toString())
    return await fetchApi<{ metrics: PerformanceMetric[]; total: number; page: number; per_page: number }>(`/staff/${staffId}/performance/metrics?${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch performance metrics')
    }
    throw error
  }
}

export async function createPerformanceMetric(token: string, staffId: number, data: Partial<PerformanceMetric>): Promise<PerformanceMetric> {
  try {
    return await fetchApi<PerformanceMetric>(`/staff/${staffId}/performance/metrics`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create performance metric')
    }
    throw error
  }
}

export async function listEvaluations(token: string, staffId: number, page = 1, perPage = 20): Promise<{ evaluations: PerformanceEvaluation[]; total: number; page: number; per_page: number }> {
  try {
    const params = new URLSearchParams()
    params.set('page', page.toString())
    params.set('per_page', perPage.toString())
    return await fetchApi<{ evaluations: PerformanceEvaluation[]; total: number; page: number; per_page: number }>(`/staff/${staffId}/performance/evaluations?${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch evaluations')
    }
    throw error
  }
}

export async function createEvaluation(token: string, staffId: number, data: Partial<PerformanceEvaluation>): Promise<PerformanceEvaluation> {
  try {
    return await fetchApi<PerformanceEvaluation>(`/staff/${staffId}/performance/evaluations`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create evaluation')
    }
    throw error
  }
}

// Training Management
export async function listTrainings(token: string, staffId: number, page = 1, perPage = 20): Promise<TrainingCompletionResult> {
  try {
    const params = new URLSearchParams()
    params.set('page', page.toString())
    params.set('per_page', perPage.toString())
    return await fetchApi<TrainingCompletionResult>(`/staff/${staffId}/training?${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch training')
    }
    throw error
  }
}

export async function createTraining(token: string, staffId: number, data: Partial<Training>): Promise<Training> {
  try {
    return await fetchApi<Training>(`/staff/${staffId}/training`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create training record')
    }
    throw error
  }
}

export async function updateTraining(token: string, staffId: number, trainingId: number, data: Partial<Training>): Promise<Training> {
  try {
    return await fetchApi<Training>(`/staff/${staffId}/training/${trainingId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update training record')
    }
    throw error
  }
}

export async function deleteTraining(token: string, staffId: number, trainingId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/${staffId}/training/${trainingId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete training record')
    }
    throw error
  }
}

// ==================== Teacher Card ====================

export async function setTeacherCard(
  token: string,
  patronId: number,
  schoolId: number | null,
): Promise<AdminUser> {
  try {
    return await fetchApi<AdminUser>(`/staff/patrons/${patronId}/teacher-card`, {
      method: 'PATCH',
      token,
      body: { school_id: schoolId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || (schoolId === null ? 'Failed to revoke teacher card' : 'Failed to issue teacher card'))
    }
    throw error
  }
}

export interface TeacherCardSchoolOption {
  id: number
  name: string
  partner_type: string
}

interface PartnersListEnvelope {
  partners: TeacherCardSchoolOption[]
  total: number
  limit: number
  offset: number
}

export async function listSchoolPartnersForTeacherCard(
  token: string,
): Promise<TeacherCardSchoolOption[]> {
  try {
    const response = await fetchApi<PartnersListEnvelope>(
      '/outreach/partners?partner_type=school&limit=500',
      { token },
    )
    return response.partners
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to load school partners')
    }
    throw error
  }
}

// ==================== Staff Invite ====================

export interface InviteStaffData {
  email: string
  first_name: string
  last_name: string
  role: string
  staff_role?: string
}

export async function inviteStaff(data: InviteStaffData): Promise<void> {
  try {
    await fetchApi<void>('/staff-invites', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send invitation')
    }
    throw error
  }
}

export async function resendStaffInvite(userId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff-invites/${userId}/resend`, {
      method: 'POST',
      body: {},
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resend invitation')
    }
    throw error
  }
}

export async function revokeStaffInvite(userId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff-invites/${userId}`, {
      method: 'DELETE',
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to revoke invitation')
    }
    throw error
  }
}
