/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import { Plus, Edit2, Trash2, Search, Loader2, AlertCircle, Mail, Phone, UserCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../ConfirmDialog'
import BoardMemberForm from './BoardMemberForm'
import api from '../../api/api'
import { API_BASE } from '@/api/types'
import { useTranslation} from '@/i18n'

export interface BoardMember {
  id: number
  full_name: string
  email: string
  phone?: string
  position: string

  term_start_date: string
  is_current: boolean
}

interface BoardMembersSectionProps {
  token: string | null
  userRole: string
}

const POSITION_COLORS: Record<string, string> = {
  Chair: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300',
  'Vice Chair': 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  Secretary: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  Treasurer: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  Member: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
}

export default function BoardMembersSection({
  token,
  userRole,
}: BoardMembersSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const [members, setMembers] = useState<BoardMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingMember, setEditingMember] = useState<BoardMember | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const isAdmin = ['admin', 'super_admin'].includes(userRole)

  const fetchMembers = useCallback(async () => {
    if (!token) return

    try {
      setLoading(true)
      setError(null)
      const data = await api.get(`${API_BASE}/board/members`)
      if (data && typeof data === 'object') {
        const members = Array.isArray(data) ? data : (data.members || [])
        setMembers(members)
      }
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to load board members. Please try again.'
      setError(message)
      toast.error(message)
      setMembers([])
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchMembers()
  }, [fetchMembers])

  const handleAddMember = async (formData: unknown) => {
    if (!token) return

    try {
      setSubmitting(true)
      await api.post(`${API_BASE}/board/members`, formData)
      toast.success(t('components.board.boardMembersSection.boardMemberAddedSuccessfully'))
      setShowForm(false)
      await fetchMembers()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to add board member. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdateMember = async (formData: unknown) => {
    if (!token || !editingMember) return

    try {
      setSubmitting(true)
      await api.put(`${API_BASE}/board/members/${editingMember.id}`, formData)
      toast.success(t('components.board.boardMembersSection.boardMemberUpdatedSuccessfully'))
      setEditingMember(null)
      await fetchMembers()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to update board member. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteMember = async () => {
    if (!token || !deleteConfirm) return

    try {
      setSubmitting(true)
      await api.delete(`${API_BASE}/board/members/${deleteConfirm.id}`)
      toast.success(t('components.board.boardMembersSection.boardMemberDeletedSuccessfully'))
      setDeleteConfirm(null)
      await fetchMembers()
    } catch (_err) {
      const message = _err instanceof Error ? _err.message : 'Unable to delete board member. Please try again.'
      toast.error(message)
    } finally {
      setSubmitting(false)
    }
  }

  const filteredMembers = members.filter((member) => {
    const query = searchQuery.toLowerCase()
    return (
      (member.full_name || '').toLowerCase().includes(query) ||
      (member.email || '').toLowerCase().includes(query)
    )
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header and Search */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            Board Members
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {members.length} members registered
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => {
              setEditingMember(null)
              setShowForm(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Member
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <input
          type="text"
          placeholder={t('components.board.boardMembersSection.searchByNameOrEmail')}
          aria-label={t('components.board.boardMembersSection.searchByNameOrEmail2')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        />
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-900/50 rounded-lg flex gap-3">
          <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</p>
        </div>
      )}

      {/* Members List */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
        {filteredMembers.length === 0 ? (
          <div className="p-8 text-center">
            <UserCheck className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {searchQuery ? 'No members found matching your search' : 'No board members yet'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto overflow-y-auto max-h-[calc(100vh-300px)]">
            <table className="w-full" aria-label={t('aria.board.boardMembersDirectory')}>
              <thead className="bg-lsc-cream dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Name
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Role
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Contact
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                    Term Start
                  </th>
                  {isAdmin && (
                    <th scope="col" className="px-6 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Actions
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                {filteredMembers.map((member) => (
                  <tr
                    key={member.id}
                    className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {member.full_name}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {member.position && (
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                            POSITION_COLORS[member.position] || POSITION_COLORS['Member']
                          }`}
                        >
                          {member.position}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                          <Mail className="w-4 h-4" />
                          {member.email}
                        </div>
                        {member.phone && (
                          <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            <Phone className="w-4 h-4" />
                            {member.phone}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                      {member.term_start_date && !isNaN(new Date(member.term_start_date).getTime())
                        ? new Date(member.term_start_date).toLocaleDateString()
                        : '—'}
                    </td>
                    {isAdmin && (
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setEditingMember(member)}
                            className="p-2 hover:bg-earth-100 dark:bg-earth-800/30 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
                            aria-label={`Edit member ${member.full_name}`}
                          >
                            <Edit2 className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                          </button>
                          <button
                            onClick={() =>
                              setDeleteConfirm({
                                id: member.id,
                                name: `${member.full_name}`,
                              })
                            }
                            className="p-2 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                            aria-label={`Remove member ${member.full_name}`}
                          >
                            <Trash2 className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Forms */}
      {(showForm || editingMember) && isAdmin && (
        <BoardMemberForm
          member={editingMember}
          onSubmit={editingMember ? handleUpdateMember : handleAddMember}
          onCancel={() => {
            setShowForm(false)
            setEditingMember(null)
          }}
          loading={submitting}
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Remove Board Member?"
        message={`Are you sure you want to remove ${deleteConfirm?.name} from the board? This action cannot be undone.`}
        confirmText="Remove"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={handleDeleteMember}
        onCancel={() => setDeleteConfirm(null)}
        loading={submitting}
      />
    </div>
  )
}