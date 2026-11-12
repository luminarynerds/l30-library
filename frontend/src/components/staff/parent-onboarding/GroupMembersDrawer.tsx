/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Right-side drawer listing active + waitlisted members of a connection
 * group, with a per-row remove action that requires picking a reason from a
 * fixed enum. Implemented as a Modal (size=xl) rather than a true drawer to
 * reuse the focus-trap + escape-handling we already ship; the visual diff is
 * minor and the a11y benefits are real.
 */
import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Loader2, Trash2, AlertTriangle } from 'lucide-react'

import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  listConnectionGroupMembers,
  removeConnectionGroupMember,
  type GroupMemberDetail,
  type ParentConnectionGroup,
  type RemovalReason,
} from '@/api/parent-onboarding-api'

const REMOVAL_REASONS: RemovalReason[] = [
  'patron_request',
  'attendance_lapse',
  'safety',
  'program_ended',
  'other',
]

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

const REDACTED_CTX = {
  tags: { group_type: '[redacted]' },
  extra: { group_id: '[redacted]' },
} as const

interface Props {
  group: ParentConnectionGroup
  isOpen: boolean
  onClose: () => void
}

export function GroupMembersDrawer({ group, isOpen, onClose }: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['connection-group-members', group.id],
    queryFn: () => listConnectionGroupMembers(group.id),
    enabled: isOpen,
  })

  const [pendingPatronId, setPendingPatronId] = useState<number | null>(null)
  const [reason, setReason] = useState<RemovalReason>('patron_request')

  const removeMutation = useMutation({
    mutationFn: (vars: { patronId: number; reason: RemovalReason }) =>
      removeConnectionGroupMember(group.id, vars.patronId, vars.reason),
    onSuccess: (_void, vars) => {
      queryClient.invalidateQueries({ queryKey: ['connection-group-members', group.id] })
      queryClient.invalidateQueries({ queryKey: ['connection-groups'] })
      const patronName = displayNameById(data?.members ?? [], vars.patronId)
      toast.success(
        t('parentOnboarding.connectionGroups.members.removeSuccess', { patronName }),
      )
      setPendingPatronId(null)
    },
    onError: (err: unknown) => {
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.members.removeFailure'))
    },
  })

  const active = useMemo(
    () => (data?.members ?? []).filter(m => m.status === 'active'),
    [data],
  )
  const waitlisted = useMemo(
    () => (data?.members ?? []).filter(m => m.status === 'waitlisted'),
    [data],
  )

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.members.drawerTitle', {
        groupName: group.name,
      })}
      size="xl"
    >
      {isLoading && (
        <div className="flex items-center justify-center py-10">
          <Loader2
            className="w-6 h-6 motion-safe:animate-spin text-lsc-rose"
            role="status"
            aria-label={t(
              'parentOnboarding.connectionGroups.pageStrings.loadingLabel',
            )}
          />
        </div>
      )}

      {error && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-3 text-sm flex items-center gap-2">
          <AlertTriangle
            className="w-4 h-4 text-status-danger-500"
            aria-hidden="true"
          />
          {t('parentOnboarding.connectionGroups.members.removeFailure')}
        </div>
      )}

      {!isLoading && !error && (data?.members?.length ?? 0) === 0 && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-6 text-center">
          {t('parentOnboarding.connectionGroups.members.empty')}
        </p>
      )}

      {!isLoading && !error && (data?.members?.length ?? 0) > 0 && (
        <div className="space-y-4">
          <Section
            heading={t(
              'parentOnboarding.connectionGroups.members.activeHeading',
            )}
            rows={active}
            t={t}
            pendingPatronId={pendingPatronId}
            setPendingPatronId={setPendingPatronId}
            reason={reason}
            setReason={setReason}
            onConfirm={(patronId) =>
              removeMutation.mutate({ patronId, reason })
            }
            isRemoving={removeMutation.isPending}
          />
          <Section
            heading={t(
              'parentOnboarding.connectionGroups.members.waitlistedHeading',
            )}
            rows={waitlisted}
            t={t}
            pendingPatronId={pendingPatronId}
            setPendingPatronId={setPendingPatronId}
            reason={reason}
            setReason={setReason}
            onConfirm={(patronId) =>
              removeMutation.mutate({ patronId, reason })
            }
            isRemoving={removeMutation.isPending}
          />
        </div>
      )}

      <div className="flex justify-end pt-4">
        <button
          type="button"
          onClick={onClose}
          className={`px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
        >
          {t('parentOnboarding.connectionGroups.members.close')}
        </button>
      </div>
    </Modal>
  )
}

interface SectionProps {
  heading: string
  rows: GroupMemberDetail[]
  t: (key: string, opts?: Record<string, unknown>) => string
  pendingPatronId: number | null
  setPendingPatronId: (id: number | null) => void
  reason: RemovalReason
  setReason: (r: RemovalReason) => void
  onConfirm: (patronId: number) => void
  isRemoving: boolean
}

function Section({
  heading,
  rows,
  t,
  pendingPatronId,
  setPendingPatronId,
  reason,
  setReason,
  onConfirm,
  isRemoving,
}: SectionProps) {
  if (rows.length === 0) return null
  return (
    <div>
      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        {heading}
      </h3>
      <ul className="space-y-1" data-testid={`members-section-${heading}`}>
        {rows.map((m) => {
          const isPending = pendingPatronId === m.patron_id
          return (
            <li
              key={m.id}
              className="border border-lsc-border dark:border-earth-700 rounded-lg p-3"
            >
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="text-sm text-lsc-dark dark:text-lsc-cream">
                  <div className="font-medium">
                    {m.patron_name || `#${m.patron_id}`}
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {m.joined_date} · {m.attendance_count}{' '}
                  </div>
                </div>
                {!isPending ? (
                  <button
                    type="button"
                    onClick={() => setPendingPatronId(m.patron_id)}
                    data-testid="members-remove-trigger"
                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-status-danger-50 hover:text-status-danger-600 hover:border-status-danger-200 dark:hover:bg-status-danger-900/20 dark:hover:text-status-danger-400 ${FOCUS_RING}`}
                  >
                    <Trash2 className="w-3 h-3" aria-hidden="true" />
                    {t('parentOnboarding.connectionGroups.members.removeButton')}
                  </button>
                ) : null}
              </div>
              {isPending && (
                <div
                  className="mt-2 space-y-2 text-sm"
                  data-testid="members-remove-form"
                >
                  <p className="text-lsc-dark dark:text-lsc-cream">
                    {t(
                      'parentOnboarding.connectionGroups.members.removeConfirm',
                      { patronName: m.patron_name || `#${m.patron_id}` },
                    )}
                  </p>
                  <label className="block">
                    <span className="block text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {t(
                        'parentOnboarding.connectionGroups.members.removeReasonLabel',
                      )}
                    </span>
                    <select
                      value={reason}
                      onChange={(e) => setReason(e.target.value as RemovalReason)}
                      data-testid="members-remove-reason"
                      className={`w-full px-2 py-1 text-sm rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
                    >
                      {REMOVAL_REASONS.map((r) => (
                        <option key={r} value={r}>
                          {t(
                            `parentOnboarding.connectionGroups.members.reason.${r}`,
                          )}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => onConfirm(m.patron_id)}
                      disabled={isRemoving}
                      data-testid="members-remove-confirm"
                      className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-lg bg-status-danger-500 text-white hover:bg-status-danger-600 disabled:opacity-50 ${FOCUS_RING}`}
                    >
                      {isRemoving && (
                        <Loader2
                          className="w-3 h-3 motion-safe:animate-spin"
                          aria-hidden="true"
                        />
                      )}
                      {t('parentOnboarding.connectionGroups.members.removeButton')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setPendingPatronId(null)}
                      className={`px-2 py-1 text-xs rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
                    >
                      {t('parentOnboarding.connectionGroups.enroll.cancel')}
                    </button>
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function displayNameById(rows: GroupMemberDetail[], patronId: number): string {
  const row = rows.find((r) => r.patron_id === patronId)
  return row?.patron_name || `#${patronId}`
}

export default GroupMembersDrawer
