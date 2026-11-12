/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Plus, X, Loader2 } from 'lucide-react';
import FocusTrap from 'focus-trap-react';
import toast from 'react-hot-toast';
import { useTranslation } from '@/i18n';
import { medicalEmergencyApi } from './medical-emergency-api';

interface EmergencyTriggerFormProps {
  onSuccess: () => void;
}

export default function EmergencyTriggerModal({ onSuccess }: EmergencyTriggerFormProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Store trigger element on open and restore focus on close
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement;
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
      previousActiveElement.current?.focus();
      previousActiveElement.current = null;
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);
  const [emergencyType, setEmergencyType] = useState('medical_emergency');
  const [location, setLocation] = useState('');
  const [patronId, setPatronId] = useState('');
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [consciousness, setConsciousness] = useState('alert');
  const [notes, setNotes] = useState('');

  const triggerMutation = useMutation({
    mutationFn: () =>
      medicalEmergencyApi.triggerEmergency({
        emergency_type: emergencyType,
        location,
        patron_id: patronId ? parseInt(patronId) : null,
        medical_context: {
          symptoms,
          consciousness_level: consciousness,
          ...(notes && { notes }),
        },
      }),
    onSuccess: () => {
      toast.success(t('staffMedicalEmergency.medicalEmergencyAlertTriggered'));
      setIsOpen(false);
      onSuccess();
    },
    onError: () => {
      toast.error(t('staffMedicalEmergency.failedToTriggerEmergencyAlert'));
    },
  });

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="bg-status-danger-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-status-danger-700 flex items-center gap-2"
      >
        <Plus className="w-5 h-5" />
        Trigger Medical Emergency
      </button>
    );
  }

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onKeyDown={(e) => { if (e.key === 'Escape') setIsOpen(false); }}
      >
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-labelledby="emergency-trigger-modal-title"
      >
        <div className="flex justify-between items-center mb-4">
          <h3 id="emergency-trigger-modal-title" className="font-serif text-lg font-semibold text-status-danger-700 dark:text-status-danger-300">{t('staffMedicalEmergency.triggerMedicalEmergencyAlert')}</h3>
          <button
            onClick={() => setIsOpen(false)}
            className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-6 h-6" aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Emergency Type</label>
            <select
              value={emergencyType}
              onChange={(e) => setEmergencyType(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="medical_emergency">General Medical Emergency</option>
              <option value="cardiac_event">{t('staffMedicalEmergency.cardiacEventHeartAttackArrhythmia')}</option>
              <option value="respiratory_distress">{t('staffMedicalEmergency.respiratoryDistressChokingAsthma')}</option>
              <option value="severe_injury">{t('staffMedicalEmergency.severeInjuryTraumaBleeding')}</option>
              <option value="allergic_reaction">Allergic Reaction</option>
              <option value="unconscious_unresponsive">Unconscious/Unresponsive</option>
              <option value="acute_mental_health">{t('staffMedicalEmergency.acuteMentalHealthCrisis')}</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Location</label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder={t('placeholder.staffMedicalEmergency.egMainBranchReading')}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{t('staffMedicalEmergency.patronIdIfKnown')}</label>
            <input
              type="number"
              value={patronId}
              onChange={(e) => setPatronId(e.target.value)}
              placeholder={t('staffMedicalEmergency.leaveBlankIfUnknown')}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Consciousness Level</label>
            <select
              value={consciousness}
              onChange={(e) => setConsciousness(e.target.value)}
              className="w-full border rounded px-3 py-2"
            >
              <option value="alert">Alert & Responsive</option>
              <option value="responsive">{t('staffMedicalEmergency.responsiveToPainVoice')}</option>
              <option value="unresponsive">Unresponsive</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Observed Symptoms</label>
            <div className="space-y-2">
              {['Chest pain', 'Difficulty breathing', 'Bleeding', 'Severe injury', 'Loss of consciousness'].map(
                (symptom) => (
                  <label key={symptom} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={symptoms.includes(symptom)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSymptoms([...symptoms, symptom]);
                        } else {
                          setSymptoms(symptoms.filter((s) => s !== symptom));
                        }
                      }}
                      className="rounded"
                    />
                    {symptom}
                  </label>
                )
              )}
            </div>
          </div>

          <div>
            <label className="block font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Additional Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={t('staffMedicalEmergency.anyOtherRelevantInformationFor')}
              className="w-full border rounded px-3 py-2 h-20"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => triggerMutation.mutate()}
              disabled={!location || triggerMutation.isPending}
              className="flex-1 bg-status-danger-600 text-white py-2 rounded font-semibold hover:bg-status-danger-700 disabled:opacity-50"
            >
              {triggerMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin inline mr-2" />
                  Triggering...
                </>
              ) : (
                '🚨 TRIGGER EMERGENCY ALERT'
              )}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="px-4 py-2 border rounded hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
      </div>
    </FocusTrap>
  );
}
