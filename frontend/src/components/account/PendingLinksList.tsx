/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * PendingLinksList Component
 *
 * Displays pending family account link requests for parents to approve or decline.
 */

import React, { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Loader, AlertCircle } from 'lucide-react';
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'

interface PendingLink {
  id: number;
  requester_name: string;
  message?: string;
  created_at: string;
}

interface PendingLinksListProps {
  onLinkApproved?: () => void;
  onLinkDeclined?: () => void;
}

export const PendingLinksList: React.FC<PendingLinksListProps> = ({
  onLinkApproved,
  onLinkDeclined,
}) => {
  const { t } = useTranslation()
  const [pendingLinks, setPendingLinks] = useState<PendingLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [declineReason, setDeclineReason] = useState<{ [key: number]: string }>({});
  const [showDeclineForm, setShowDeclineForm] = useState<number | null>(null);

  const fetchPendingLinks = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchApi('/households/pending-requests');
      setPendingLinks(data.links || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pending requests');
      setPendingLinks([]);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    fetchPendingLinks();
  }, []);

  const handleApprove = async (linkId: number) => {
    setProcessingId(linkId);

    try {
      await fetchApi(`/households/${linkId}/approve-link`, {
        method: 'PATCH',
        body: JSON.stringify({
          approved: true,
        }),
      });

      // Remove from list
      setPendingLinks(pendingLinks.filter((link) => link.id !== linkId));

      if (onLinkApproved) {
        onLinkApproved();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve link');
    } finally {
      setProcessingId(null);
    }
  };

  const handleDecline = async (linkId: number) => {
    const reason = declineReason[linkId]?.trim();

    if (!reason) {
      setError('Please provide a reason for declining');
      return;
    }

    setProcessingId(linkId);

    try {
      await fetchApi(`/households/${linkId}/approve-link`, {
        method: 'PATCH',
        body: JSON.stringify({
          approved: false,
          decline_reason: reason,
        }),
      });

      // Remove from list
      setPendingLinks(pendingLinks.filter((link) => link.id !== linkId));
      setShowDeclineForm(null);
      setDeclineReason({});

      if (onLinkDeclined) {
        onLinkDeclined();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to decline link');
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8 gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Loader className="w-4 h-4 motion-safe:animate-spin" />
        <span>Loading pending requests...</span>
      </div>
    );
  }

  if (pendingLinks.length === 0) {
    return (
      <div className="p-4 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        <p>{t('components.account.pendingLinksList.noPendingLinkRequests')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="flex items-start gap-3 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-status-danger-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-status-danger-800 dark:text-status-danger-300">{error}</div>
        </div>
      )}

      {pendingLinks.map((link) => (
        <div key={link.id} className="border border-lsc-border dark:border-earth-700 rounded-lg p-4 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{link.requester_name}</h4>
              {link.message && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  <span className="font-medium">Message:</span> {link.message}
                </p>
              )}
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Requested {new Date(link.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>

          {showDeclineForm === link.id ? (
            <div className="mt-4 space-y-3 p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                Reason for declining:
              </label>
              <textarea
                value={declineReason[link.id] || ''}
                onChange={(e) =>
                  setDeclineReason({ ...declineReason, [link.id]: e.target.value })
                }
                placeholder={t('components.account.pendingLinksList.brieflyExplainWhyYouRe')}
                maxLength={500}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setShowDeclineForm(null);
                    setDeclineReason({ ...declineReason, [link.id]: '' });
                  }}
                  className="px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded hover:bg-earth-50 dark:hover:bg-earth-800"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDecline(link.id)}
                  disabled={processingId === link.id}
                  className="px-3 py-1.5 text-sm text-white bg-status-danger-600 rounded hover:bg-status-danger-700 disabled:bg-status-danger-400 flex items-center gap-1"
                >
                  {processingId === link.id && <Loader className="w-3 h-3 motion-safe:animate-spin" />}
                  Confirm Decline
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => handleApprove(link.id)}
                disabled={processingId === link.id}
                className="flex-1 px-3 py-2 bg-status-success-600 text-white rounded hover:bg-status-success-700 disabled:bg-status-success-400 flex items-center justify-center gap-2 text-sm"
              >
                {processingId === link.id && <Loader className="w-4 h-4 motion-safe:animate-spin" />}
                <CheckCircle className="w-4 h-4" />
                Approve
              </button>
              <button
                onClick={() => setShowDeclineForm(link.id)}
                disabled={processingId === link.id}
                className="flex-1 px-3 py-2 bg-earth-200 dark:bg-earth-600 text-earth-800 dark:text-earth-100 rounded hover:bg-earth-300 dark:hover:bg-earth-500 disabled:bg-earth-100 dark:disabled:bg-earth-700 flex items-center justify-center gap-2 text-sm"
              >
                <XCircle className="w-4 h-4" />
                Decline
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
