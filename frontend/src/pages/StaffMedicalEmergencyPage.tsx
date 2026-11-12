/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { medicalEmergencyApi } from '../components/medical-emergency/medical-emergency-api';
import EmergencyTriggerModal from '../components/medical-emergency/EmergencyTriggerModal';
import ActiveEmergencyCard from '../components/medical-emergency/ActiveEmergencyCard';
import ResourcesTab from '../components/medical-emergency/ResourcesTab';
import GuidesTab from '../components/medical-emergency/GuidesTab';
import type { MedicalEmergencyAlert } from '../components/medical-emergency/types';

export default function StaffMedicalEmergencyPage() {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user: _user, isLoading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'emergencies' | 'resources' | 'guides'>('emergencies');

  const { data: activeEmergencies, isLoading: emergenciesLoading, refetch: refetchEmergencies } = useQuery({
    queryKey: ['activeEmergencies'],
    queryFn: () => medicalEmergencyApi.getActiveEmergencies(undefined),
    refetchInterval: 10000,
  });

  const { data: trainedStaff, isLoading: staffLoading } = useQuery({
    queryKey: ['trainedStaff'],
    queryFn: () => medicalEmergencyApi.getTrainedStaff(undefined),
    enabled: activeTab === 'resources',
  });

  const { data: aeds, isLoading: aedsLoading } = useQuery({
    queryKey: ['aedLocations'],
    queryFn: () => medicalEmergencyApi.getAEDLocations(undefined),
    enabled: activeTab === 'resources',
  });

  const { data: firstAidKits, isLoading: kitsLoading } = useQuery({
    queryKey: ['firstAidKits'],
    queryFn: () => medicalEmergencyApi.getFirstAidKits(undefined),
    enabled: activeTab === 'resources',
  });

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin" />
      </div>
    );
  }

  return (
    <AdminShell title={t('staffMedicalEmergency.medicalEmergencyResponseSystem')}>
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('staffMedicalEmergency.medicalEmergencyResponseSystem2')}</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Coordinated medical emergency response with staff training, equipment locations, and patron medical info
            </p>
          </div>

          <div className="flex gap-2 mb-6 border-b">
            {(['emergencies', 'resources', 'guides'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 font-semibold border-b-2 transition ${
                  activeTab === tab
                    ? 'border-status-danger-600 text-status-danger-600'
                    : 'border-transparent text-earth-600 hover:text-lsc-dark dark:text-lsc-cream dark:hover:text-earth-100'
                }`}
              >
                {tab === 'emergencies' && '🚨 Active Emergencies'}
                {tab === 'resources' && '📍 Resources'}
                {tab === 'guides' && '📖 Guides & Training'}
              </button>
            ))}
          </div>

          {activeTab === 'emergencies' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">Active Medical Emergencies</h2>
                  {activeEmergencies && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                      {activeEmergencies.total_active} active
                      {activeEmergencies.life_threatening_count > 0 &&
                        ` (${activeEmergencies.life_threatening_count} life-threatening)`}
                    </p>
                  )}
                </div>
                <EmergencyTriggerModal onSuccess={() => refetchEmergencies()} />
              </div>

              {emergenciesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin" />
                </div>
              ) : activeEmergencies && activeEmergencies.total_active > 0 ? (
                <div className="grid gap-4">
                  {activeEmergencies.emergencies.map((alert: MedicalEmergencyAlert) => (
                    <ActiveEmergencyCard key={alert.id} alert={alert} onRefresh={() => refetchEmergencies()} />
                  ))}
                </div>
              ) : (
                <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-8 text-center">
                  <CheckCircle2 className="w-12 h-12 text-status-success-600 mx-auto mb-3" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('staffMedicalEmergency.noActiveMedicalEmergencies')}</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'resources' && (
            <ResourcesTab
              trainedStaff={trainedStaff}
              staffLoading={staffLoading}
              aeds={aeds}
              aedsLoading={aedsLoading}
              firstAidKits={firstAidKits}
              kitsLoading={kitsLoading}
            />
          )}

          {activeTab === 'guides' && <GuidesTab />}
        </div>
    </AdminShell>
  );
}
