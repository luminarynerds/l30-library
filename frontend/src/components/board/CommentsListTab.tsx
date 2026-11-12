/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  MessageSquare,
  User,
  Eye,
  CheckCircle,
  XCircle,
  FileText,
  Reply,
  Trash2,
} from 'lucide-react'
import type { PublicComment } from '../../api/board-public-comments-api'

interface CommentsListTabProps {
  activeTab: 'pending' | 'approved' | 'rejected'
  displayComments: PublicComment[]
  selectedComment: PublicComment | null
  setSelectedComment: (v: PublicComment | null) => void
  getStatusColor: (status: PublicComment['status']) => string
  getStatusIcon: (status: PublicComment['status']) => React.ReactNode
  getCommentTypeIcon: (type: PublicComment['comment_type']) => React.ReactNode
  onModerateAction: (type: 'approve' | 'reject' | 'read' | 'delete', comment: PublicComment) => void
  onRespond: (comment: PublicComment) => void
}

export function CommentsListTab({
  activeTab,
  displayComments,
  selectedComment,
  setSelectedComment,
  getStatusColor,
  getStatusIcon,
  getCommentTypeIcon,
  onModerateAction,
  onRespond,
}: CommentsListTabProps) {
  return (
    <div className="space-y-4">
      {displayComments.length === 0 ? (
        <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <MessageSquare className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {activeTab === 'pending' ? 'No comments awaiting moderation' :
             activeTab === 'approved' ? 'No approved comments' :
             'No rejected comments'}
          </p>
        </div>
      ) : (
        displayComments.map((comment) => (
          <div
            key={comment.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(comment.status)}`}>
                      {getStatusIcon(comment.status)}
                      {comment.status.replace('_', ' ')}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {getCommentTypeIcon(comment.comment_type)}
                      {comment.comment_type.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {comment.commenter_name}
                    </span>
                    {comment.commenter_email && (
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        ({comment.commenter_email})
                      </span>
                    )}
                    {comment.organization && (
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        - {comment.organization}
                      </span>
                    )}
                  </div>

                  {comment.subject && (
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {comment.subject}
                    </p>
                  )}

                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
                    {selectedComment?.id === comment.id ? comment.comment_text : (
                      comment.comment_text.length > 300
                        ? `${comment.comment_text.substring(0, 300)}...`
                        : comment.comment_text
                    )}
                  </p>

                  <div className="flex flex-wrap gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span>Submitted: {new Date(comment.submitted_at).toLocaleString()}</span>
                    {comment.moderated_at && (
                      <span>Moderated: {new Date(comment.moderated_at).toLocaleString()}</span>
                    )}
                  </div>

                  {comment.moderation_notes && (
                    <div className="mt-2 p-2 bg-lsc-cream/50 dark:bg-earth-900/50 rounded text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <strong>Moderation notes:</strong> {comment.moderation_notes}
                    </div>
                  )}

                  {comment.rejection_reason && (
                    <div className="mt-2 p-2 bg-status-danger-50 dark:bg-status-danger-900/20 rounded text-xs text-status-danger-700 dark:text-status-danger-300">
                      <strong>Rejection reason:</strong> {comment.rejection_reason}
                    </div>
                  )}

                  {comment.staff_response && (
                    <div className="mt-2 p-2 bg-earth-50 dark:bg-earth-800/20 rounded text-xs text-lsc-rose dark:text-lsc-rose-light">
                      <strong>Staff response:</strong> {comment.staff_response}
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {comment.comment_text.length > 300 && (
                    <button
                      onClick={() => setSelectedComment(selectedComment?.id === comment.id ? null : comment)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600 rounded-lg transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      {selectedComment?.id === comment.id ? 'Less' : 'Full'}
                    </button>
                  )}

                  {comment.status === 'pending' && (
                    <>
                      <button
                        onClick={() => onModerateAction('approve', comment)}
                        className="flex items-center gap-1 px-3 py-1 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => onModerateAction('reject', comment)}
                        className="flex items-center gap-1 px-3 py-1 text-sm bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 rounded-lg transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject
                      </button>
                    </>
                  )}

                  {comment.status === 'approved' && (
                    <>
                      <button
                        onClick={() => onModerateAction('read', comment)}
                        className="flex items-center gap-1 px-3 py-1 text-sm bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light hover:bg-earth-200 dark:hover:bg-earth-800/50 rounded-lg transition-colors"
                      >
                        <FileText className="w-4 h-4" />
                        Mark Read
                      </button>
                      {!comment.staff_response && (
                        <button
                          onClick={() => onRespond(comment)}
                          className="flex items-center gap-1 px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 rounded-lg hover:bg-lsc-cream/80"
                        >
                          <Reply className="w-4 h-4" />
                          Respond
                        </button>
                      )}
                    </>
                  )}

                  <button
                    onClick={() => onModerateAction('delete', comment)}
                    className="flex items-center gap-1 px-3 py-1 text-sm bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
