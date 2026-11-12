/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useAuth } from '@/contexts/AuthContext'
import { hasRole, type RoleGroup } from '@/auth/roleMatrix'
import type { User } from '@/api/domains/auth/auth-api'

export interface UseRequireRoleResult {
  user: User | null
  authLoading: boolean
  isAuthorized: boolean
}

export function useRequireRole(group: RoleGroup): UseRequireRoleResult {
  const { user, isLoading } = useAuth()
  return {
    user,
    authLoading: isLoading,
    isAuthorized: hasRole(user, group),
  }
}
