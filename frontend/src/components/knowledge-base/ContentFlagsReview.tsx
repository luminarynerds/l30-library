/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Flag, CheckCircle, XCircle, AlertTriangle, Clock, Eye } from 'lucide-react';
import api from '../../api/api';
import toast from 'react-hot-toast';
import { useTranslation } from '@/i18n'

interface ContentFlag {
  id: number;
  article_id: number;
  reason: string;
  description: string;
  status: string;
  flagged_by_id: number;
  reviewed_by_id: number | null;
  created_at: string;
  reviewed_at: string | null;
  reviewer_notes: string | null;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; icon: React.ElementType }> = {
  pending: { bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-800 dark:text-status-warning-300', icon: Clock },
  under_review: { bg: 'bg-earth-100 dark:bg-earth-800/30', text: 'text-earth-800 dark:text-lsc-rose-light', icon: Eye },
  resolved: { bg: 'bg-status-success-100 dark:bg-status-success-900/30', text: 'text-status-success-800 dark:text-status-success-300', icon: CheckCircle },
  dismissed: { bg: 'bg-earth-100 dark:bg-earth-700', text: 'text-earth-800 dark:text-earth-300', icon: XCircle },
};

export default function ContentFlagsReview() {
  const { t } = useTranslation()

  // Built inside the component so reason labels react to runtime language switches.
  const REASON_LABELS: Record<string, string> = {
    outdated: t('components.knowledgeBase.contentFlagsReview.reasonOutdated', 'Outdated Information'),
    incorrect: t('components.knowledgeBase.contentFlagsReview.reasonIncorrect', 'Incorrect Information'),
    unclear: t('components.knowledgeBase.contentFlagsReview.reasonUnclear', 'Unclear or Confusing'),
    incomplete: t('components.knowledgeBase.contentFlagsReview.reasonIncomplete', 'Incomplete'),
    other: t('components.knowledgeBase.contentFlagsReview.reasonOther', 'Other'),
  };
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [resolveStatus, setResolveStatus] = useState<string>('resolved');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const queryClient = useQueryClient();
  const resolveSelectRef = useRef<HTMLSelectElement>(null);

  // Move focus into the resolve form when it opens so keyboard/SR users land
  // on the first field rather than staying on the toggle.
  useEffect(() => {
    if (resolvingId !== null) resolveSelectRef.current?.focus();
  }, [resolvingId]);

  const { data: flags, isLoading } = useQuery({
    queryKey: ['content-flags', statusFilter],
    queryFn: async () => {
      return await api.get<ContentFlag[]>('/staff-knowledge/flags', {
        params: { status: statusFilter || undefined },
      });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: async ({ flagId, status, notes }: { flagId: number; status: string; notes: string }) => {
      await api.put(`/staff-knowledge/flags/${flagId}`, {
        status,
        reviewer_notes: notes,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['content-flags'] });
      setResolvingId(null);
      setReviewerNotes('');
      toast.success(t('toast.knowledge-base.flagResolved'));
    },
    onError: () => {
      toast.error(t('components.knowledgeBase.contentFlagsReview.failedToResolveFlag'));
    },
  });

  const statuses = [
    { value: 'pending', label: t('components.knowledgeBase.contentFlagsReview.statusPending', 'Pending'), count: 0 },
    { value: 'under_review', label: t('components.knowledgeBase.contentFlagsReview.statusUnderReview', 'Under Review'), count: 0 },
    { value: 'resolved', label: t('components.knowledgeBase.contentFlagsReview.statusResolved', 'Resolved'), count: 0 },
    { value: 'dismissed', label: t('components.knowledgeBase.contentFlagsReview.statusDismissed', 'Dismissed'), count: 0 },
    { value: '', label: t('components.knowledgeBase.contentFlagsReview.statusAll', 'All'), count: 0 },
  ];

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-status-warning-600"></div>
        <span className="sr-only">{t('common.loading', 'Loading...')}</span>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Flag className="w-6 h-6 text-status-warning-500" />
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{t('components.knowledgeBase.contentFlagsReview.contentFlagsForReview')}</h2>
      </div>

      {/* Status Filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {statuses.map(s => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(s.value)}
            aria-pressed={statusFilter === s.value}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition ${
              statusFilter === s.value
                ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 border border-status-warning-200 dark:border-status-warning-800'
                : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 border border-lsc-border dark:border-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Flags List */}
      {!flags || flags.length === 0 ? (
        <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
          <Flag className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-3" />
          <p className="text-earth-600 dark:text-earth-400">
            {statusFilter === 'pending'
              ? t('components.knowledgeBase.contentFlagsReview.noPendingFlags', 'No pending flags. Content is up to date!')
              : t('components.knowledgeBase.contentFlagsReview.noFlagsMatchingFilter', 'No flags matching this filter.')}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {flags.map(flag => {
            const style = (STATUS_STYLES[flag.status] ?? STATUS_STYLES.pending)!;
            const StatusIcon = style.icon;

            return (
              <div
                key={flag.id}
                className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-5"
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
                      <StatusIcon className="w-3 h-3" />
                      {flag.status.replace('_', ' ')}
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      flag.reason === 'outdated' ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300' :
                      flag.reason === 'incorrect' ? 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300' :
                      'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-200'
                    }`}>
                      {REASON_LABELS[flag.reason] || flag.reason}
                    </div>
                  </div>
                  <span className="text-xs text-earth-600 dark:text-earth-400 flex-shrink-0">
                    {new Date(flag.created_at).toLocaleDateString()}
                  </span>
                </div>

                <p className="text-earth-600 dark:text-earth-400 mb-3">{flag.description}</p>

                <p className="text-sm text-earth-600 dark:text-earth-400 mb-4">
                  {`${t('components.knowledgeBase.contentFlagsReview.flaggedArticle', 'Flagged article')}: #${flag.article_id}`}
                </p>

                {/* Reviewer notes (if resolved) */}
                {flag.reviewer_notes && (
                  <div className="bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg p-3 mb-4">
                    <p className="text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">{t('components.knowledgeBase.contentFlagsReview.reviewerNotes', 'Reviewer Notes:')}</p>
                    <p className="text-sm text-earth-600 dark:text-earth-400">{flag.reviewer_notes}</p>
                    {flag.reviewed_at && (
                      <p className="text-xs text-earth-600 dark:text-earth-400 mt-2">
                        {`${t('components.knowledgeBase.contentFlagsReview.reviewedOn', 'Reviewed on')} ${new Date(flag.reviewed_at).toLocaleDateString()}`}
                      </p>
                    )}
                  </div>
                )}

                {/* Resolve form */}
                {flag.status === 'pending' && resolvingId === flag.id && (
                  <div id={`content-flag-resolve-form-${flag.id}`} className="border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-4 bg-status-warning-50 dark:bg-status-warning-900/10">
                    <div className="space-y-3">
                      <div>
                        <label htmlFor={`content-flag-resolution-${flag.id}`} className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                          {t('components.knowledgeBase.contentFlagsReview.resolution', 'Resolution')}
                        </label>
                        <select
                          id={`content-flag-resolution-${flag.id}`}
                          ref={resolveSelectRef}
                          value={resolveStatus}
                          onChange={e => setResolveStatus(e.target.value)}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                        >
                          <option value="resolved">{t('components.knowledgeBase.contentFlagsReview.resolvedContentUpdated', 'Resolved - Content Updated')}</option>
                          <option value="dismissed">{t('components.knowledgeBase.contentFlagsReview.dismissedNoActionNeeded')}</option>
                          <option value="under_review">{t('components.knowledgeBase.contentFlagsReview.underReviewNeedsMoreInvestigation')}</option>
                        </select>
                      </div>
                      <div>
                        <label htmlFor={`content-flag-notes-${flag.id}`} className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                          {t('components.knowledgeBase.contentFlagsReview.notes', 'Notes')}
                        </label>
                        <textarea
                          id={`content-flag-notes-${flag.id}`}
                          value={reviewerNotes}
                          onChange={e => setReviewerNotes(e.target.value)}
                          placeholder={t('components.knowledgeBase.contentFlagsReview.describeWhatActionWasTaken')}
                          rows={3}
                          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                        />
                      </div>
                      <div className="flex gap-3">
                        <button
                          onClick={() => resolveMutation.mutate({
                            flagId: flag.id,
                            status: resolveStatus,
                            notes: reviewerNotes,
                          })}
                          disabled={resolveMutation.isPending}
                          className="px-4 py-2 bg-status-warning-600 hover:bg-status-warning-700 disabled:bg-earth-400 text-white rounded-lg font-medium transition"
                        >
                          {t('components.knowledgeBase.contentFlagsReview.submitResolution', 'Submit Resolution')}
                        </button>
                        <button
                          onClick={() => { setResolvingId(null); setReviewerNotes(''); }}
                          className="px-4 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 text-earth-600 dark:text-earth-400 rounded-lg font-medium transition"
                        >
                          {t('components.knowledgeBase.contentFlagsReview.cancel', 'Cancel')}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {flag.status === 'pending' && resolvingId !== flag.id && (
                  <button
                    onClick={() => { setResolvingId(flag.id); setReviewerNotes(''); setResolveStatus('resolved'); }}
                    className="px-4 py-2 bg-status-warning-100 dark:bg-status-warning-900/30 hover:bg-status-warning-200 dark:hover:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300 rounded-lg font-medium text-sm transition flex items-center gap-2"
                  >
                    <AlertTriangle className="w-4 h-4" />
                    {t('components.knowledgeBase.contentFlagsReview.reviewAndResolve', 'Review & Resolve')}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
