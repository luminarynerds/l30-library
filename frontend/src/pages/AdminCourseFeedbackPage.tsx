/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { API_BASE } from '@/api/types';
import {
  Loader2,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Link2,
  Eye,
  HelpCircle,
  CheckCircle,
  XCircle,
  Clock,
  Filter,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import api from '../api/api';
import { useTranslation} from '@/i18n'
import { AdminShell } from '@/components/shells'

interface FeedbackItem {
  id: number;
  user_id: number | null;
  course_id: number;
  lesson_id: number | null;
  feedback_type: string;
  rating: number | null;
  comment: string | null;
  status: string;
  admin_notes: string | null;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  created_at: string;
  user_name: string | null;
  user_email: string | null;
  course_title: string | null;
  lesson_title: string | null;
  reviewer_name: string | null;
}

interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
  page: number;
  page_size: number;
  pending_count: number;
  issue_count: number;
}

const FEEDBACK_TYPE_CONFIG: Record<string, { label: string; icon: React.ElementType; classes: string }> = {
  helpful: { label: 'Helpful', icon: ThumbsUp, classes: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400' },
  not_helpful: { label: 'Not Helpful', icon: ThumbsDown, classes: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400' },
  content_error: { label: 'Content Error', icon: AlertTriangle, classes: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400' },
  broken_link: { label: 'Broken Link', icon: Link2, classes: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400' },
  accessibility: { label: 'Accessibility', icon: Eye, classes: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400' },
  other: { label: 'Other', icon: HelpCircle, classes: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-400' },
};

const STATUS_CONFIG: Record<string, { label: string; icon: React.ElementType; classes: string }> = {
  pending: { label: 'Pending', icon: Clock, classes: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400' },
  reviewed: { label: 'Reviewed', icon: Eye, classes: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light' },
  resolved: { label: 'Resolved', icon: CheckCircle, classes: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400' },
  dismissed: { label: 'Dismissed', icon: XCircle, classes: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-400' },
};

function TypeBadge({ type }: { type: string }) {
  const config = (FEEDBACK_TYPE_CONFIG[type] ?? FEEDBACK_TYPE_CONFIG.other)!;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.classes}`}>
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config = (STATUS_CONFIG[status] ?? STATUS_CONFIG.pending)!;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.classes}`}>
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </span>
  );
}

export default function AdminCourseFeedbackPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<FeedbackListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filterType, setFilterType] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [adminNotes, setAdminNotes] = useState<Record<number, string>>({});
  const [updating, setUpdating] = useState<number | null>(null);

  const pageSize = 25;

  const fetchFeedback = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('page_size', String(pageSize));
      if (filterType) params.set('feedback_type', filterType);
      if (filterStatus) params.set('feedback_status', filterStatus);

      const result = await api.get(`${API_BASE}/learning/admin/feedback?${params.toString()}`);
      setData(result as FeedbackListResponse);
    } catch (err: unknown) {
      const error = err as { message?: string };
      toast.error(error.message || t('toast.adminCourseFeedback.failedToLoadFeedback'));
    } finally {
      setLoading(false);
    }
  }, [page, filterType, filterStatus, t]);

  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  const handleStatusUpdate = async (feedbackId: number, newStatus: string) => {
    setUpdating(feedbackId);
    try {
      const notes = adminNotes[feedbackId] || '';
      await api.patch(`${API_BASE}/learning/admin/feedback/${feedbackId}`, {
        status: newStatus,
        admin_notes: notes || undefined,
      });
      toast.success(t('toast.adminCourseFeedback.feedbackMarkedAsNewstatus', { newStatus: newStatus }));
      setExpandedId(null);
      setAdminNotes(prev => { const next = { ...prev }; delete next[feedbackId]; return next; });
      fetchFeedback();
    } catch (err: unknown) {
      const error = err as { message?: string };
      toast.error(error.message || t('toast.adminCourseFeedback.failedToUpdateFeedback'));
    } finally {
      setUpdating(null);
    }
  };

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  // Aggregate counts from API (across all pages, not just current)
  const pendingCount = data?.pending_count ?? 0;
  const issueCount = data?.issue_count ?? 0;

  return (
    <AdminShell
      title="Course Feedback"
      subtitle="Review and manage feedback submitted by patrons on courses and lessons."
      icon={<MessageSquare className="w-7 h-7 text-lsc-rose" />}
    >
      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Feedback</p>
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{data.total}</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <p className="text-sm text-status-warning-700 dark:text-status-warning-400">Pending Review</p>
            <p className="text-2xl font-bold text-status-warning-700 dark:text-status-warning-400">{pendingCount}</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
            <p className="text-sm text-status-danger-700 dark:text-status-danger-400">Reported Issues</p>
            <p className="text-2xl font-bold text-status-danger-700 dark:text-status-danger-400">{issueCount}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6 items-center">
        <Filter className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" aria-hidden="true" />
        <select
          value={filterType}
          onChange={(e) => { setFilterType(e.target.value); setPage(1); }}
          className="text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          aria-label={t('admin.adminCourseFeedback.filterByFeedbackType')}
        >
          <option value="">All Types</option>
          <option value="helpful">Helpful</option>
          <option value="not_helpful">Not Helpful</option>
          <option value="content_error">Content Error</option>
          <option value="broken_link">Broken Link</option>
          <option value="accessibility">Accessibility</option>
          <option value="other">Other</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
          className="text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          aria-label={t('aria.acquisition.filterByStatus')}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="reviewed">Reviewed</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16" role="status" aria-live="polite" aria-busy="true">
          <Loader2 className="w-10 h-10 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          <span className="mt-4 text-lsc-dark/70 dark:text-lsc-cream/70">Loading feedback...</span>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-12 text-center" role="status">
          <div className="w-16 h-16 bg-lsc-rose/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <MessageSquare className="w-8 h-8 text-lsc-rose" aria-hidden="true" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">No feedback yet</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mx-auto">
            Feedback submitted by patrons on courses and lessons will appear here.
          </p>
        </div>
      ) : (
        <>
          {/* Feedback list */}
          <div className="space-y-3">
            {data.items.map((fb) => (
              <div
                key={fb.id}
                className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden"
              >
                {/* Row summary */}
                <button
                  onClick={() => {
                    setExpandedId(expandedId === fb.id ? null : fb.id);
                    if (expandedId !== fb.id) {
                      setAdminNotes(prev => ({ ...prev, [fb.id]: fb.admin_notes || '' }));
                    }
                  }}
                  className="w-full text-left px-5 py-4 flex flex-col sm:flex-row sm:items-center gap-3 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors"
                  aria-expanded={expandedId === fb.id}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <TypeBadge type={fb.feedback_type} />
                      <StatusBadge status={fb.status} />
                    </div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={`${fb.course_title || `Course #${fb.course_id}`}${fb.lesson_title ? ` \u2192 ${fb.lesson_title}` : ''}`}>
                      {fb.course_title || `Course #${fb.course_id}`}
                      {fb.lesson_title && (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/50"> &rarr; {fb.lesson_title}</span>
                      )}
                    </p>
                    {fb.comment && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate mt-1" title={fb.comment}>{fb.comment}</p>
                    )}
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                      {fb.user_name || fb.user_email || 'Anonymous'}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      {new Date(fb.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </button>

                {/* Expanded detail */}
                {expandedId === fb.id && (
                  <div className="border-t border-lsc-border dark:border-earth-700 px-5 py-4 bg-lsc-cream/30 dark:bg-earth-700/30">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4 text-sm">
                      <div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">Submitted by:</span>{' '}
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {fb.user_name || fb.user_email || 'Anonymous'}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">Date:</span>{' '}
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {new Date(fb.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">Course:</span>{' '}
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{fb.course_title || `#${fb.course_id}`}</span>
                      </div>
                      {fb.lesson_title && (
                        <div>
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Lesson:</span>{' '}
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{fb.lesson_title}</span>
                        </div>
                      )}
                      {fb.reviewer_name && (
                        <div>
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Reviewed by:</span>{' '}
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{fb.reviewer_name}</span>
                        </div>
                      )}
                      {fb.reviewed_at && (
                        <div>
                          <span className="font-medium text-lsc-dark dark:text-lsc-cream">Reviewed at:</span>{' '}
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(fb.reviewed_at).toLocaleString()}</span>
                        </div>
                      )}
                    </div>

                    {fb.comment && (
                      <div className="mb-4">
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Comment:</p>
                        <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 bg-lsc-white dark:bg-earth-800 rounded-lg p-3 border border-lsc-border dark:border-earth-700">
                          {fb.comment}
                        </p>
                      </div>
                    )}

                    {/* Admin notes */}
                    <div className="mb-4">
                      <label htmlFor={`notes-${fb.id}`} className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1 block">
                        Admin Notes:
                      </label>
                      <textarea
                        id={`notes-${fb.id}`}
                        value={adminNotes[fb.id] ?? ''}
                        onChange={(e) => setAdminNotes(prev => ({ ...prev, [fb.id]: e.target.value }))}
                        rows={2}
                        maxLength={2000}
                        className="w-full text-sm border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
                        placeholder={t('admin.adminCourseFeedback.addInternalNotesAboutThis')}
                      />
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      {fb.status !== 'reviewed' && (
                        <button
                          onClick={() => handleStatusUpdate(fb.id, 'reviewed')}
                          disabled={updating === fb.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded-lg hover:bg-earth-200 dark:hover:bg-earth-800/50 transition-colors disabled:opacity-50"
                        >
                          <Eye className="w-3.5 h-3.5" /> Mark Reviewed
                        </button>
                      )}
                      {fb.status !== 'resolved' && (
                        <button
                          onClick={() => handleStatusUpdate(fb.id, 'resolved')}
                          disabled={updating === fb.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-lg hover:bg-status-success-200 dark:hover:bg-status-success-900/50 transition-colors disabled:opacity-50"
                        >
                          <CheckCircle className="w-3.5 h-3.5" /> Mark Resolved
                        </button>
                      )}
                      {fb.status !== 'dismissed' && (
                        <button
                          onClick={() => handleStatusUpdate(fb.id, 'dismissed')}
                          disabled={updating === fb.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-200 dark:hover:bg-earth-900/50 transition-colors disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" /> Dismiss
                        </button>
                      )}
                      {fb.status !== 'pending' && (
                        <button
                          onClick={() => handleStatusUpdate(fb.id, 'pending')}
                          disabled={updating === fb.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded-lg hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50 transition-colors disabled:opacity-50"
                        >
                          <Clock className="w-3.5 h-3.5" /> Reopen
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Page {page} of {totalPages} ({data.total} total)
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 transition-colors"
                  aria-label={t('aria.account.previousPage')}
                >
                  <ChevronLeft className="w-4 h-4" /> Prev
                </button>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="inline-flex items-center gap-1 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 transition-colors"
                  aria-label={t('aria.account.nextPage')}
                >
                  Next <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </AdminShell>
  );
}