/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Phone, BookOpen, CheckCircle2, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from '@/i18n';
import { medicalEmergencyApi } from './medical-emergency-api';
import { getEmergencyIcon, getSeverityColor } from './EmergencyHelpers';
import type { MedicalEmergencyAlert } from './types';

interface ActiveEmergencyCardProps {
  alert: MedicalEmergencyAlert;
  onRefresh: () => void;
}

export default function ActiveEmergencyCard({ alert, onRefresh }: ActiveEmergencyCardProps) {
  const { t } = useTranslation();
  const [showPackage, setShowPackage] = useState(false);
  const [showResolve, setShowResolve] = useState(false);

  const { data: responsePackage, isLoading } = useQuery({
    queryKey: ['emergencyResponsePackage', alert.id],
    queryFn: () => medicalEmergencyApi.getResponsePackage(alert.id),
    enabled: showPackage,
  });

  const call911Mutation = useMutation({
    mutationFn: () => medicalEmergencyApi.callEmergencyServices(alert.id, 5),
    onSuccess: () => {
      toast.success(t('toast.staffMedicalEmergency.911CalledEta5Minutes'));
      onRefresh();
    },
    onError: () => toast.error(t('toast.staffMedicalEmergency.failedToCall911')),
  });

  const resolveMutation = useMutation({
    mutationFn: (status: string) => medicalEmergencyApi.resolveEmergency(alert.id, status),
    onSuccess: () => {
      toast.success(t('toast.staffMedicalEmergency.emergencyResolved'));
      setShowResolve(false);
      onRefresh();
    },
    onError: () => toast.error(t('staffMedicalEmergency.failedToResolveEmergency')),
  });

  return (
    <div className={`border-2 rounded-lg p-4 ${getSeverityColor(alert.severity)}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3">
          {getEmergencyIcon(alert.emergency_type)}
          <div>
            <h4 className="font-serif font-semibold capitalize">{alert.emergency_type.replace(/_/g, ' ')}</h4>
            <p className="text-sm opacity-75">{alert.location}</p>
          </div>
        </div>
        <span className="text-xs font-semibold px-2 py-1 bg-lsc-white dark:bg-earth-800/50 rounded">
          {new Date(alert.created_at).toLocaleTimeString()}
        </span>
      </div>

      {alert.caller_description && (
        <p className="text-sm mb-3 italic">"{ alert.caller_description}"</p>
      )}

      <div className="flex gap-2 flex-wrap mb-3">
        {!alert.emergency_services_called && (
          <button
            onClick={() => call911Mutation.mutate()}
            disabled={call911Mutation.isPending}
            className="flex items-center gap-1 bg-status-danger-600 text-white text-sm px-3 py-1 rounded font-semibold hover:bg-status-danger-700"
          >
            <Phone className="w-4 h-4" />
            {call911Mutation.isPending ? 'Calling...' : 'Call 911'}
          </button>
        )}

        {alert.emergency_services_called && (
          <span className="flex items-center gap-1 bg-status-danger-600 text-white text-sm px-3 py-1 rounded font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            911 Called
          </span>
        )}

        <button
          onClick={() => setShowPackage(!showPackage)}
          className="flex items-center gap-1 bg-lsc-rose text-white text-sm px-3 py-1 rounded hover:bg-lsc-rose/90"
        >
          <BookOpen className="w-4 h-4" />
          Response Package
        </button>

        <button
          onClick={() => setShowResolve(!showResolve)}
          className="flex items-center gap-1 bg-status-success-600 text-white text-sm px-3 py-1 rounded hover:bg-status-success-700"
        >
          <CheckCircle2 className="w-4 h-4" />
          Resolve
        </button>
      </div>

      {showResolve && (
        <div className="mt-3 p-3 bg-lsc-white dark:bg-earth-800/50 rounded space-y-2">
          <button
            onClick={() => resolveMutation.mutate('stabilized')}
            className="w-full bg-status-warning-600 text-white py-1 rounded hover:bg-status-warning-700 text-sm"
          >
            Stabilized
          </button>
          <button
            onClick={() => resolveMutation.mutate('transferred')}
            className="w-full bg-lsc-rose text-white py-1 rounded hover:bg-lsc-rose/90 text-sm"
          >
            Transferred to Hospital
          </button>
          <button
            onClick={() => resolveMutation.mutate('resolved')}
            className="w-full bg-status-success-600 text-white py-1 rounded hover:bg-status-success-700 text-sm"
          >
            Resolved / No Longer Needed
          </button>
        </div>
      )}

      {showPackage && isLoading && (
        <div className="mt-3 flex items-center justify-center gap-2 text-sm">
          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          Loading response package...
        </div>
      )}

      {showPackage && responsePackage && (
        <div className="mt-3 space-y-3 text-sm bg-lsc-white dark:bg-earth-800/50 p-3 rounded">
          {responsePackage.patron_medical_info && (
            <div className="border-b pb-2">
              <h5 className="font-semibold mb-1">⚠️ Patron Medical Info:</h5>
              {responsePackage.patron_medical_info.allergies && (
                <p><strong>Allergies:</strong> {responsePackage.patron_medical_info.allergies}</p>
              )}
              {responsePackage.patron_medical_info.medical_conditions && (
                <p><strong>Conditions:</strong> {responsePackage.patron_medical_info.medical_conditions}</p>
              )}
              {responsePackage.patron_medical_info.medications && (
                <p><strong>Medications:</strong> {responsePackage.patron_medical_info.medications}</p>
              )}
            </div>
          )}

          {responsePackage.nearest_aeds.length > 0 && (
            <div className="border-b pb-2">
              <h5 className="font-semibold mb-1">⚡ Nearest AEDs:</h5>
              {responsePackage.nearest_aeds.slice(0, 2).map((aed) => (
                <p key={aed.id}><strong>{aed.location_description}</strong> {aed.access_instructions}</p>
              ))}
            </div>
          )}

          {responsePackage.trained_staff.length > 0 && (
            <div className="border-b pb-2">
              <h5 className="font-semibold mb-1">👥 Trained Staff Available:</h5>
              {responsePackage.trained_staff.slice(0, 3).map((staff) => (
                <p key={staff.id}>{staff.name} - {staff.qualifications.join(', ')}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
