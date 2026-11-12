/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Users,
  Building2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Play,
  Pause,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../../ConfirmDialog'
import {
  listMembers,
  getMember,
  suspendMember,
  activateMember,
  type ConsortiumDetail,
  type ConsortiumMember,
  type ConsortiumMemberDetail,
} from '../../../api/consortium-api'
import { STATUS_STYLES, MEMBER_TYPE_LABELS } from './StatusBadges'
import { t } from '@/i18n'

function MembersTab({
  token,
  selectedConsortium,
}: {
  token: string | null
  selectedConsortium: ConsortiumDetail | null
}) {
  const [members, setMembers] = useState<ConsortiumMember[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedMemberId, setExpandedMemberId] = useState<number | null>(null)
  const [memberDetails, setMemberDetails] = useState<ConsortiumMemberDetail | null>(null)
  const [actionConfirm, setActionConfirm] = useState<{
    memberId: number
    action: 'suspend' | 'activate'
    name: string
  } | null>(null)

  const loadMembers = useCallback(async () => {
    if (!selectedConsortium) return
    try {
      setLoading(true)
      const data = await listMembers(selectedConsortium.id, { active_only: false })
      setMembers(data)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadMembers'))
    } finally {
      setLoading(false)
    }
  }, [selectedConsortium])

  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  const handleExpandMember = async (memberId: number) => {
    if (expandedMemberId === memberId) {
      setExpandedMemberId(null)
      setMemberDetails(null)
      return
    }
    try {
      const details = await getMember(memberId)
      setMemberDetails(details)
      setExpandedMemberId(memberId)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToLoadMemberDetails'))
    }
  }

  const handleMemberAction = async () => {
    if (!actionConfirm || !token) return
    try {
      if (actionConfirm.action === 'suspend') {
        await suspendMember(token, actionConfirm.memberId)
        toast.success(t('toast.admin.memberSuspended'))
      } else {
        await activateMember(token, actionConfirm.memberId)
        toast.success(t('toast.admin.memberActivated'))
      }
      setActionConfirm(null)
      loadMembers()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.admin.failedToUpdateMember'))
    }
  }

  if (!selectedConsortium) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
        <Users className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          Select a consortium
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Go to the Consortiums tab and select a consortium to manage its members.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Member Libraries
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {selectedConsortium.name} - {members.length} member(s)
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors">
          <span>Add Member</span>
        </button>
      </div>

      {members.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
          <Building2 className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            No members yet
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Add library systems as members of this consortium.
          </p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-lsc-cream/50 dark:bg-earth-700/50 border-b border-lsc-border dark:border-earth-700">
                <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Library System
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Type
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Joined
                </th>
                <th className="px-6 py-4 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <React.Fragment key={member.id}>
                  <tr
                    className="border-b border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors cursor-pointer"
                    onClick={() => handleExpandMember(member.id)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-lsc-rose/10 rounded-lg flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-lsc-rose" />
                        </div>
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            Library System #{member.library_system_id}
                          </p>
                          {member.voting_member && (
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                              Voting Member (weight: {member.vote_weight})
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                        {MEMBER_TYPE_LABELS[member.member_type] || member.member_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[member.status].bg} ${STATUS_STYLES[member.status].text}`}
                      >
                        {member.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {new Date(member.joined_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {member.status === 'active' ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionConfirm({
                                memberId: member.id,
                                action: 'suspend',
                                name: `Library System #${member.library_system_id}`,
                              })
                            }}
                            className="p-2 text-status-warning-600 hover:bg-status-warning-100 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/30 rounded-lg transition-colors"
                            title="Suspend member"
                          >
                            <Pause className="w-4 h-4" />
                          </button>
                        ) : member.status === 'suspended' ? (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setActionConfirm({
                                memberId: member.id,
                                action: 'activate',
                                name: `Library System #${member.library_system_id}`,
                              })
                            }}
                            className="p-2 text-status-success-600 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded-lg transition-colors"
                            title="Activate member"
                          >
                            <Play className="w-4 h-4" />
                          </button>
                        ) : null}
                        <button
                          onClick={(e) => e.stopPropagation()}
                          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
                        >
                          {expandedMemberId === member.id ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedMemberId === member.id && memberDetails && (
                    <tr>
                      <td colSpan={5} className="px-6 py-4 bg-lsc-cream/20 dark:bg-earth-700/20">
                        <div className="grid md:grid-cols-3 gap-6">
                          <div>
                            <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                              Membership Details
                            </h4>
                            <dl className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Annual Fee:</dt>
                                <dd className="text-lsc-dark dark:text-lsc-cream">
                                  {member.annual_fee ? `$${member.annual_fee}` : 'N/A'}
                                </dd>
                              </div>
                              <div className="flex justify-between">
                                <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Fee Paid Through:</dt>
                                <dd className="text-lsc-dark dark:text-lsc-cream">
                                  {member.fee_paid_through
                                    ? new Date(member.fee_paid_through).toLocaleDateString()
                                    : 'N/A'}
                                </dd>
                              </div>
                              {member.expiry_date && (
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Expires:</dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {new Date(member.expiry_date).toLocaleDateString()}
                                  </dd>
                                </div>
                              )}
                            </dl>
                          </div>
                          {memberDetails.reciprocal_settings && (
                            <div>
                              <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                                Reciprocal Borrowing
                              </h4>
                              <dl className="space-y-1 text-sm">
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                                    Incoming Borrowers:
                                  </dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {memberDetails.reciprocal_settings.allow_incoming_borrowers
                                      ? 'Allowed'
                                      : 'Not Allowed'}
                                  </dd>
                                </div>
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                                    Checkout Limit:
                                  </dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {memberDetails.reciprocal_settings.incoming_checkout_limit}
                                  </dd>
                                </div>
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">
                                    Hold Limit:
                                  </dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {memberDetails.reciprocal_settings.incoming_hold_limit}
                                  </dd>
                                </div>
                              </dl>
                            </div>
                          )}
                          {memberDetails.library_system && (
                            <div>
                              <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                                Library System
                              </h4>
                              <dl className="space-y-1 text-sm">
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Name:</dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {memberDetails.library_system.name}
                                  </dd>
                                </div>
                                <div className="flex justify-between">
                                  <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Code:</dt>
                                  <dd className="text-lsc-dark dark:text-lsc-cream">
                                    {memberDetails.library_system.code}
                                  </dd>
                                </div>
                              </dl>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Action Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!actionConfirm}
        title={actionConfirm?.action === 'suspend' ? 'Suspend Member' : 'Activate Member'}
        message={
          actionConfirm?.action === 'suspend'
            ? `Are you sure you want to suspend ${actionConfirm?.name}? They will lose access to consortium resources.`
            : `Activate ${actionConfirm?.name}? They will regain access to consortium resources.`
        }
        confirmText={actionConfirm?.action === 'suspend' ? 'Suspend' : 'Activate'}
        confirmVariant={actionConfirm?.action === 'suspend' ? 'warning' : 'success'}
        onConfirm={handleMemberAction}
        onCancel={() => setActionConfirm(null)}
      />
    </div>
  )
}

export default MembersTab
