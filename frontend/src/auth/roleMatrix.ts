/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { User } from '@/api/domains/auth/auth-api'

export type Role = User['role']

/**
 * Named role groups used by admin-area pages. Treat this file as the single
 * source of truth for "who can see this admin page"; never inline a role
 * allowlist in a component.
 *
 * Backend equivalents live in `backend/app/api/v1/dependencies.py` and the
 * `_verify_admin_access` helper in `backend/app/api/v1/admin.py`. Keep them
 * in sync when changing a group.
 */
export const ADMIN_ROLE_GROUPS = {
  systemAdmin: ['admin', 'super_admin'],
  adminOrDirector: ['admin', 'super_admin', 'director'],
  adminOrStaff: ['admin', 'super_admin', 'staff'],
  adminStaffOrDirector: ['admin', 'super_admin', 'staff', 'director'],
  // Mirrors backend require_staff (dependencies.py): who may read staff
  // knowledge-base articles and decision trees.
  staffKnowledge: ['admin', 'super_admin', 'staff', 'director', 'legal'],
  superAdmin: ['super_admin'],
  teacher: ['teacher'],
} as const satisfies Record<string, ReadonlyArray<Role>>

export type RoleGroup = keyof typeof ADMIN_ROLE_GROUPS

export function hasRole(
  user: { role: Role } | null | undefined,
  group: RoleGroup,
): boolean {
  if (!user) return false
  return (ADMIN_ROLE_GROUPS[group] as ReadonlyArray<Role>).includes(user.role)
}
