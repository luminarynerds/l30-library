/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Clock, Loader2, Plus, CheckCircle } from 'lucide-react';
import { UseMutationResult } from '@tanstack/react-query';
import { DeliveryVolunteer } from '../../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { VolunteerStatusBadge, RecognitionBadge } from './VolunteerBadges';
import { formatDate } from './volunteers-data';
import toast from 'react-hot-toast';

interface HoursLog {
  id: number;
  date: string;
  hours: number;
  activity_type: string;
  notes?: string | null;
  verified: boolean;
}

interface HoursData {
  total_hours: number;
  logs: HoursLog[];
}

interface HoursTabProps {
  volunteers: DeliveryVolunteer[];
  hoursVolunteerId: number | null;
  hoursDate: string;
  hoursCount: string;
  hoursActivityType: string;
  hoursNotes: string;
  hoursData: HoursData | undefined;
  logHoursMutation: UseMutationResult<unknown, Error, void>;
  verifyHoursMutation: UseMutationResult<unknown, Error, number>;
  onHoursVolunteerIdChange: (v: number | null) => void;
  onHoursDateChange: (v: string) => void;
  onHoursCountChange: (v: string) => void;
  onHoursActivityTypeChange: (v: string) => void;
  onHoursNotesChange: (v: string) => void;
}

export function HoursTab({
  volunteers,
  hoursVolunteerId,
  hoursDate,
  hoursCount,
  hoursActivityType,
  hoursNotes,
  hoursData,
  logHoursMutation,
  verifyHoursMutation,
  onHoursVolunteerIdChange,
  onHoursDateChange,
  onHoursCountChange,
  onHoursActivityTypeChange,
  onHoursNotesChange,
}: HoursTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Log Volunteer Hours</h3>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Volunteer</label>
            <select
              value={hoursVolunteerId ?? ''}
              onChange={(e) => onHoursVolunteerIdChange(Number(e.target.value) || null)}
              className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <option value="">Select volunteer...</option>
              {volunteers.filter((v) => v.status === 'active').map((v) => (
                <option key={v.id} value={v.id}>{v.user_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Date</label>
            <input
              type="date"
              value={hoursDate}
              onChange={(e) => onHoursDateChange(e.target.value)}
              className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Hours</label>
            <input
              type="number"
              step="0.25"
              min="0"
              max="24"
              value={hoursCount}
              onChange={(e) => onHoursCountChange(e.target.value)}
              placeholder={t('placeholder.homeDeliveryVolunteers.eg25')}
              className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Activity Type</label>
            <select
              value={hoursActivityType}
              onChange={(e) => onHoursActivityTypeChange(e.target.value)}
              className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <option value="delivery">Delivery</option>
              <option value="packing">Packing</option>
              <option value="training">Training</option>
              <option value="item_selection">Item Selection</option>
              <option value="admin">Admin</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
        <div className="mt-3">
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes</label>
          <input
            type="text"
            value={hoursNotes}
            onChange={(e) => onHoursNotesChange(e.target.value)}
            placeholder={t('placeholder.staff.optionalNotes')}
            className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>
        <div className="mt-3 flex justify-end">
          <button
            onClick={() => {
              if (!hoursVolunteerId || !hoursDate || !hoursCount) {
                toast.error(t('homeDeliveryVolunteers.pleaseFillInAllRequired'));
                return;
              }
              logHoursMutation.mutate();
            }}
            disabled={logHoursMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
          >
            {logHoursMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Plus className="w-4 h-4" />
            Log Hours
          </button>
        </div>
      </div>

      {hoursVolunteerId && hoursData && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
            <div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                Hours for {volunteers.find((v) => v.id === hoursVolunteerId)?.user_name}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Total: <span className="font-bold text-lsc-rose">{hoursData.total_hours}h</span>
              </p>
            </div>
          </div>
          {hoursData.logs.length === 0 ? (
            <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>{t('homeDeliveryVolunteers.noHoursLoggedYet')}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Date</th>
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Hours</th>
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Activity</th>
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Notes</th>
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Verified</th>
                    <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {hoursData.logs.map((log) => (
                    <tr key={log.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                      <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">{formatDate(log.date)}</td>
                      <td className="px-4 py-2 font-medium text-lsc-dark dark:text-lsc-cream">{log.hours}h</td>
                      <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                        {log.activity_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">{log.notes ?? '—'}</td>
                      <td className="px-4 py-2">
                        {log.verified ? (
                          <span className="inline-flex items-center gap-1 text-status-success-600 dark:text-status-success-400 text-xs">
                            <CheckCircle className="w-3.5 h-3.5" /> Verified
                          </span>
                        ) : (
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Unverified</span>
                        )}
                      </td>
                      <td className="px-4 py-2">
                        {!log.verified && (
                          <button
                            onClick={() => verifyHoursMutation.mutate(log.id)}
                            disabled={verifyHoursMutation.isPending}
                            className="px-2 py-1 text-xs bg-status-success-600 hover:bg-status-success-700 text-white rounded"
                          >
                            Verify
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!hoursVolunteerId && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Volunteer Hours Summary</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('homeDeliveryVolunteers.selectAVolunteerAboveTo')}</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-700/50">
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Volunteer</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Hours</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Total Deliveries</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Recognition</th>
                  <th className="px-4 py-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {volunteers.map((volunteer) => (
                  <tr key={volunteer.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                    <td className="px-4 py-3">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{volunteer.user_name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <VolunteerStatusBadge status={volunteer.status} />
                    </td>
                    <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">
                      {volunteer.total_volunteer_hours}h
                    </td>
                    <td className="px-4 py-3 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {volunteer.total_deliveries}
                    </td>
                    <td className="px-4 py-3">
                      <RecognitionBadge level={volunteer.recognition_level} />
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => { onHoursVolunteerIdChange(volunteer.id); }}
                        className="px-2 py-1 text-xs bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded"
                      >
                        View Hours
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {volunteers.length === 0 && (
              <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">No volunteers found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
