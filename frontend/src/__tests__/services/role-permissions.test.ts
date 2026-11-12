/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  listRoles,
  listPermissions,
  assignPermissionToRole,
  removePermissionFromRole,
  applyPermissionTemplate,
  createRole,
  updateRole,
  deleteRole,
  type Role,
  type Permission,
  PERMISSION_TEMPLATES,
} from '@/api/staff-api'

// Mock the fetch API
const mockFetch = vi.fn()
global.fetch = mockFetch as unknown as typeof fetch

describe('Role and Permission Services', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockToken = 'test-token'

  describe('listRoles', () => {
    it('should fetch all roles', async () => {
      const mockRoles: Role[] = [
        {
          id: '1',
          name: 'Admin',
          description: 'Administrator role',
          permissions: [],
        },
        {
          id: '2',
          name: 'Staff',
          description: 'Staff role',
          permissions: [],
        },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRoles,
      })

      const result = await listRoles(mockToken)

      expect(result).toEqual(mockRoles)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/roles'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      )
    })

    it('should handle fetch errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      })

      await expect(listRoles(mockToken)).rejects.toThrow()
    })
  })

  describe('listPermissions', () => {
    it('should fetch all permissions', async () => {
      const mockPermissions: Permission[] = [
        {
          id: 1,
          code: 'circulation.checkout',
          name: 'Checkout Items',
          description: 'Allow checkouts',
          category: 'circulation',
        },
        {
          id: 2,
          code: 'circulation.renew',
          name: 'Renew Items',
          description: 'Allow renewals',
          category: 'circulation',
        },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPermissions,
      })

      const result = await listPermissions(mockToken)

      expect(result).toEqual(mockPermissions)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/permissions'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      )
    })
  })

  describe('assignPermissionToRole', () => {
    it('should assign a permission to a role', async () => {
      const roleId = '1'
      const permissionId = 1
      const mockUpdatedRole: Role = {
        id: roleId,
        name: 'Admin',
        description: 'Administrator role',
        permissions: ['circulation.checkout'],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedRole,
      })

      const result = await assignPermissionToRole(mockToken, roleId, permissionId)

      expect(result).toEqual(mockUpdatedRole)
      expect(result.permissions).toHaveLength(1)
      expect(result.permissions[0]).toBeDefined()
    })
  })

  describe('removePermissionFromRole', () => {
    it('should remove a permission from a role', async () => {
      const roleId = '1'
      const permissionId = 1
      const mockUpdatedRole: Role = {
        id: roleId,
        name: 'Admin',
        description: 'Administrator role',
        permissions: [],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedRole,
      })

      const result = await removePermissionFromRole(mockToken, roleId, permissionId)

      expect(result).toEqual(mockUpdatedRole)
      expect(result.permissions).toHaveLength(0)
    })
  })

  describe('createRole', () => {
    it('should create a new role', async () => {
      const newRoleData = {
        name: 'Content Manager',
        description: 'Manages catalog content',
      }

      const mockCreatedRole: Role = {
        id: '3',
        ...newRoleData,
        permissions: [],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCreatedRole,
      })

      const result = await createRole(mockToken, newRoleData)

      expect(result).toEqual(mockCreatedRole)
      expect(result.name).toBe(newRoleData.name)
    })
  })

  describe('updateRole', () => {
    it('should update an existing role', async () => {
      const roleId = '1'
      const updates = {
        name: 'Updated Admin',
        description: 'Updated administrator role',
      }

      const mockUpdatedRole: Role = {
        id: roleId,
        ...updates,
        permissions: [],
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockUpdatedRole,
      })

      const result = await updateRole(mockToken, roleId, updates)

      expect(result).toEqual(mockUpdatedRole)
      expect(result.name).toBe(updates.name)
    })
  })

  describe('deleteRole', () => {
    it('should delete a role', async () => {
      const roleId = '1'

      mockFetch.mockResolvedValueOnce({
        ok: true,
      })

      await deleteRole(mockToken, roleId)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/roles/${roleId}`),
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('applyPermissionTemplate', () => {
    it('should apply a template with multiple permissions', async () => {
      const roleId = '1'
      const template = PERMISSION_TEMPLATES[0]
      if (!template) throw new Error('Template not found')
      const mockPermissions: Permission[] = [
        {
          id: 1,
          code: template.permissionCodes[0] ?? '',
          name: 'Permission 1',
          description: 'Test permission 1',
          category: 'circulation',
        },
        {
          id: 2,
          code: template.permissionCodes[1] ?? '',
          name: 'Permission 2',
          description: 'Test permission 2',
          category: 'circulation',
        },
      ]

      const mockUpdatedRole: Role = {
        id: roleId,
        name: 'Admin',
        description: 'Administrator role',
        permissions: mockPermissions.map(p => p.code),
      }

      // applyPermissionTemplate diffs against the role's *current*
      // permissions before assigning anything (getRole), then re-fetches
      // the role once it's done (getRole again). Since mockUpdatedRole
      // already carries every code the template maps, the diff finds
      // nothing missing and skips straight to the second getRole call.
      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => mockUpdatedRole,
      })

      const result = await applyPermissionTemplate(
        mockToken,
        roleId,
        template.permissionCodes,
        mockPermissions
      )

      expect(result).toEqual(mockUpdatedRole)
      expect(result.permissions.length).toBeGreaterThan(0)
    })
  })

  describe('Permission Templates', () => {
    it('should have valid permission templates', () => {
      expect(PERMISSION_TEMPLATES).toBeDefined()
      expect(Array.isArray(PERMISSION_TEMPLATES)).toBe(true)
      expect(PERMISSION_TEMPLATES.length).toBeGreaterThan(0)

      PERMISSION_TEMPLATES.forEach((template) => {
        expect(template).toHaveProperty('name')
        expect(template).toHaveProperty('description')
        expect(template).toHaveProperty('permissionCodes')
        expect(Array.isArray(template.permissionCodes)).toBe(true)
      })
    })

    it('each template should have at least one permission code', () => {
      PERMISSION_TEMPLATES.forEach((template) => {
        expect(template.permissionCodes.length).toBeGreaterThan(0)
        template.permissionCodes.forEach((code) => {
          expect(typeof code).toBe('string')
          expect(code.length).toBeGreaterThan(0)
        })
      })
    })
  })
})
