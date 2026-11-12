/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2, CheckCircle } from 'lucide-react';
import { UseMutationResult } from '@tanstack/react-query';
import { DeliveryVolunteer } from '../../../api/homeDeliveryApi';
import { useTranslation } from '@/i18n';
import { formatDate } from './volunteers-data';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface HoursLog {
  id: number;
  date: string;
  hours: number;
  activity_type: string;
  verified: boolean;
}

interface HoursData {
  total_hours: number;
  logs: HoursLog[];
}

interface HoursModalProps {
  hoursVolunteerId: number;
  volunteers: DeliveryVolunteer[];
  hoursData: HoursData | undefined;
  verifyHoursMutation: UseMutationResult<unknown, Error, number>;
  onClose: () => void;
}

export function HoursModal({
  hoursVolunteerId,
  volunteers,
  hoursData,
  verifyHoursMutation,
  onClose,
}: HoursModalProps) {
  const { t } = useTranslation();
  const volunteerName = volunteers.find((v) => v.id === hoursVolunteerId)?.user_name;

  return (
    <ModalBackdrop onClose={onClose} title="Volunteer Hours">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              Hours for {volunteerName}
            </h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          {hoursData ? (
            <div>
              <div className="p-3 bg-lsc-rose/10 rounded-lg mb-4">
                <p className="text-center">
                  <span className="text-3xl font-bold text-lsc-rose">{hoursData.total_hours}</span>
                  <span className="text-lsc-dark/70 dark:text-lsc-cream/70 ml-2">total hours</span>
                </p>
              </div>
              {hoursData.logs.length === 0 ? (
                <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-4">{t('homeDeliveryVolunteers.noHoursLoggedYet2')}</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {hoursData.logs.map((log) => (
                    <div key={log.id} className="flex items-center justify-between p-2 bg-lsc-cream dark:bg-earth-700/50 rounded-lg text-sm">
                      <div>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{formatDate(log.date)}</span>
                        <span className="ml-2 text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">{log.activity_type.replace(/_/g, ' ')}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{log.hours}h</span>
                        {log.verified ? (
                          <CheckCircle className="w-4 h-4 text-status-success-500" />
                        ) : (
                          <button
                            onClick={() => verifyHoursMutation.mutate(log.id)}
                            className="px-2 py-0.5 text-xs bg-status-success-600 text-white rounded"
                          >
                            Verify
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex justify-center py-4">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
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
