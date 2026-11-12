/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Plus, Search, Edit2, Trash2, X, Loader2, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import { listStaff, createStaffMember, updateStaffMember, deleteStaffMember, type StaffMember } from '../api/api'
import ConfirmDialog from '../components/ConfirmDialog'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

const ROLES = ['staff', 'admin', 'LIBRARIAN', 'CIRCULATION', 'CATALOGING', 'REFERENCE']

export default function StaffManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    role: 'staff',
    department: '',
    is_active: true,
  })
  const [deleteStaffConfirm, setDeleteStaffConfirm] = useState<{ id: number; name: string } | null>(null)

  const loadStaff = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const result = await listStaff(token, 1, 100, searchQuery ? { search: searchQuery } : undefined)
      setStaff(result.staff || [])
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.staffManagement.failedToLoadStaff'))
    } finally {
      setIsLoading(false)
    }
  }


  useEffect(() => {
    if (!user || !['admin', 'super_admin'].includes(user.role)) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      return
    }
    loadStaff()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const handleSearch = () => loadStaff()

  const openAddForm = () => {
    setFormData({ first_name: '', last_name: '', email: '', role: 'staff', department: '', is_active: true })
    setEditingId(null)
    setShowForm(true)
  }

  const openEditForm = (member: StaffMember) => {
    setFormData({
      first_name: member.first_name,
      last_name: member.last_name,
      email: member.email,
      role: member.role,
      department: member.department || '',
      is_active: member.is_active,
    })
    setEditingId(member.id)
    setShowForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return

    setIsSubmitting(true)
    try {
      if (editingId) {
        await updateStaffMember(token, editingId, formData)
        toast.success(t('toast.staffManagement.staffMemberUpdated'))
      } else {
        await createStaffMember(token, formData)
        toast.success(t('toast.staffManagement.staffMemberAdded'))
      }
      setShowForm(false)
      loadStaff()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.saveFailed'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!token) return

    try {
      await deleteStaffMember(token, id)
      toast.success(t('toast.staffManagement.staffMemberDeleted'))
      setDeleteStaffConfirm(null)
      loadStaff()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.deleteFailed'))
    }
  }

  if (!user || !['admin', 'super_admin'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <p className="text-lsc-dark dark:text-lsc-cream">Admin access required</p>
        </PageContainer>
      </div>
    )
  }

  return (

    <AdminShell title="Staff Management" subtitle={t('staffManagement.manageLibraryStaffMembers')}>    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-8">
      <PageContainer>
        <div className="flex items-center justify-between mb-8">
          <div></div>
          <button onClick={openAddForm} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors">
            <Plus className="w-5 h-5" />
            Add Staff
          </button>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6">
          <div className="flex gap-2">
            <input type="text" placeholder={t('staffManagement.searchByNameOrEmail')} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} aria-label={t('aria.staffManagement.searchStaff')} className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
            <button onClick={handleSearch} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2">
              <Search className="w-5 h-5" />
              Search
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
          </div>
        ) : staff.length === 0 ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffManagement.noStaffMembersFound')}</p>
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Name</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Email</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Role</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Department</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Status</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {staff.map((member) => (
                    <tr key={member.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {member.first_name} {member.last_name}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{member.email}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className="px-2 py-1 bg-lsc-cream dark:bg-lsc-brown rounded text-lsc-dark dark:text-lsc-cream text-xs font-medium">
                          {member.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{member.department || '-'}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${member.is_active ? 'bg-status-success-100 text-status-success-700' : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                          {member.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button onClick={() => openEditForm(member)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 rounded-xl transition-colors" aria-label={`Edit staff member ${member.first_name} ${member.last_name}`}>
                            <Edit2 className="w-4 h-4" aria-hidden="true" />
                          </button>
                          <button onClick={() => setDeleteStaffConfirm({ id: member.id, name: `${member.first_name} ${member.last_name}` })} className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-xl transition-colors" aria-label={`Delete staff member ${member.first_name} ${member.last_name}`}>
                            <Trash2 className="w-4 h-4" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </PageContainer>

      {showForm && (
        <ModalBackdrop onClose={() => setShowForm(false)} title={editingId ? 'Edit Staff Member' : 'Add Staff Member'}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editingId ? 'Edit Staff Member' : 'Add Staff Member'}
              </h2>
              <button onClick={() => setShowForm(false)} className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full" aria-label={t('aria.authModals.close')}>
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="staff-first-name" className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">First Name *</label>
                  <input id="staff-first-name" type="text" value={formData.first_name} onChange={(e) => setFormData({ ...formData, first_name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
                </div>
                <div>
                  <label htmlFor="staff-last-name" className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Last Name *</label>
                  <input id="staff-last-name" type="text" value={formData.last_name} onChange={(e) => setFormData({ ...formData, last_name: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
                </div>
              </div>
              <div>
                <label htmlFor="staff-email" className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Email *</label>
                <input id="staff-email" type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="staff-role-select" className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Role</label>
                  <select id="staff-role-select" value={formData.role} onChange={(e) => setFormData({ ...formData, role: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="staff-department" className="block text-sm font-medium text-lsc-dark dark:text-earth-300 mb-1">Department</label>
                  <input id="staff-department" type="text" value={formData.department} onChange={(e) => setFormData({ ...formData, department: e.target.value })} placeholder={t('placeholder.staffManagement.egCirculation')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="active" checked={formData.is_active} onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })} className="w-4 h-4" />
                <label htmlFor="active" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Active
                </label>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border">
                <button type="button" onClick={() => setShowForm(false)} disabled={isSubmitting} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl font-medium disabled:opacity-50">
                  Cancel
                </button>
                <button type="submit" disabled={isSubmitting} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50">
                  {isSubmitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Check className="w-4 h-4" />}
                  {isSubmitting ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </ModalBackdrop>
      )}

      <ConfirmDialog
        isOpen={!!deleteStaffConfirm}
        title="Delete Staff Member?"
        message={`Are you sure you want to delete ${deleteStaffConfirm?.name}? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteStaffConfirm) handleDelete(deleteStaffConfirm.id) }}
        onCancel={() => setDeleteStaffConfirm(null)}
      />
    </div>
  </AdminShell>
  )
}
