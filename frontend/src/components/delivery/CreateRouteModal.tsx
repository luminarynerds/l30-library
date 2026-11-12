/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n';
import type { DeliveryVolunteer } from '../../api/homeDeliveryApi';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateRouteModalProps {
  volunteers: DeliveryVolunteer[];
  name: string;
  date: string;
  volunteerId: number | null;
  onNameChange: (val: string) => void;
  onDateChange: (val: string) => void;
  onVolunteerChange: (id: number | null) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function CreateRouteModal({
  volunteers,
  name,
  date,
  volunteerId,
  onNameChange,
  onDateChange,
  onVolunteerChange,
  onSubmit,
  onClose,
}: CreateRouteModalProps) {
  const { t } = useTranslation();
  return (
    <ModalBackdrop onClose={onClose} title="Create Route">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-md w-full">
        <div className="p-6">
          <h2 className="font-serif text-xl font-bold mb-4">Create Route</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Route Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
                placeholder={t('placeholder.homeDeliveryManagement.egNorthSideRoute')}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => onDateChange(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Assigned Volunteer (optional)</label>
              <select
                value={volunteerId || ''}
                onChange={(e) => onVolunteerChange(Number(e.target.value) || null)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500"
              >
                <option value="">No volunteer assigned</option>
                {volunteers
                  .filter((v) => v.status === 'active')
                  .map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.user_name}
                    </option>
                  ))}
              </select>
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
              Create Route
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
