/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Users, Zap, Home } from 'lucide-react';
import { useTranslation } from '@/i18n';
import type { TrainedStaff, AEDLocation, FirstAidKit } from './types';

interface ResourcesTabProps {
  trainedStaff: TrainedStaff[] | undefined;
  staffLoading: boolean;
  aeds: AEDLocation[] | undefined;
  aedsLoading: boolean;
  firstAidKits: FirstAidKit[] | undefined;
  kitsLoading: boolean;
}

export default function ResourcesTab({
  trainedStaff,
  staffLoading,
  aeds,
  aedsLoading,
  firstAidKits,
  kitsLoading,
}: ResourcesTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border p-6">
        <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Users className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          Staff with Medical Training
        </h3>

        {staffLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
          </div>
        ) : trainedStaff && trainedStaff.length > 0 ? (
          <div className="space-y-2">
            {trainedStaff.map((staff: TrainedStaff) => (
              <div key={staff.id} className="p-3 bg-earth-50 dark:bg-earth-800/20 rounded border border-lsc-border dark:border-earth-700">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{staff.name}</p>
                    <div className="flex gap-2 flex-wrap mt-1">
                      {staff.qualifications.map((q: string) => (
                        <span key={q} className="bg-earth-200 text-earth-800 dark:text-lsc-rose-light text-xs px-2 py-1 rounded">
                          {q}
                        </span>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{staff.phone}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffMedicalEmergency.noStaffWithMedicalTraining')}</p>
        )}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border p-6">
        <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Zap className="w-6 h-6 text-status-warning-600" />
          AED (Automated External Defibrillator) Locations
        </h3>

        {aedsLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
          </div>
        ) : aeds && aeds.length > 0 ? (
          <div className="space-y-2">
            {aeds.map((aed: AEDLocation) => (
              <div key={aed.id} className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 rounded border border-status-warning-200 dark:border-status-warning-800">
                <div>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{aed.location_description}</p>
                  {aed.room_number && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Room: {aed.room_number}</p>}
                  {aed.access_instructions && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      <strong>Access:</strong> {aed.access_instructions}
                    </p>
                  )}
                  <div className="flex gap-2 mt-2 text-xs">
                    {aed.visible_signage && (
                      <span className="bg-status-warning-200 text-status-warning-800 dark:text-status-warning-300 px-2 py-1 rounded">✓ Visible Signage</span>
                    )}
                    {aed.directional_signage && (
                      <span className="bg-status-warning-200 text-status-warning-800 dark:text-status-warning-300 px-2 py-1 rounded">✓ Directional Signs</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffMedicalEmergency.noAedLocationsRegistered')}</p>
        )}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border p-6">
        <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Home className="w-6 h-6 text-status-success-600" />
          First Aid Kit Locations
        </h3>

        {kitsLoading ? (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
          </div>
        ) : firstAidKits && firstAidKits.length > 0 ? (
          <div className="space-y-2">
            {firstAidKits.map((kit: FirstAidKit) => (
              <div key={kit.id} className="p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded border border-status-success-200 dark:border-status-success-800">
                <div>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{kit.location_description}</p>
                  {kit.room_number && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Room: {kit.room_number}</p>}
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Type: {kit.kit_type}</p>
                  {kit.access_instructions && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      <strong>Access:</strong> {kit.access_instructions}
                    </p>
                  )}
                  {kit.staff_trained && (
                    <p className="text-xs text-status-success-700 dark:text-status-success-300 mt-1">✓ Staff trained on this kit</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffMedicalEmergency.noFirstAidKitLocations')}</p>
        )}
      </div>
    </div>
  );
}
