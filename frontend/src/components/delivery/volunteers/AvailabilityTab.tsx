/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CheckCircle, XCircle } from 'lucide-react';
import { DeliveryVolunteer } from '../../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { DAYS_OF_WEEK } from './volunteers-data';

interface AvailabilityTabProps {
  volunteers: DeliveryVolunteer[];
  availableOnDate: string;
  onAvailableDateChange: (v: string) => void;
}

export function AvailabilityTab({ volunteers, availableOnDate, onAvailableDateChange }: AvailabilityTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 flex-wrap">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Find available on date:
          </label>
          <input
            type="date"
            value={availableOnDate}
            onChange={(e) => onAvailableDateChange(e.target.value)}
            className="px-3 py-2 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>
        {availableOnDate && (
          <button
            onClick={() => onAvailableDateChange('')}
            className="mt-6 px-3 py-2 text-sm text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream"
          >
            Clear filter
          </button>
        )}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('homeDeliveryVolunteers.volunteerAvailabilityByDay')}</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryVolunteers.basedOnEachVolunteerS')}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Volunteer</th>
                {DAYS_OF_WEEK.map((day) => (
                  <th key={day} className="px-2 py-3 font-medium text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                    {day.slice(0, 3)}
                  </th>
                ))}
                <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Time Window</th>
                <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Max/Week</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
              {volunteers
                .filter((v) => v.status === 'active')
                .map((volunteer) => (
                  <tr key={volunteer.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-2">
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.user_name}</p>
                        {volunteer.assigned_patrons_count !== undefined && (
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {volunteer.assigned_patrons_count} patron{volunteer.assigned_patrons_count !== 1 ? 's' : ''}
                          </p>
                        )}
                      </div>
                    </td>
                    {DAYS_OF_WEEK.map((day) => (
                      <td key={day} className="px-2 py-2 text-center">
                        {volunteer.available_days.includes(day) ? (
                          <CheckCircle className="w-4 h-4 text-status-success-500 mx-auto" />
                        ) : (
                          <XCircle className="w-4 h-4 text-lsc-border dark:text-earth-700 mx-auto" />
                        )}
                      </td>
                    ))}
                    <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {volunteer.available_time_start && volunteer.available_time_end
                        ? `${volunteer.available_time_start} – ${volunteer.available_time_end}`
                        : volunteer.available_time_start || '—'}
                    </td>
                    <td className="px-4 py-2 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                      {volunteer.max_deliveries_per_week}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
          {volunteers.filter((v) => v.status === 'active').length === 0 && (
            <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">
              No active volunteers
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
