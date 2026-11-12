/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import {
  Flag,
  AlertOctagon,
  X,
  Check,
  Info,
  Loader2,
  CheckCircle,
  XCircle,
} from "lucide-react"
import {
  ContentFlag,
  FlagsFeedback,
} from "../../api/contentFlagService"
import { useTranslation } from '@/i18n'
import { getStatusConfig, getFlagTypeConfig } from './FlagConfig'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface FlagDetailModalProps {
  flag: ContentFlag | null
  onClose: () => void
  onResolve: (flagId: number, feedback: FlagsFeedback) => Promise<void>
  onModerateReview: (reviewId: number, action: "approve" | "reject" | "remove", reason?: string) => Promise<void>
  onEditReview: (reviewId: number, comment: string, reason?: string) => Promise<void>
}

// eslint-disable-next-line complexity
export default function FlagDetailModal({ flag, onClose, onResolve, onModerateReview, onEditReview }: FlagDetailModalProps) {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [resolution, setResolution] = useState<"resolved" | "false_positive" | "false_negative">("resolved")
  const [isCorrectFlag, setIsCorrectFlag] = useState(true)
  const [resolutionNotes, setResolutionNotes] = useState("")
  const [staffFeedback, setStaffFeedback] = useState("")
  const [isActionSubmitting, setIsActionSubmitting] = useState(false)
  const [actionReason, setActionReason] = useState("")
  const [isEditing, setIsEditing] = useState(false)
  const [editedComment, setEditedComment] = useState("")

  useEffect(() => {
    if (flag?.review_content?.comment !== undefined) {
      setEditedComment(flag.review_content.comment || "")
    } else {
      setEditedComment("")
    }
    setActionReason("")
    setIsEditing(false)
  }, [flag])

  if (!flag) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await onResolve(flag.id, {
        status: resolution,
        is_correct_flag: isCorrectFlag,
        ...(resolutionNotes && { resolution_notes: resolutionNotes }),
        ...(staffFeedback && { staff_feedback: staffFeedback }),
      })
      onClose()
    } catch (_error: unknown) {
      // Error handled in parent
    } finally {
      setIsSubmitting(false)
    }
  }

  const statusConfig = getStatusConfig(flag.status)
  const flagTypeConfig = getFlagTypeConfig(flag.flag_type)
  const hasEventReview = flag.review_type === "event_review" && flag.review_content
  const analysisSummary =
    typeof flag.analysis_details?.summary === "string" ? flag.analysis_details.summary : null

  const handleModerationAction = async (action: "approve" | "reject" | "remove") => {
    if (!flag.review_id || !hasEventReview) return
    setIsActionSubmitting(true)
    try {
      await onModerateReview(flag.review_id, action, actionReason ? actionReason : undefined)
      setIsEditing(false)
    } catch (_error: unknown) {
      // Error handled in parent
    } finally {
      setIsActionSubmitting(false)
    }
  }

  const handleEditSubmit = async () => {
    if (!flag.review_id || !hasEventReview) return
    setIsActionSubmitting(true)
    try {
      await onEditReview(flag.review_id, editedComment, actionReason ? actionReason : undefined)
      setIsEditing(false)
    } catch (_error: unknown) {
      // Error handled in parent
    } finally {
      setIsActionSubmitting(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Flag Details">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl flex items-center justify-center">
              <Flag className="w-5 h-5 text-lsc-rose" />
            </div>
            <div>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Flag Details</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Review ID: {flag.review_id} | {flag.review_type.replace("_", " ")}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label={t('aria.flagDetailModal.close', 'Close')}
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors"
          >
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="flex flex-wrap gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${statusConfig.bg} ${statusConfig.text}`}>
              {statusConfig.icon}
              {flag.status.replace("_", " ")}
            </span>
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium text-white ${flagTypeConfig.color}`}>
              {flagTypeConfig.label}
            </span>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
              Score: {flag.confidence_score}%
            </span>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">AI Confidence Score</span>
              <span className={`text-sm font-bold ${
                flag.confidence_score >= 90 ? "text-status-danger-600 dark:text-status-danger-400" :
                flag.confidence_score >= 70 ? "text-status-warning-600 dark:text-status-warning-400" :
                "text-status-success-600 dark:text-status-success-400"
              }`}>
                {flag.confidence_score}%
              </span>
            </div>
            <div className="h-3 bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  flag.confidence_score >= 90 ? "bg-status-danger-500" :
                  flag.confidence_score >= 70 ? "bg-status-warning-500" :
                  "bg-status-success-500"
                }`}
                style={{ width: `${flag.confidence_score}%` }}
              />
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Flag Reason</h3>
            <div className="bg-lsc-cream/50 dark:bg-earth-700 rounded-xl p-4 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{flagTypeConfig.label}</p>
              {analysisSummary && (
                <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{analysisSummary}</p>
              )}
            </div>
          </div>

          {flag.analysis_details && Object.keys(flag.analysis_details).length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">AI Analysis Details</h3>
              <div className="bg-lsc-cream/50 dark:bg-earth-700 rounded-xl p-4">
                <pre className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(flag.analysis_details, null, 2)}
                </pre>
              </div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Review Content</h3>
            {hasEventReview ? (
              <div className="bg-lsc-cream/50 dark:bg-earth-700 rounded-xl p-4 space-y-3">
                <div className="flex flex-wrap items-center gap-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                  <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                    {flag.review_content?.event_title || "Event"}
                  </span>
                  {flag.review_content?.rating !== null && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-xs">
                      Rating: {flag.review_content?.rating}
                    </span>
                  )}
                  {flag.review_content?.moderation_status && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-xs">
                      Status: {flag.review_content.moderation_status}
                    </span>
                  )}
                  {flag.review_content?.is_removed === 1 && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 text-xs">
                      Removed
                    </span>
                  )}
                </div>
                <div className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
                  {flag.review_content?.comment || "No comment provided."}
                </div>
                {flag.review_content?.patron_email && (
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    Patron: {flag.review_content.patron_email}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-lsc-cream/50 dark:bg-earth-700 rounded-xl p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Review details are not available for this content type.
              </div>
            )}
          </div>

          {hasEventReview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Moderation Actions</h3>
                <button
                  type="button"
                  onClick={() => setIsEditing((prev) => !prev)}
                  className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  {isEditing ? "Cancel edit" : "Edit comment"}
                </button>
              </div>
              {isEditing && (
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Edited comment</label>
                  <textarea
                    value={editedComment}
                    onChange={(e) => setEditedComment(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Action reason (optional)
                </label>
                <input
                  type="text"
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder={t('staffContentFlags.provideContextForYourAction')}
                  className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleModerationAction("approve")}
                  disabled={isActionSubmitting}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-status-success-500 text-white text-sm font-medium hover:bg-status-success-600 disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => handleModerationAction("remove")}
                  disabled={isActionSubmitting}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-status-danger-500 text-white text-sm font-medium hover:bg-status-danger-600 disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Remove
                </button>
                {isEditing && (
                  <button
                    type="button"
                    onClick={handleEditSubmit}
                    disabled={isActionSubmitting || editedComment.trim().length === 0}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    Save Edit
                  </button>
                )}
              </div>
            </div>
          )}

          {flag.resolved_by && (
            <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
              <h3 className="text-sm font-medium text-earth-800 dark:text-lsc-rose-light/80 mb-2 flex items-center gap-2">
                <Info className="w-4 h-4" />
                Previous Resolution
              </h3>
              <div className="space-y-1 text-sm text-lsc-rose dark:text-lsc-rose-light">
                <p><strong>Resolved by:</strong> {flag.resolved_by}</p>
                {flag.resolved_at && (
                  <p><strong>Resolved at:</strong> {new Date(flag.resolved_at).toLocaleString()}</p>
                )}
                {flag.resolution_notes && <p><strong>Notes:</strong> {flag.resolution_notes}</p>}
                {flag.staff_feedback && <p><strong>Staff feedback:</strong> {flag.staff_feedback}</p>}
              </div>
            </div>
          )}

          {flag.status === "pending" && (
            <form onSubmit={handleSubmit} className="space-y-4 pt-4 border-t border-lsc-border dark:border-earth-700">
              <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Resolve this Flag</h3>

              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Resolution Type
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => { setResolution("resolved"); setIsCorrectFlag(true); }}
                    className={`p-3 rounded-xl border-2 transition-colors text-left ${
                      resolution === "resolved"
                        ? "border-status-success-500 bg-status-success-50 dark:bg-status-success-900/20"
                        : "border-lsc-border dark:border-earth-700 hover:border-lsc-rose"
                    }`}
                  >
                    <CheckCircle className={`w-5 h-5 mb-1 ${resolution === "resolved" ? "text-status-success-600 dark:text-status-success-400" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`} />
                    <p className={`text-sm font-medium ${resolution === "resolved" ? "text-status-success-700 dark:text-status-success-300" : "text-lsc-dark dark:text-lsc-cream"}`}>Resolved</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Flag was correct</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => { setResolution("false_positive"); setIsCorrectFlag(false); }}
                    className={`p-3 rounded-xl border-2 transition-colors text-left ${
                      resolution === "false_positive"
                        ? "border-lsc-rose/50 bg-earth-50 dark:bg-earth-800/20"
                        : "border-lsc-border dark:border-earth-700 hover:border-lsc-rose"
                    }`}
                  >
                    <XCircle className={`w-5 h-5 mb-1 ${resolution === "false_positive" ? "text-lsc-rose dark:text-lsc-rose-light" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`} />
                    <p className={`text-sm font-medium ${resolution === "false_positive" ? "text-lsc-rose dark:text-lsc-rose-light" : "text-lsc-dark dark:text-lsc-cream"}`}>False Positive</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Incorrect flag</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => { setResolution("false_negative"); setIsCorrectFlag(false); }}
                    className={`p-3 rounded-xl border-2 transition-colors text-left ${
                      resolution === "false_negative"
                        ? "border-status-danger-500 bg-status-danger-50 dark:bg-status-danger-900/20"
                        : "border-lsc-border dark:border-earth-700 hover:border-lsc-rose"
                    }`}
                  >
                    <AlertOctagon className={`w-5 h-5 mb-1 ${resolution === "false_negative" ? "text-status-danger-600 dark:text-status-danger-400" : "text-lsc-dark/70 dark:text-lsc-cream/70"}`} />
                    <p className={`text-sm font-medium ${resolution === "false_negative" ? "text-status-danger-700 dark:text-status-danger-300" : "text-lsc-dark dark:text-lsc-cream"}`}>False Negative</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Missed issue</p>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Resolution Notes (Optional)
                </label>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder={t('staffContentFlags.addNotesAboutHowThis')}
                  rows={2}
                  className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  Feedback for AI Model (Optional)
                </label>
                <textarea
                  value={staffFeedback}
                  onChange={(e) => setStaffFeedback(e.target.value)}
                  placeholder={t('staffContentFlags.provideFeedbackToImproveThe')}
                  rows={2}
                  className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Resolve Flag
                </button>
              </div>
            </form>
          )}

          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 pt-4 border-t border-lsc-border dark:border-earth-700">
            <p>Created: {new Date(flag.created_at).toLocaleString()}</p>
            <p>Updated: {new Date(flag.updated_at).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
