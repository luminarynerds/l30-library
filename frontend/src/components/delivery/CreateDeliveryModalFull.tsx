/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2 } from 'lucide-react';
import type { HomeDeliveryEnrollment, DeliveryRoute } from '../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateDeliveryModalFullProps {
  enrollmentId: number | null;
  onEnrollmentChange: (id: number | null) => void;
  date: string;
  onDateChange: (date: string) => void;
  timeStart: string;
  onTimeStartChange: (t: string) => void;
  timeEnd: string;
  onTimeEndChange: (t: string) => void;
  routeId: number | null;
  onRouteChange: (id: number | null) => void;
  notes: string;
  onNotesChange: (n: string) => void;
  enrollments: HomeDeliveryEnrollment[];
  routes: DeliveryRoute[];
  onSubmit: () => void;
  onClose: () => void;
  isPending: boolean;
}

export function CreateDeliveryModalFull({
  enrollmentId,
  onEnrollmentChange,
  date,
  onDateChange,
  timeStart,
  onTimeStartChange,
  timeEnd,
  onTimeEndChange,
  routeId,
  onRouteChange,
  notes,
  onNotesChange,
  enrollments,
  routes,
  onSubmit,
  onClose,
  isPending,
}: CreateDeliveryModalFullProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Schedule Delivery">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Schedule Delivery</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Patron <span className="text-status-danger-500">*</span>
              </label>
              <select
                value={enrollmentId ?? ''}
                onChange={(e) => onEnrollmentChange(Number(e.target.value) || null)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">Select patron...</option>
                {enrollments.filter((e) => e.status === 'active').map((e) => (
                  <option key={e.id} value={e.id}>{e.patron_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Delivery Date <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => onDateChange(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Time Start</label>
                <input
                  type="time"
                  value={timeStart}
                  onChange={(e) => onTimeStartChange(e.target.value)}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Time End</label>
                <input
                  type="time"
                  value={timeEnd}
                  onChange={(e) => onTimeEndChange(e.target.value)}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('homeDelivery.assignToRouteOptional')}</label>
              <select
                value={routeId ?? ''}
                onChange={(e) => onRouteChange(Number(e.target.value) || null)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">No route</option>
                {routes.filter((r) => ['draft', 'planned'].includes(r.status)).map((r) => (
                  <option key={r.id} value={r.id}>{r.name} ({r.date})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Staff Notes</label>
              <textarea
                value={notes}
                onChange={(e) => onNotesChange(e.target.value)}
                rows={2}
                placeholder={t('homeDelivery.internalNotesForStaff')}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
            >
              Cancel
            </button>
            <button
              onClick={onSubmit}
              disabled={isPending}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium"
            >
              {isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Schedule
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
