/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import toast from 'react-hot-toast';
import {
  getPendingFocusTimeApprovals,
  approveFocusTimeRequest,
  rejectFocusTimeRequest,
  getFocusTimeBlock,
  FocusTimeApproval,
} from '@/api/focus-time-api'
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'

interface ApprovalWithDetails extends FocusTimeApproval {
  staff_name?: string
  work_type?: string
  start_time?: string
  end_time?: string
  description?: string
}

export const FocusTimeApprovalDashboard: React.FC = () => {
  const { t } = useTranslation()
  const [selectedApprovalId, setSelectedApprovalId] = useState<number | null>(null)
  const [decisionComment, setDecisionComment] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<'approve' | 'reject' | null>(null)
  const [approvalDetails, setApprovalDetails] = useState<ApprovalWithDetails | null>(null)

  // Fetch pending approvals
  const { data: approvalsData, refetch: refetchApprovals } = useQuery({
    queryKey: ['pendingFocusTimeApprovals'],
    queryFn: getPendingFocusTimeApprovals,
    staleTime: 1000 * 60 * 2, // 2 minutes
  })

  // Approve mutation
  const approveMutation = useMutation({
    mutationFn: (approvalId: number) =>
      approveFocusTimeRequest(approvalId, clean({
        decision_comment: decisionComment || undefined,
      })),
    onSuccess: () => {
      toast.success(t('components.staff.focusTimeApprovalDashboard.focusTimeRequestApprovedSuccessfully'))
      setDecisionComment('')
      setSelectedApprovalId(null)
      setIsModalOpen(false)
      setPendingAction(null)
      refetchApprovals()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staff.failedToApproveFocusTime'))
    },
  })

  // Reject mutation
  const rejectMutation = useMutation({
    mutationFn: (approvalId: number) =>
      rejectFocusTimeRequest(approvalId, decisionComment),
    onSuccess: () => {
      toast.success(t('components.staff.focusTimeApprovalDashboard.focusTimeRequestRejected'))
      setDecisionComment('')
      setSelectedApprovalId(null)
      setIsModalOpen(false)
      setPendingAction(null)
      refetchApprovals()
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.staff.failedToRejectFocusTime'))
    },
  })

  const handleOpenApprovalModal = async (
    approval: FocusTimeApproval,
    action: 'approve' | 'reject'
  ) => {
    setSelectedApprovalId(approval.id)
    setPendingAction(action)
    setIsModalOpen(true)
    setDecisionComment('')

    // Fetch block details
    try {
      const blockDetails = await getFocusTimeBlock(approval.focus_block_id)
      if (blockDetails.block) {
        const details: ApprovalWithDetails = {
          ...approval,
          work_type: blockDetails.block.work_type as string,
          start_time: blockDetails.block.start_time,
          end_time: blockDetails.block.end_time,
          ...(blockDetails.block.description != null ? { description: blockDetails.block.description } : {}),
        }
        setApprovalDetails(details)
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }

  const handleSubmitDecision = () => {
    if (!selectedApprovalId || !pendingAction) return

    if (pendingAction === 'reject' && !decisionComment.trim()) {
      toast.error(t('components.staff.focusTimeApprovalDashboard.pleaseProvideAReasonFor'))
      return
    }

    if (pendingAction === 'approve') {
      approveMutation.mutate(selectedApprovalId)
    } else {
      rejectMutation.mutate(selectedApprovalId)
    }
  }

  const approvals = approvalsData?.pending_approvals || []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-serif font-bold mb-2">{t('components.staff.focusTimeApprovalDashboard.focusTimeApprovalQueue')}</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Review and approve focus time requests from your team members
        </p>
      </div>

      {approvals.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-status-success-600 mx-auto mb-2" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.focusTimeApprovalDashboard.noPendingFocusTimeApprovals')}</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-serif font-semibold text-earth-900 dark:text-lsc-rose-light/80">
                {approvals.length} pending request{approvals.length !== 1 ? 's' : ''}
              </h3>
              <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
                Review each request and approve or reject with appropriate feedback
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {approvals.map((approval) => (
              <Card key={approval.id} className="hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <div className="space-y-4">
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="secondary">PENDING</Badge>
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            Requested{' '}
                            {approval.requested_at
                              ? new Date(approval.requested_at).toLocaleDateString()
                              : 'Unknown'}
                          </span>
                        </div>
                        {approval.expires_at && (
                          <div className="flex items-center gap-1 text-sm text-status-warning-800 dark:text-status-warning-400 mt-1">
                            <Clock className="w-4 h-4" />
                            Expires{' '}
                            {new Date(approval.expires_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Details */}
                    <div className="bg-earth-50 dark:bg-earth-900 rounded p-3 space-y-2">
                      {approvalDetails?.start_time && (
                        <div className="text-sm">
                          <span className="font-semibold">Time:</span>{' '}
                          {new Date(approvalDetails.start_time).toLocaleString()} -
                          {new Date(approvalDetails.end_time!).toLocaleTimeString()}
                        </div>
                      )}
                      {approvalDetails?.work_type && (
                        <div className="text-sm">
                          <span className="font-semibold">Work Type:</span>{' '}
                          {approvalDetails.work_type}
                        </div>
                      )}
                      {approvalDetails?.description && (
                        <div className="text-sm">
                          <span className="font-semibold">Description:</span>{' '}
                          {approvalDetails.description}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-2">
                      <Button
                        onClick={() => handleOpenApprovalModal(approval, 'approve')}
                        className="bg-status-success-600 hover:bg-status-success-700 flex-1"
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Approve
                      </Button>
                      <Button
                        onClick={() => handleOpenApprovalModal(approval, 'reject')}
                        variant="outline"
                        className="flex-1"
                      >
                        <XCircle className="w-4 h-4 mr-2" />
                        Reject
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Decision Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {pendingAction === 'approve' ? 'Approve Focus Time' : 'Reject Focus Time'}
            </DialogTitle>
            <DialogDescription>
              {pendingAction === 'approve'
                ? 'This staff member will be able to protect their focus time with this approval.'
                : 'Provide feedback on why this focus time cannot be approved.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Block Details */}
            {approvalDetails && (
              <div className="bg-earth-50 dark:bg-earth-900 rounded p-3 space-y-2 text-sm">
                {approvalDetails.start_time && (
                  <div>
                    <span className="font-semibold">Time:</span>{' '}
                    {new Date(approvalDetails.start_time).toLocaleString()}
                  </div>
                )}
                {approvalDetails.work_type && (
                  <div>
                    <span className="font-semibold">Work Type:</span> {approvalDetails.work_type}
                  </div>
                )}
              </div>
            )}

            {/* Comment */}
            <div className="space-y-2">
              <Label htmlFor="decision_comment">
                {pendingAction === 'approve'
                  ? 'Comment (optional)'
                  : 'Reason for rejection *'}
              </Label>
              <Textarea
                id="decision_comment"
                placeholder={
                  pendingAction === 'approve'
                    ? 'Add any notes for the staff member...'
                    : 'Explain why this focus time cannot be approved...'
                }
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {pendingAction === 'approve' ? (
              <Button
                onClick={handleSubmitDecision}
                disabled={approveMutation.isPending}
                className="bg-status-success-600 hover:bg-status-success-700 flex-1"
              >
                {approveMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 motion-safe:animate-spin" />
                    Approving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 mr-2" />
                    Approve
                  </>
                )}
              </Button>
            ) : (
              <Button
                onClick={handleSubmitDecision}
                disabled={rejectMutation.isPending || !decisionComment.trim()}
                variant="danger"
                className="flex-1"
              >
                {rejectMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 motion-safe:animate-spin" />
                    Rejecting...
                  </>
                ) : (
                  <>
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </>
                )}
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => setIsModalOpen(false)}
              disabled={approveMutation.isPending || rejectMutation.isPending}
            >
              Cancel
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
