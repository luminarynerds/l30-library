/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import FocusTrap from 'focus-trap-react'
import { AlertTriangle, Loader2, X as CloseIcon } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  listConnectionGroupMeetings,
  type GroupMeeting,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'
import { CancelMeetingDialog } from './CancelMeetingDialog'
import { RescheduleMeetingDialog } from './RescheduleMeetingDialog'
import { FOCUS_RING } from './shared'

interface MeetingsProps {
  group: ParentConnectionGroup
  isOpen: boolean
  onClose: () => void
}

export function MeetingsDrawer({ group, isOpen, onClose }: MeetingsProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [cancelFor, setCancelFor] = useState<GroupMeeting | null>(null)
  const [rescheduleFor, setRescheduleFor] = useState<GroupMeeting | null>(null)

  const meetingsQuery = useQuery({
    queryKey: ['connection-group-meetings', group.id],
    queryFn: () => listConnectionGroupMeetings(group.id),
    enabled: isOpen,
  })

  const meetings = meetingsQuery.data?.meetings ?? []

  const closeAllDialogs = () => {
    setCancelFor(null)
    setRescheduleFor(null)
  }

  const refreshMeetings = () => {
    queryClient.invalidateQueries({
      queryKey: ['connection-group-meetings', group.id],
    })
  }

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('parentOnboarding.connectionGroups.admin.meetings.drawerTitle', {
        groupName: group.name,
      })}
      className="fixed inset-0 z-50 flex"
      data-testid="cg-meetings-drawer"
    >
      <div
        className="flex-1 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <FocusTrap
        focusTrapOptions={{
          escapeDeactivates: false,
          allowOutsideClick: true,
          returnFocusOnDeactivate: true,
          fallbackFocus: () => document.body,
        }}
      >
      <div className="w-full max-w-2xl bg-lsc-white dark:bg-earth-900 shadow-lg flex flex-col">
        <div className="flex items-start justify-between px-6 py-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('parentOnboarding.connectionGroups.admin.meetings.drawerTitle', {
              groupName: group.name,
            })}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('parentOnboarding.connectionGroups.admin.meetings.close')}
            className={`p-1 rounded ${FOCUS_RING}`}
          >
            <CloseIcon className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {meetingsQuery.isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" role="status" />
            </div>
          ) : meetingsQuery.isError ? (
            <p className="text-status-danger-600">
              <AlertTriangle className="inline w-4 h-4 mr-1" aria-hidden="true" />
              {t('parentOnboarding.connectionGroups.failedToLoad')}
            </p>
          ) : meetings.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('parentOnboarding.connectionGroups.admin.meetings.empty')}
            </p>
          ) : (
            <table className="w-full text-sm" data-testid="cg-meetings-table">
              <thead>
                <tr className="text-left text-xs uppercase text-lsc-dark/60 dark:text-lsc-cream/60 border-b border-lsc-border dark:border-earth-700">
                  <th className="py-2 pr-2">{t('parentOnboarding.connectionGroups.admin.meetings.headerDate')}</th>
                  <th className="py-2 pr-2">{t('parentOnboarding.connectionGroups.admin.meetings.headerTime')}</th>
                  <th className="py-2 pr-2">{t('parentOnboarding.connectionGroups.admin.meetings.headerLocation')}</th>
                  <th className="py-2 pr-2">{t('parentOnboarding.connectionGroups.admin.meetings.headerStatus')}</th>
                  <th className="py-2">{t('parentOnboarding.connectionGroups.admin.meetings.headerActions')}</th>
                </tr>
              </thead>
              <tbody>
                {meetings.map((m) => (
                  <tr
                    key={m.id}
                    className="border-b border-lsc-border/40 dark:border-earth-700/40"
                    data-testid="cg-meeting-row"
                    data-status={m.status}
                  >
                    <td className="py-2 pr-2">{m.meeting_date}</td>
                    <td className="py-2 pr-2">{m.scheduled_time ?? '-'}</td>
                    <td className="py-2 pr-2">{m.location ?? '-'}</td>
                    <td className="py-2 pr-2">
                      <StatusBadge status={m.status} />
                    </td>
                    <td className="py-2">
                      {m.status === 'scheduled' ? (
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setCancelFor(m)}
                            className={`text-xs underline ${FOCUS_RING}`}
                            data-testid="cg-meeting-cancel-action"
                          >
                            {t('parentOnboarding.connectionGroups.admin.meetings.cancelAction')}
                          </button>
                          <button
                            type="button"
                            onClick={() => setRescheduleFor(m)}
                            className={`text-xs underline ${FOCUS_RING}`}
                            data-testid="cg-meeting-reschedule-action"
                          >
                            {t('parentOnboarding.connectionGroups.admin.meetings.rescheduleAction')}
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      </FocusTrap>

      {cancelFor && (
        <CancelMeetingDialog
          group={group}
          meeting={cancelFor}
          isOpen
          onClose={() => closeAllDialogs()}
          onSuccess={() => {
            refreshMeetings()
            closeAllDialogs()
          }}
        />
      )}
      {rescheduleFor && (
        <RescheduleMeetingDialog
          group={group}
          meeting={rescheduleFor}
          isOpen
          onClose={() => closeAllDialogs()}
          onSuccess={() => {
            refreshMeetings()
            closeAllDialogs()
          }}
        />
      )}
    </div>
  )
}
function StatusBadge({ status }: { status: GroupMeeting['status'] }) {
  const { t } = useTranslation()
  const cls = useMemo(() => {
    switch (status) {
      case 'cancelled':
        return 'bg-status-danger-50 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300'
      case 'rescheduled':
        return 'bg-status-warning-50 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300'
      case 'completed':
        return 'bg-sage-100 text-sage-800 dark:bg-sage-900/30 dark:text-sage-300'
      default:
        return 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
    }
  }, [status])
  const label = t(
    `parentOnboarding.connectionGroups.admin.meetings.status${
      status.charAt(0).toUpperCase() + status.slice(1)
    }`,
  )
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
