/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n';
import type { HomeDeliveryApplication, HomeDeliveryApplicationStatus } from '../../api/homeDeliveryApi';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ReviewApplicationModalProps {
  application: HomeDeliveryApplication;
  reviewNotes: string;
  denialReason: string;
  onReviewNotesChange: (val: string) => void;
  onDenialReasonChange: (val: string) => void;
  onReview: (status: HomeDeliveryApplicationStatus) => void;
  onClose: () => void;
}

export function ReviewApplicationModal({
  application,
  reviewNotes,
  denialReason,
  onReviewNotesChange,
  onDenialReasonChange,
  onReview,
  onClose,
}: ReviewApplicationModalProps) {
  const { t } = useTranslation();
  return (
    <ModalBackdrop onClose={onClose} title="Review Application">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="font-serif text-xl font-bold mb-4">Review Application</h2>

          <div className="space-y-4">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Patron</p>
              <p className="font-medium">{application.patron_name}</p>
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Reason for Service</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{application.reason}</p>
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Delivery Address</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{application.delivery_address}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Review Notes</label>
              <textarea
                value={reviewNotes}
                onChange={(e) => onReviewNotesChange(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                placeholder={t('placeholder.staff.optionalNotes')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('homeDeliveryManagement.denialReasonIfDenying')}</label>
              <textarea
                value={denialReason}
                onChange={(e) => onDenialReasonChange(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                placeholder={t('placeholder.homeDeliveryManagement.requiredIfDenying')}
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-earth-600 hover:text-earth-800 dark:text-earth-100"
            >
              Cancel
            </button>
            <button
              onClick={() => onReview('denied')}
              className="px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700"
            >
              Deny
            </button>
            <button
              onClick={() => onReview('approved')}
              className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700"
            >
              Approve & Enroll
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
