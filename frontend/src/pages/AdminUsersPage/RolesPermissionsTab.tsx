/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  Shield,
  Plus,
  Edit,
  AlertCircle,
  Loader2,
  Check,
  Layers,
  Key,
} from 'lucide-react'
import { useTranslation} from '@/i18n'
import {
  PERMISSION_TEMPLATES,
} from '../../api/staff-api'
import ApplyTemplateModal from './ApplyTemplateModal'
import type { useRolesPermissions } from './useRolesPermissions'

type RolesPermissionsReturn = ReturnType<typeof useRolesPermissions>

interface RolesPermissionsTabProps {
  rolesPermissions: RolesPermissionsReturn
}

const RolesPermissionsTab: React.FC<RolesPermissionsTabProps> = ({ rolesPermissions }) => {
  const { t } = useTranslation()
  const {
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
    setShowAddRoleModal,
    setEditingRole,
    handlePermissionToggle,
    handleApplyTemplate,
    fetchRolesAndPermissions,
  } = rolesPermissions

  return (
    <div className="space-y-8">
      {/* Loading State */}
      {rolesLoading ? (
        <div role="status" aria-live="polite" className="flex justify-center items-center py-20">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-lsc-rose motion-safe:animate-spin mx-auto mb-4" aria-hidden="true" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Loading roles and permissions...
            </p>
          </div>
        </div>
      ) : rolesError ? (
        <div className="p-6 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl flex items-start gap-4">
          <AlertCircle className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-status-danger-800 dark:text-status-danger-300 font-semibold mb-2">{t('admin.adminUsers.failedToLoadRolesAnd')}</p>
            <p className="text-status-danger-700 dark:text-status-danger-400 mb-4">{rolesError}</p>
            <button
              onClick={() => fetchRolesAndPermissions()}
              className="text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 font-semibold"
            >
              Try again
            </button>
          </div>
        </div>
      ) : roles.length === 0 ? (
        <div className="text-center py-20 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No roles available</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Contact your system administrator to create roles.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Roles Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden shadow-sm">
              <div className="bg-lsc-cream dark:bg-earth-700 px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between gap-2">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Roles</h3>
                <button
                  onClick={() => setShowAddRoleModal(true)}
                  className="p-1.5 hover:bg-lsc-rose/20 rounded-lg transition-colors text-lsc-rose"
                  title="Create new role"
                  aria-label={t('aria.rolesPermissionsTab.createNewRole')}
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="divide-y divide-earth-200 dark:divide-earth-700">
                {roles.map((role) => (
                  <div
                    key={role.id}
                    className={`flex items-center gap-0 transition-colors duration-200 group ${
                      selectedRoleId === role.id
                        ? 'bg-lsc-rose/10'
                        : 'hover:bg-lsc-cream/50 dark:hover:bg-earth-700'
                    }`}
                  >
                    <button
                      onClick={() => setSelectedRoleId(role.id)}
                      aria-current={selectedRoleId === role.id ? 'true' : undefined}
                      className="flex-1 text-left px-6 py-4 transition-colors duration-200"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={role.name}>
                            {role.name}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate" title={`${role.permissions.length} permissions`}>
                            {role.permissions.length} permissions
                          </p>
                        </div>
                        {selectedRoleId === role.id && (
                          <Check className="w-5 h-5 text-lsc-rose flex-shrink-0" aria-hidden="true" />
                        )}
                      </div>
                    </button>
                    <button
                      onClick={() => setEditingRole(role)}
                      className="px-3 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors opacity-0 group-hover:opacity-100"
                      title={`Edit ${role.name}`}
                      aria-label={`Edit ${role.name}`}
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Permissions Panel */}
          <div className="lg:col-span-3 space-y-6">
            {selectedRole && (
              <>
                {/* Role Info Card */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-lsc-rose/20 dark:bg-lsc-rose/10 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Shield className="w-6 h-6 text-lsc-rose" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                        {selectedRole.name}
                      </h2>
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {selectedRole.description || 'No description'}
                      </p>
                      <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700 flex flex-wrap gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg text-sm font-medium">
                          <Layers className="w-4 h-4" />
                          {selectedRole.permissions.length} permission{selectedRole.permissions.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Permission Templates */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 shadow-sm">
                  <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                    <Layers className="w-5 h-5" />
                    Quick Templates
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                    Apply a pre-configured set of permissions to this role:
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {PERMISSION_TEMPLATES.map((template) => (
                      <button
                        key={template.name}
                        onClick={() => setShowTemplateModal(selectedRole.id)}
                        disabled={applyingTemplate}
                        className="p-4 border-2 border-lsc-border dark:border-earth-700 hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 rounded-xl transition-all duration-200 text-left disabled:opacity-50 disabled:cursor-not-allowed group"
                      >
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 bg-lsc-cream dark:bg-earth-700 group-hover:bg-lsc-rose/20 dark:group-hover:bg-lsc-rose/10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors">
                            <Layers className="w-4 h-4 text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">
                              {template.name}
                            </p>
                            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2" title={template.description}>
                              {template.description}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Permissions Grid */}
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden shadow-sm">
                  <div className="bg-lsc-cream dark:bg-earth-700 px-6 py-4 border-b border-lsc-border dark:border-earth-700">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                      <Key className="w-5 h-5" />
                      Permissions
                    </h3>
                  </div>

                  <div className="divide-y divide-earth-200 dark:divide-earth-700">
                    {permissionsByCategory.length === 0 ? (
                      <div className="p-8 text-center">
                        <Key className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          No permissions available
                        </p>
                      </div>
                    ) : (
                      permissionsByCategory.map(({ category, permissions: categoryPermissions }) => (
                        <div key={category}>
                          <div className="bg-lsc-cream/50 dark:bg-earth-700/50 px-6 py-3 border-b border-lsc-border dark:border-earth-700">
                            <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream uppercase tracking-wide">
                              {category.replace(/_/g, ' ')}
                            </h4>
                          </div>
                          <div className="divide-y divide-earth-200 dark:divide-earth-700">
                            {categoryPermissions.map((permission) => {
                              const hasPermission = selectedRole.permissions.includes(permission.code)
                              const isChanging =
                                permissionChanging?.roleId === selectedRole.id &&
                                permissionChanging?.permissionId === permission.id

                              return (
                                <div
                                  key={permission.id}
                                  className={`px-6 py-4 flex items-start gap-4 transition-colors ${
                                    hasPermission
                                      ? 'bg-status-success-50 dark:bg-status-success-900/10'
                                      : 'hover:bg-lsc-cream/30 dark:hover:bg-earth-700/50'
                                  }`}
                                >
                                  <button
                                    onClick={() =>
                                      handlePermissionToggle(
                                        selectedRole.id,
                                        permission.id,
                                        hasPermission
                                      )
                                    }
                                    disabled={isChanging}
                                    className={`mt-1 w-6 h-6 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                                      hasPermission
                                        ? 'bg-status-success-600 dark:bg-status-success-500 border-status-success-600 dark:border-status-success-500'
                                        : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
                                    } ${isChanging ? 'opacity-50 cursor-not-allowed' : ''}`}
                                    title={
                                      hasPermission
                                        ? `Remove ${permission.name} permission`
                                        : `Add ${permission.name} permission`
                                    }
                                    aria-label={
                                      hasPermission
                                        ? `Remove ${permission.name} permission`
                                        : `Add ${permission.name} permission`
                                    }
                                  >
                                    {isChanging ? (
                                      <Loader2 className="w-4 h-4 text-white motion-safe:animate-spin" />
                                    ) : hasPermission ? (
                                      <Check className="w-4 h-4 text-white" />
                                    ) : null}
                                  </button>
                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                                      {permission.name}
                                    </p>
                                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                                      {permission.description}
                                    </p>
                                    <div className="mt-2">
                                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose">
                                        {permission.code}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Template Application Modal */}
      {showTemplateModal && selectedRole && (
        <ApplyTemplateModal
          roleName={selectedRole.name}
          isApplying={applyingTemplate}
          onApply={(template) => handleApplyTemplate(selectedRole.id, template)}
          onCancel={() => setShowTemplateModal(null)}
        />
      )}
    </div>
  )
}

export default RolesPermissionsTab
