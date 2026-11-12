/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2, Plus } from 'lucide-react';
import { UseMutationResult } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { formatDate } from './volunteers-data';
import toast from 'react-hot-toast';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ScheduleEntry {
  id: number;
  date: string;
  is_available: boolean;
  time_start?: string | null;
  time_end?: string | null;
}

interface ScheduleModalProps {
  scheduleVolunteerId: number;
  scheduleDate: string;
  scheduleIsAvailable: boolean;
  scheduleStartTime: string;
  scheduleEndTime: string;
  scheduleData: ScheduleEntry[] | undefined;
  createScheduleMutation: UseMutationResult<unknown, Error, void>;
  deleteScheduleMutation: UseMutationResult<unknown, Error, { volunteerId: number; date: string }>;
  onClose: () => void;
  onScheduleDateChange: (v: string) => void;
  onScheduleIsAvailableChange: (v: boolean) => void;
  onScheduleStartTimeChange: (v: string) => void;
  onScheduleEndTimeChange: (v: string) => void;
}

export function ScheduleModal({
  scheduleVolunteerId,
  scheduleDate,
  scheduleIsAvailable,
  scheduleStartTime,
  scheduleEndTime,
  scheduleData,
  createScheduleMutation,
  deleteScheduleMutation,
  onClose,
  onScheduleDateChange,
  onScheduleIsAvailableChange,
  onScheduleStartTimeChange,
  onScheduleEndTimeChange,
}: ScheduleModalProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Manage Schedule">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Manage Schedule</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="mb-4 p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg space-y-3">
            <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Add Schedule Entry</h4>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Date</label>
                <input
                  type="date"
                  value={scheduleDate}
                  onChange={(e) => onScheduleDateChange(e.target.value)}
                  className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={scheduleIsAvailable}
                    onChange={(e) => onScheduleIsAvailableChange(e.target.checked)}
                    className="rounded border-lsc-border text-lsc-rose"
                  />
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream">Available</span>
                </label>
              </div>
            </div>
            {scheduleIsAvailable && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Start Time</label>
                  <input
                    type="time"
                    value={scheduleStartTime}
                    onChange={(e) => onScheduleStartTimeChange(e.target.value)}
                    className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">End Time</label>
                  <input
                    type="time"
                    value={scheduleEndTime}
                    onChange={(e) => onScheduleEndTimeChange(e.target.value)}
                    className="w-full px-2 py-1.5 bg-lsc-white dark:bg-earth-600 border border-lsc-border dark:border-earth-700 rounded text-sm text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </div>
            )}
            <button
              onClick={() => {
                if (!scheduleDate) { toast.error(t('homeDeliveryVolunteers.pleaseSelectADate')); return; }
                createScheduleMutation.mutate();
              }}
              disabled={createScheduleMutation.isPending}
              className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded text-sm font-medium"
            >
              {createScheduleMutation.isPending && <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />}
              <Plus className="w-3.5 h-3.5" />
              Add Entry
            </button>
          </div>

          {scheduleData && scheduleData.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Next 30 Days</h4>
              {scheduleData.map((entry) => (
                <div key={entry.id} className="flex items-center justify-between p-2 bg-lsc-cream dark:bg-earth-700/50 rounded-lg">
                  <div>
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatDate(entry.date)}
                    </span>
                    {entry.is_available ? (
                      <span className="ml-2 text-xs text-status-success-600 dark:text-status-success-400">
                        Available
                        {entry.time_start && ` (${entry.time_start}${entry.time_end ? ` – ${entry.time_end}` : ''})`}
                      </span>
                    ) : (
                      <span className="ml-2 text-xs text-status-danger-600 dark:text-status-danger-400">Unavailable</span>
                    )}
                  </div>
                  <button
                    onClick={() => deleteScheduleMutation.mutate({ volunteerId: scheduleVolunteerId, date: entry.date })}
                    className="p-1 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-500 rounded"
                    title="Remove entry"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4">
              No schedule entries for the next 30 days
            </p>
          )}

          <div className="flex justify-end mt-4">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
