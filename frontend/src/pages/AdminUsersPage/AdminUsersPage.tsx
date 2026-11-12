/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useId, useRef, useState, type KeyboardEvent } from 'react'
import { useRequireRole } from '@/hooks/useRequireRole'
import { AdminShell } from '../../components/shells'
import {
  Shield,
  Users,
  Key,
} from 'lucide-react'
import AddUserModal from '../../components/AddUserModal'
import InviteStaffModal from '../../components/InviteStaffModal'
import EditUserModal from '../../components/EditUserModal'
import AddRoleModal from '../../components/AddRoleModal'
import EditRoleModal from '../../components/EditRoleModal'
import ConfirmDialog from '../../components/ConfirmDialog'
import { useUsersAdmin } from './useUsersAdmin'
import { useRolesPermissions } from './useRolesPermissions'
import UsersTab from './UsersTab'
import RolesPermissionsTab from './RolesPermissionsTab'
import PageContainer from '@/components/layout/PageContainer'
import { useTranslation } from '@/i18n'

// Tab types
type AdminTab = 'users' | 'roles'

const TABS: AdminTab[] = ['users', 'roles']

export default function AdminUsersPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthorized } = useRequireRole('systemAdmin')

  // Active tab state
  const [activeTab, setActiveTab] = useState<AdminTab>('users')
  const [showInviteModal, setShowInviteModal] = useState(false)

  const baseId = useId()
  const tabId = (tab: AdminTab) => `${baseId}-${tab}-tab`
  const panelId = (tab: AdminTab) => `${baseId}-${tab}-panel`

  const tabRefs = useRef<Partial<Record<AdminTab, HTMLButtonElement | null>>>({})

  const focusTab = (tab: AdminTab) => {
    setActiveTab(tab)
    requestAnimationFrame(() => {
      tabRefs.current[tab]?.focus()
    })
  }

  const handleTabKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const currentIndex = TABS.indexOf(activeTab)
    let nextIndex: number | null = null
    if (e.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % TABS.length
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + TABS.length) % TABS.length
    } else if (e.key === 'Home') {
      nextIndex = 0
    } else if (e.key === 'End') {
      nextIndex = TABS.length - 1
    }
    if (nextIndex !== null) {
      e.preventDefault()
      focusTab(TABS[nextIndex]!)
    }
  }

  // Hooks
  const usersAdmin = useUsersAdmin()
  const rolesPermissions = useRolesPermissions(activeTab)

  // Check admin access
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-earth-900 dark:via-earth-900 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Staff-Only Area
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            Admin access required
          </p>
        </PageContainer>
      </div>
    )
  }

  return (
    <AdminShell
      title="User Management"
      subtitle="Manage system users, roles, and access permissions"
      icon={<Users className="w-7 h-7 text-lsc-rose" />}
    >
        {/* Tabs */}
        <div role="tablist" aria-label={t('aria.adminUsers.tablistLabel', 'User management sections')} className="flex gap-1 mb-6 bg-lsc-white dark:bg-earth-800 rounded-xl p-1.5 border border-lsc-border dark:border-earth-700 w-fit">
          <button
            ref={(el) => { tabRefs.current.users = el }}
            id={tabId('users')}
            role="tab"
            type="button"
            aria-selected={activeTab === 'users'}
            aria-controls={panelId('users')}
            tabIndex={activeTab === 'users' ? 0 : -1}
            onClick={() => setActiveTab('users')}
            onKeyDown={handleTabKeyDown}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all duration-200 ${
              activeTab === 'users'
                ? 'bg-lsc-rose text-white shadow-md'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'
            }`}
          >
            <Users className="w-4 h-4" />
            Users
          </button>
          <button
            ref={(el) => { tabRefs.current.roles = el }}
            id={tabId('roles')}
            role="tab"
            type="button"
            aria-selected={activeTab === 'roles'}
            aria-controls={panelId('roles')}
            tabIndex={activeTab === 'roles' ? 0 : -1}
            onClick={() => setActiveTab('roles')}
            onKeyDown={handleTabKeyDown}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all duration-200 ${
              activeTab === 'roles'
                ? 'bg-lsc-rose text-white shadow-md'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'
            }`}
          >
            <Key className="w-4 h-4" />
            Roles & Permissions
          </button>
        </div>

        {/* Users Tab Content */}
        {activeTab === 'users' && (
          <div
            role="tabpanel"
            id={panelId('users')}
            aria-labelledby={tabId('users')}
            tabIndex={0}
          >
            <UsersTab usersAdmin={usersAdmin} onInviteStaff={() => setShowInviteModal(true)} />
          </div>
        )}

        {/* Roles & Permissions Tab Content */}
        {activeTab === 'roles' && (
          <div
            role="tabpanel"
            id={panelId('roles')}
            aria-labelledby={tabId('roles')}
            tabIndex={0}
          >
            <RolesPermissionsTab rolesPermissions={rolesPermissions} />
          </div>
        )}

        {/* Modals */}
        <AddUserModal
          isOpen={usersAdmin.showAddModal}
          onClose={() => usersAdmin.setShowAddModal(false)}
          onSuccess={usersAdmin.handleUserAdded}
        />

        <InviteStaffModal
          isOpen={showInviteModal}
          onClose={() => setShowInviteModal(false)}
          onSuccess={usersAdmin.handleUserAdded}
        />

        <AddRoleModal
          isOpen={rolesPermissions.showAddRoleModal}
          onClose={() => rolesPermissions.setShowAddRoleModal(false)}
          onSuccess={rolesPermissions.handleRoleAdded}
        />

        {rolesPermissions.editingRole && (
          <EditRoleModal
            role={rolesPermissions.editingRole}
            isOpen={true}
            onClose={() => rolesPermissions.setEditingRole(null)}
            onSuccess={rolesPermissions.handleRoleUpdated}
          />
        )}

        {usersAdmin.editingUser && (
          <EditUserModal
            user={usersAdmin.editingUser}
            onClose={() => usersAdmin.setEditingUser(null)}
            onSuccess={usersAdmin.handleUserUpdated}
          />
        )}

        {usersAdmin.deleteConfirm && (
          <ConfirmDialog
            isOpen={true}
            title="Delete User Account"
            message={`Permanently delete ${usersAdmin.deleteConfirm.userName}'s account? This will remove their library card, reading history, current holds, and all checkout records. This action cannot be undone.`}
            confirmText="Delete"
            confirmVariant="danger"
            onConfirm={usersAdmin.handleDeleteUser}
            onCancel={() => usersAdmin.setDeleteConfirm(null)}
          />
        )}

        {usersAdmin.lockConfirm && (
          <ConfirmDialog
            isOpen={true}
            title={usersAdmin.lockConfirm.isLocking ? 'Lock Account' : 'Unlock Account'}
            message={usersAdmin.lockConfirm.isLocking
              ? `Lock ${usersAdmin.lockConfirm.userName}'s account? They will not be able to log in, check out items, or place holds until unlocked. Their current checkouts will not be affected.`
              : `Unlock ${usersAdmin.lockConfirm.userName}'s account? They will be able to log in and use library services again.`}
            confirmText={usersAdmin.lockConfirm.isLocking ? 'Lock' : 'Unlock'}
            confirmVariant={usersAdmin.lockConfirm.isLocking ? 'warning' : 'success'}
            onConfirm={usersAdmin.handleLockToggle}
            onCancel={() => usersAdmin.setLockConfirm(null)}
          />
        )}

        {usersAdmin.passwordResetConfirm && (
          <ConfirmDialog
            isOpen={true}
            title="Send Password Reset"
            message={`Send a password reset link to ${usersAdmin.passwordResetConfirm.userName} (${usersAdmin.passwordResetConfirm.userEmail})? They will receive an email with instructions to reset their password. The link will expire in 24 hours.`}
            confirmText="Send Reset Link"
            confirmVariant="primary"
            onConfirm={usersAdmin.handlePasswordReset}
            onCancel={() => usersAdmin.setPasswordResetConfirm(null)}
          />
        )}

        {usersAdmin.revokeConfirm && (
          <ConfirmDialog
            isOpen={true}
            title="Revoke Invitation"
            message={`Revoke this pending invitation for ${usersAdmin.revokeConfirm.userName}? They will no longer be able to use the invitation link to create their account.`}
            confirmText="Revoke"
            confirmVariant="danger"
            onConfirm={usersAdmin.handleRevokeInvite}
            onCancel={() => usersAdmin.setRevokeConfirm(null)}
          />
        )}
    </AdminShell>
  )
}
