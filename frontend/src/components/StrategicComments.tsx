/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useLanguage, formatRelativeTime } from "../i18n";
import { API_BASE } from '@/api/types';
import {
  MessageCircle,
  Reply,
  Edit2,
  Trash2,
  Send,
  X,
  ChevronDown,
  ChevronUp,
  User as UserIcon,
} from "lucide-react";
import api from "../api/api";
import toast from "react-hot-toast";
import ConfirmDialog from "./ConfirmDialog";
import { useTranslation} from '@/i18n'

interface Comment {
  id: number;
  goal_id: number;
  user_id: number;
  user_name: string;
  content: string;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
  replies?: Comment[];
}

interface StrategicCommentsProps {
  goalId: number;
  canComment: boolean;
}

export default function StrategicComments({ goalId, canComment }: StrategicCommentsProps) {
  const { t } = useTranslation()
  const { user } = useAuth();
  const { language } = useLanguage();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [replyContent, setReplyContent] = useState("");
  const [editingComment, setEditingComment] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; content: string } | null>(null);
  const [expandedReplies, setExpandedReplies] = useState<Set<number>>(new Set());

  const fetchComments = async () => {
    setLoading(true);
    try {
      const res = await api.get(`${API_BASE}/strategic/goals/${goalId}/comments`);
      setComments(res || []);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchComments();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goalId]);

  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || submitting) return;

    setSubmitting(true);
    try {
      await api.post(`${API_BASE}/strategic/goals/${goalId}/comments`, {
        content: newComment.trim(),
      });
      toast.success(t('toast.commentAdded'));
      setNewComment("");
      fetchComments();
    } catch {
      toast.error(t('components.strategicComments.unableToAddCommentPlease'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmitReply = async (parentId: number) => {
    if (!replyContent.trim() || submitting) return;

    setSubmitting(true);
    try {
      await api.post(`${API_BASE}/strategic/goals/${goalId}/comments`, {
        content: replyContent.trim(),
        parent_id: parentId,
      });
      toast.success(t('toast.replyAdded'));
      setReplyContent("");
      setReplyingTo(null);
      // Expand replies for the parent comment
      setExpandedReplies((prev) => new Set(prev).add(parentId));
      fetchComments();
    } catch {
      toast.error(t('components.strategicComments.unableToAddReplyPlease'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateComment = async (commentId: number) => {
    if (!editContent.trim() || submitting) return;

    setSubmitting(true);
    try {
      await api.put(`${API_BASE}/strategic/comments/${commentId}`, {
        content: editContent.trim(),
      });
      toast.success(t('toast.commentUpdated'));
      setEditingComment(null);
      setEditContent("");
      fetchComments();
    } catch {
      toast.error(t('components.strategicComments.unableToUpdateCommentPlease'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    try {
      await api.delete(`${API_BASE}/strategic/comments/${commentId}`);
      toast.success(t('toast.commentDeleted'));
      setDeleteConfirm(null);
      fetchComments();
    } catch {
      toast.error(t('components.strategicComments.unableToDeleteCommentPlease'));
    }
  };

  const startEdit = (comment: Comment) => {
    setEditingComment(comment.id);
    setEditContent(comment.content);
    setReplyingTo(null);
  };

  const startReply = (commentId: number) => {
    setReplyingTo(commentId);
    setReplyContent("");
    setEditingComment(null);
  };

  const toggleReplies = (commentId: number) => {
    setExpandedReplies((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(commentId)) {
        newSet.delete(commentId);
      } else {
        newSet.add(commentId);
      }
      return newSet;
    });
  };

  const isOwnComment = (comment: Comment) => {
    return user && comment.user_id === user.id;
  };

  // Organize comments into threads (top-level and nested replies)
  const topLevelComments = comments.filter((c) => !c.parent_id);
  const repliesMap = new Map<number, Comment[]>();
  comments
    .filter((c) => c.parent_id)
    .forEach((c) => {
      const parentReplies = repliesMap.get(c.parent_id!) || [];
      parentReplies.push(c);
      repliesMap.set(c.parent_id!, parentReplies);
    });

  const renderComment = (comment: Comment, isReply = false) => {
    const replies = repliesMap.get(comment.id) || [];
    const hasReplies = replies.length > 0;
    const isExpanded = expandedReplies.has(comment.id);
    const isEditing = editingComment === comment.id;
    const isReplying = replyingTo === comment.id;

    return (
      <div
        key={comment.id}
        className={`${isReply ? "ml-8 pl-4 border-l-2 border-lsc-border dark:border-earth-700" : ""}`}
      >
        <div className="py-3">
          {/* Comment Header */}
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 bg-lsc-cream dark:bg-lsc-brown rounded-full flex items-center justify-center shrink-0">
              <UserIcon className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-lsc-dark dark:text-lsc-cream text-sm">
                  {comment.user_name}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {formatRelativeTime(comment.created_at, language)}
                </span>
                {comment.updated_at !== comment.created_at && (
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                    (edited)
                  </span>
                )}
              </div>

              {/* Comment Content or Edit Form */}
              {isEditing ? (
                <div className="mt-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                    placeholder={t('placeholder.strategicComments.editYourComment')}
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleUpdateComment(comment.id)}
                      disabled={submitting || !editContent.trim()}
                      className="px-3 py-1.5 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingComment(null);
                        setEditContent("");
                      }}
                      className="px-3 py-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg text-sm transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/90 whitespace-pre-wrap break-words">
                  {comment.content}
                </p>
              )}

              {/* Comment Actions */}
              {!isEditing && (
                <div className="flex items-center gap-2 mt-2">
                  {canComment && !isReply && (
                    <button
                      onClick={() => startReply(comment.id)}
                      className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
                    >
                      <Reply className="h-3.5 w-3.5" />
                      Reply
                    </button>
                  )}
                  {isOwnComment(comment) && (
                    <>
                      <button
                        onClick={() => startEdit(comment)}
                        className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                        Edit
                      </button>
                      <button
                        onClick={() =>
                          setDeleteConfirm({
                            id: comment.id,
                            content: comment.content.substring(0, 50) + (comment.content.length > 50 ? "..." : ""),
                          })
                        }
                        className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 dark:hover:text-status-danger-400 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </>
                  )}
                  {hasReplies && !isReply && (
                    <button
                      onClick={() => toggleReplies(comment.id)}
                      className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors ml-auto"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-3.5 w-3.5" />
                          Hide {replies.length} {replies.length === 1 ? "reply" : "replies"}
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3.5 w-3.5" />
                          Show {replies.length} {replies.length === 1 ? "reply" : "replies"}
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Reply Form */}
          {isReplying && canComment && (
            <div className="mt-3 ml-11">
              <textarea
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                placeholder={t('placeholder.strategicComments.writeAReply')}
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => handleSubmitReply(comment.id)}
                  disabled={submitting || !replyContent.trim()}
                  className="flex items-center gap-1 px-3 py-1.5 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                >
                  <Send className="h-3.5 w-3.5" />
                  Reply
                </button>
                <button
                  onClick={() => {
                    setReplyingTo(null);
                    setReplyContent("");
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg text-sm transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Nested Replies */}
        {hasReplies && isExpanded && !isReply && (
          <div className="mt-1">
            {replies.map((reply) => renderComment(reply, true))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
          <MessageCircle className="h-5 w-5" />
          <span className="font-medium">Comments</span>
        </div>
        <div className="motion-safe:animate-pulse space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="flex gap-3">
              <div className="w-8 h-8 bg-lsc-cream dark:bg-lsc-brown rounded-full" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-lsc-cream dark:bg-lsc-brown rounded w-1/4" />
                <div className="h-12 bg-lsc-cream dark:bg-lsc-brown rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
        <MessageCircle className="h-5 w-5 text-lsc-rose" />
        <span className="font-medium">
          Comments {comments.length > 0 && `(${comments.length})`}
        </span>
      </div>

      {/* Comments List */}
      {topLevelComments.length === 0 ? (
        <div className="py-8 text-center">
          <MessageCircle className="h-10 w-10 text-lsc-border dark:text-earth-300 mx-auto mb-2" />
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            No comments yet. {canComment && "Be the first to start the discussion!"}
          </p>
        </div>
      ) : (
        <div className="divide-y divide-lsc-border dark:divide-earth-700">
          {topLevelComments.map((comment) => renderComment(comment))}
        </div>
      )}

      {/* New Comment Form */}
      {canComment && (
        <form onSubmit={handleSubmitComment} className="pt-4 border-t border-lsc-border dark:border-earth-700">
          <label htmlFor="new-comment" className="sr-only">
            Add a comment
          </label>
          <textarea
            id="new-comment"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            rows={3}
            className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            placeholder={t('placeholder.strategicComments.addAComment')}
          />
          <div className="flex justify-end mt-2">
            <button
              type="submit"
              disabled={submitting || !newComment.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
            >
              <Send className="h-4 w-4" />
              {submitting ? "Posting..." : "Post Comment"}
            </button>
          </div>
        </form>
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete Comment?"
        message={`Are you sure you want to delete this comment? "${deleteConfirm?.content}"`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => {
          if (deleteConfirm) handleDeleteComment(deleteConfirm.id);
        }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  );
}

// Export a small comment count badge component
export function CommentCountBadge({ count }: { count: number }) {
  if (count === 0) return null;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-full text-xs">
      <MessageCircle className="h-3 w-3" />
      {count}
    </span>
  );
}