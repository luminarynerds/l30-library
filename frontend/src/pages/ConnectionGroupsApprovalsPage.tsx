/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Cross-group pending-approval queue for confidential connection groups.
 * Facilitator + admin only (server-enforced; route is in StaffRoutes).
 *
 * v1 fetches each confidential group's approval queue serially based on the
 * /connection-groups list. A purpose-built cross-group endpoint is deferred
 * (out of scope per spec); this keeps the surface small while exercising the
 * 3 new backend endpoints together.
 */
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Check, Loader2, MessageSquare, X } from 'lucide-react'

import { AdminShell } from '../components/shells/AdminShell'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  decideApprovalRequest,
  getApprovalQueue,
  listConnectionGroups,
  type ApprovalQueueEntry,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'

const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

function badgeForDays(days: number): { label: string; cls: string } {
  if (days >= 4) {
    return { label: `${days}d`, cls: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/40 dark:text-status-danger-300' }
  }
  if (days >= 2) {
    return { label: `${days}d`, cls: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/40 dark:text-status-warning-300' }
  }
  return { label: `${days}d`, cls: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-200' }
}

export default function ConnectionGroupsApprovalsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [decisionFor, setDecisionFor] = useState<{
    entry: ApprovalQueueEntry
    decision: 'approve' | 'deny'
  } | null>(null)
  const [decisionNote, setDecisionNote] = useState('')
  const [patronMessage, setPatronMessage] = useState('')

  const groupsQuery = useQuery({
    queryKey: ['connection-groups', { confidentialOnly: true }],
    queryFn: () => listConnectionGroups(),
  })

  const confidentialGroups: ParentConnectionGroup[] = useMemo(
    () => (groupsQuery.data?.groups ?? []).filter(g => g.confidential === true),
    [groupsQuery.data?.groups],
  )

  const queueQueries = useQueries({
    queries: confidentialGroups.map(g => ({
      queryKey: ['approval-queue', g.id],
      queryFn: () => getApprovalQueue(g.id),
    })),
  })

  const pendingFlat: ApprovalQueueEntry[] = useMemo(() => {
    const out: ApprovalQueueEntry[] = []
    queueQueries.forEach(q => {
      if (q.data?.pending) out.push(...q.data.pending)
    })
    // Oldest first across all groups.
    out.sort((a, b) => a.requested_at.localeCompare(b.requested_at))
    return out
  }, [queueQueries])

  const decideMutation = useMutation({
    mutationFn: ({
      groupId,
      memberId,
      decision,
      note,
      message,
    }: {
      groupId: number
      memberId: number
      decision: 'approve' | 'deny'
      note: string
      message: string
    }) =>
      decideApprovalRequest(groupId, memberId, {
        decision,
        decision_note: note.trim() || undefined,
        patron_message: message.trim() || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-queue'] })
      toast.success(t('connectionGroups.approvalQueue.decisionSaved'))
      setDecisionFor(null)
      setDecisionNote('')
      setPatronMessage('')
    },
    onError: () => {
      toast.error(t('connectionGroups.approvalQueue.decisionFailed'))
    },
  })

  const loading = groupsQuery.isLoading
  const error = groupsQuery.error ? String(groupsQuery.error) : null

  return (
    <AdminShell
      title={t('connectionGroups.approvalQueue.title')}
      loading={loading}
      error={error}
    >
      <section
        role="region"
        aria-label={t('connectionGroups.approvalQueue.title')}
        data-testid="conngroups-approvals-page"
      >
        {pendingFlat.length === 0 ? (
          <p
            className="text-sm text-lsc-dark/85 dark:text-lsc-cream/85"
            data-testid="conngroups-approvals-empty"
          >
            {t('connectionGroups.approvalQueue.empty')}
          </p>
        ) : (
          <ul role="list" className="space-y-3 list-none p-0">
            {pendingFlat.map(entry => {
              const badge = badgeForDays(entry.days_pending)
              return (
                <li
                  key={`${entry.group_id}-${entry.id}`}
                  data-testid="conngroups-approval-entry"
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        {entry.patron_name || `Patron #${entry.patron_id}`}
                      </p>
                      <p className="text-xs text-lsc-dark/85 dark:text-lsc-cream/85">
                        {entry.group_name}
                      </p>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${badge.cls}`}
                      data-testid="conngroups-days-pending"
                    >
                      {t('connectionGroups.approvalQueue.daysPending', {
                        days: entry.days_pending,
                      })}
                    </span>
                  </div>
                  {entry.request_message && (
                    <p className="text-xs text-lsc-dark dark:text-lsc-cream mb-2 flex items-start gap-1">
                      <MessageSquare className="w-3 h-3 mt-0.5" aria-hidden="true" />
                      <span>{entry.request_message}</span>
                    </p>
                  )}
                  {entry.patron_contact_visible ? (
                    <p
                      className="text-xs text-lsc-dark/85 dark:text-lsc-cream/85 mb-2"
                      data-testid="conngroups-approval-contact"
                    >
                      {entry.patron_email}
                      {entry.patron_phone ? ` / ${entry.patron_phone}` : ''}
                    </p>
                  ) : (
                    <p
                      className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 italic mb-2"
                      data-testid="conngroups-approval-contact-hidden"
                    >
                      {t('connectionGroups.approvalQueue.contactHidden')}
                    </p>
                  )}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setDecisionFor({ entry, decision: 'approve' })
                        setDecisionNote('')
                        setPatronMessage('')
                      }}
                      data-testid="conngroups-approve"
                      className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 ${FOCUS_RING}`}
                    >
                      <Check className="w-3.5 h-3.5" aria-hidden="true" />
                      {t('connectionGroups.approvalQueue.approve')}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setDecisionFor({ entry, decision: 'deny' })
                        setDecisionNote('')
                        setPatronMessage('')
                      }}
                      data-testid="conngroups-deny"
                      className={`inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-status-danger-700 dark:text-status-danger-300 hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
                    >
                      <X className="w-3.5 h-3.5" aria-hidden="true" />
                      {t('connectionGroups.approvalQueue.deny')}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {decisionFor && (
        <Modal
          isOpen={decisionFor !== null}
          onClose={() => setDecisionFor(null)}
          title={
            decisionFor.decision === 'approve'
              ? t('connectionGroups.approvalQueue.approveTitle')
              : t('connectionGroups.approvalQueue.denyTitle')
          }
        >
          <form
            onSubmit={e => {
              e.preventDefault()
              decideMutation.mutate({
                groupId: decisionFor.entry.group_id,
                memberId: decisionFor.entry.id,
                decision: decisionFor.decision,
                note: decisionNote,
                message: patronMessage,
              })
            }}
            className="space-y-3"
            data-testid="conngroups-decision-dialog"
          >
            <div>
              <label
                htmlFor="decision-note"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                {t('connectionGroups.approvalQueue.decisionNoteLabel')}
              </label>
              <textarea
                id="decision-note"
                value={decisionNote}
                onChange={e => setDecisionNote(e.target.value)}
                maxLength={1000}
                rows={2}
                className={`w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
              />
            </div>
            <div>
              <label
                htmlFor="patron-message"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                {t('connectionGroups.approvalQueue.patronMessageLabel')}
              </label>
              <textarea
                id="patron-message"
                value={patronMessage}
                onChange={e => setPatronMessage(e.target.value)}
                maxLength={1000}
                rows={3}
                className={`w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream ${FOCUS_RING}`}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDecisionFor(null)}
                className={`px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
              >
                {t('parentOnboarding.connectionGroups.enroll.cancel')}
              </button>
              <button
                type="submit"
                disabled={decideMutation.isPending}
                data-testid="conngroups-decision-submit"
                className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 ${FOCUS_RING}`}
              >
                {decideMutation.isPending && (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                )}
                {decisionFor.decision === 'approve'
                  ? t('connectionGroups.approvalQueue.approve')
                  : t('connectionGroups.approvalQueue.deny')}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </AdminShell>
  )
}
