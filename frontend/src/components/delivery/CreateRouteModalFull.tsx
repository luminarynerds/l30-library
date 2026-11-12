/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2 } from 'lucide-react';
import type { DeliveryVolunteer } from '../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateRouteModalFullProps {
  name: string;
  onNameChange: (v: string) => void;
  date: string;
  onDateChange: (v: string) => void;
  volunteerId: number | null;
  onVolunteerChange: (id: number | null) => void;
  plannedStart: string;
  onPlannedStartChange: (v: string) => void;
  plannedEnd: string;
  onPlannedEndChange: (v: string) => void;
  notes: string;
  onNotesChange: (v: string) => void;
  volunteers: DeliveryVolunteer[];
  onSubmit: () => void;
  onClose: () => void;
  isPending: boolean;
}

export function CreateRouteModalFull({
  name,
  onNameChange,
  date,
  onDateChange,
  volunteerId,
  onVolunteerChange,
  plannedStart,
  onPlannedStartChange,
  plannedEnd,
  onPlannedEndChange,
  notes,
  onNotesChange,
  volunteers,
  onSubmit,
  onClose,
  isPending,
}: CreateRouteModalFullProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Create Delivery Route">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Create Delivery Route</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Route Name <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                placeholder={t('placeholder.homeDelivery.egNorthDistrictRoute')}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Date <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => onDateChange(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Assigned Volunteer</label>
              <select
                value={volunteerId ?? ''}
                onChange={(e) => onVolunteerChange(Number(e.target.value) || null)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="">Unassigned</option>
                {volunteers.filter((v) => v.status === 'active').map((v) => (
                  <option key={v.id} value={v.id}>{v.user_name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Planned Start</label>
                <input
                  type="time"
                  value={plannedStart}
                  onChange={(e) => onPlannedStartChange(e.target.value)}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Planned End</label>
                <input
                  type="time"
                  value={plannedEnd}
                  onChange={(e) => onPlannedEndChange(e.target.value)}
                  className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes</label>
              <textarea
                value={notes}
                onChange={(e) => onNotesChange(e.target.value)}
                rows={2}
                placeholder={t('homeDelivery.routeNotesOrSpecialInstructions')}
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
              Create Route
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
