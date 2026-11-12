/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * User Management Constants
 * Centralized constants for user-related operations
 */

export const USER_ROLES = ['patron', 'teacher', 'staff', 'admin', 'super_admin'] as const
export type UserRole = typeof USER_ROLES[number]

export const USER_STATUS_OPTION_KEYS = [
  { value: true, labelKey: 'userManagement.statusActive' },
  { value: false, labelKey: 'userManagement.statusInactive' },
] as const

export const USER_ROLE_DESCRIPTION_KEYS: Record<UserRole, string> = {
  patron: 'userManagement.rolePatron',
  teacher: 'userManagement.roleTeacher',
  staff: 'userManagement.roleStaff',
  admin: 'userManagement.roleAdmin',
  super_admin: 'userManagement.roleSuperAdmin',
} as const

export const USER_PASSWORD_CONSTRAINTS = {
  MIN_LENGTH: 8,
  MAX_LENGTH: 128,
} as const

export const USER_EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export const USER_SORT_OPTION_KEYS = [
  { value: 'name', labelKey: 'userManagement.sortName' },
  { value: 'email', labelKey: 'userManagement.sortEmail' },
  { value: 'role', labelKey: 'userManagement.sortRole' },
  { value: 'created_at', labelKey: 'userManagement.sortDateCreated' },
  { value: 'last_login', labelKey: 'userManagement.sortLastLogin' },
] as const

export const SORT_ORDER_OPTION_KEYS = [
  { value: 'asc', labelKey: 'userManagement.sortAscending' },
  { value: 'desc', labelKey: 'userManagement.sortDescending' },
] as const

export const DEFAULT_PAGINATION = {
  PER_PAGE: 20,
  CURRENT_PAGE: 1,
} as const

/** @deprecated Use USER_STATUS_OPTION_KEYS with t() instead */
export const USER_STATUS_OPTIONS = USER_STATUS_OPTION_KEYS
/** @deprecated Use USER_SORT_OPTION_KEYS with t() instead */
export const USER_SORT_OPTIONS = USER_SORT_OPTION_KEYS
/** @deprecated Use SORT_ORDER_OPTION_KEYS with t() instead */
export const SORT_ORDER_OPTIONS = SORT_ORDER_OPTION_KEYS
/** @deprecated Use USER_ROLE_DESCRIPTION_KEYS with t() instead */
export const USER_ROLE_DESCRIPTIONS = USER_ROLE_DESCRIPTION_KEYS
