/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Custom hook for AdminUsersPage — Roles & Permissions tab logic
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import toast from 'react-hot-toast'
import {
  listRoles,
  listPermissions,
  assignPermissionToRole,
  removePermissionFromRole,
  applyPermissionTemplate,
  type Role,
  type Permission,
  type PermissionTemplate,
} from '../../api/staff-api'

export function useRolesPermissions(activeTab: 'users' | 'roles') {
  const { token } = useAuth()

  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [rolesLoading, setRolesLoading] = useState(false)
  const [rolesError, setRolesError] = useState<string | null>(null)
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null)
  const [permissionChanging, setPermissionChanging] = useState<{ roleId: string; permissionId: number } | null>(null)
  const [showTemplateModal, setShowTemplateModal] = useState<string | null>(null)
  const [applyingTemplate, setApplyingTemplate] = useState(false)
  const [showAddRoleModal, setShowAddRoleModal] = useState(false)
  const [editingRole, setEditingRole] = useState<Role | null>(null)

  const fetchRolesAndPermissions = useCallback(async () => {
    if (!token) return
    try {
      setRolesLoading(true)
      setRolesError(null)
      const [rolesData, permissionsData] = await Promise.all([
        listRoles(token),
        listPermissions(token),
      ])
      setRoles(rolesData)
      setPermissions(permissionsData)
      if (!selectedRoleId && rolesData.length > 0) {
        setSelectedRoleId(rolesData[0]!.id)
      }
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to fetch roles and permissions'
      setRolesError(message)
      toast.error(message)
    } finally {
      setRolesLoading(false)
    }
  }, [token, selectedRoleId])

  useEffect(() => {
    if (activeTab === 'roles' && roles.length === 0 && !rolesLoading) {
      fetchRolesAndPermissions()
    }
  }, [activeTab, roles.length, rolesLoading, fetchRolesAndPermissions])

  const handlePermissionToggle = async (roleId: string, permissionId: number, hasPermission: boolean) => {
    if (!token || permissionChanging) return
    try {
      setPermissionChanging({ roleId, permissionId })
      let updatedRole: Role
      if (hasPermission) {
        updatedRole = await removePermissionFromRole(token, roleId, permissionId)
        toast.success('Permission removed')
      } else {
        updatedRole = await assignPermissionToRole(token, roleId, permissionId)
        toast.success('Permission added')
      }
      setRoles(prev => prev.map(r => r.id === roleId ? updatedRole : r))
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to update permission'
      toast.error(message)
    } finally {
      setPermissionChanging(null)
    }
  }

  const handleApplyTemplate = async (roleId: string, template: PermissionTemplate) => {
    if (!token || applyingTemplate) return
    try {
      setApplyingTemplate(true)
      const updatedRole = await applyPermissionTemplate(token, roleId, template.permissionCodes, permissions)
      setRoles(prev => prev.map(r => r.id === roleId ? updatedRole : r))
      toast.success(`Template "${template.name}" applied successfully`)
      setShowTemplateModal(null)
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Failed to apply template'
      toast.error(message)
    } finally {
      setApplyingTemplate(false)
    }
  }

  const permissionsByCategory = useMemo(() => {
    const grouped: Record<string, Permission[]> = {}
    permissions.forEach(p => {
      if (!grouped[p.category]) grouped[p.category] = []
      grouped[p.category]!.push(p)
    })
    const sortedCategories = Object.keys(grouped).sort()
    return sortedCategories.map(category => ({
      category,
      permissions: grouped[category]!.sort((a, b) => a.name.localeCompare(b.name)),
    }))
  }, [permissions])

  const selectedRole = useMemo(() => {
    return roles.find(r => r.id === selectedRoleId) || null
  }, [roles, selectedRoleId])

  const handleRoleAdded = () => {
    setShowAddRoleModal(false)
    fetchRolesAndPermissions()
  }

  const handleRoleUpdated = () => {
    setEditingRole(null)
    fetchRolesAndPermissions()
  }

  return {
    roles,
    rolesLoading,
    rolesError,
    selectedRoleId,
    setSelectedRoleId,
    selectedRole,
    permissionChanging,
    permissionsByCategory,
    showTemplateModal,
    setShowTemplateModal,
    applyingTemplate,
    showAddRoleModal,
    setShowAddRoleModal,
    editingRole,
    setEditingRole,
    handlePermissionToggle,
    handleApplyTemplate,
    handleRoleAdded,
    handleRoleUpdated,
    fetchRolesAndPermissions,
  }
}
