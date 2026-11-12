/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { HomeDeliveryEnrollment } from '../../api/homeDeliveryApi';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateDeliveryModalProps {
  enrollments: HomeDeliveryEnrollment[];
  enrollmentId: number | null;
  date: string;
  onEnrollmentChange: (id: number | null) => void;
  onDateChange: (date: string) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function CreateDeliveryModal({
  enrollments,
  enrollmentId,
  date,
  onEnrollmentChange,
  onDateChange,
  onSubmit,
  onClose,
}: CreateDeliveryModalProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Schedule Delivery">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-md w-full">
        <div className="p-6">
          <h2 className="font-serif text-xl font-bold mb-4">Schedule Delivery</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Patron</label>
              <select
                value={enrollmentId || ''}
                onChange={(e) => onEnrollmentChange(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
              >
                <option value="">Select patron...</option>
                {enrollments
                  .filter((e) => e.status === 'active')
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.patron_name}
                    </option>
                  ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Delivery Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => onDateChange(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
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
              onClick={onSubmit}
              className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700"
            >
              Schedule
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
