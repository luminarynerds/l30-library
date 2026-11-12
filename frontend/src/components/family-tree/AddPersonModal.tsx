/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { personsApi, type Person } from '@/api/genealogy-research-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop';

interface AddPersonModalProps {
  projectId: number;
  onClose: () => void;
  onCreated: () => void;
}

export function AddPersonModal({ projectId, onClose, onCreated }: AddPersonModalProps) {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    given_names: '',
    surname: '',
    maiden_name: '',
    birth_date: '',
    birth_place: '',
    death_date: '',
    death_place: '',
    gender: '',
    is_living: false,
    occupation: '',
    biography: '',
    confidence_level: 3,
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit() {
    if (!formData.given_names.trim()) return;
    try {
      setSaving(true);
      await personsApi.create(projectId, {
        ...formData,
        ...(formData.gender ? {} : { gender: undefined }),
      } as Partial<Person>);
      toast.success(t('familyTree.personAddedToTree'));
      onCreated();
    } catch {
      toast.error(t('familyTree.failedToAddPerson'));
    } finally {
      setSaving(false);
    }
  }

  const field = (label: string, key: keyof typeof formData, type = 'text', placeholder = '') => (
    <div>
      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{label}</label>
      <input
        type={type}
        value={formData[key] as string}
        onChange={e => setFormData(p => ({ ...p, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm"
      />
    </div>
  );

  return (
    <ModalBackdrop onClose={onClose} title="Add Person">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">Add Person</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {field('Given Names *', 'given_names', 'text', 'First and middle names')}
            {field('Surname', 'surname', 'text', 'Family name')}
          </div>
          {field('Maiden Name', 'maiden_name', 'text', 'Birth surname if changed')}
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Gender</label>
            <select
              value={formData.gender}
              onChange={e => setFormData(p => ({ ...p, gender: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm"
            >
              <option value="">Not recorded</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="nonbinary">Nonbinary</option>
              <option value="other">Another gender / not listed</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <input type="checkbox" checked={formData.is_living} onChange={e => setFormData(p => ({ ...p, is_living: e.target.checked }))} className="rounded" />
            Person is living
          </label>
          <div className="grid grid-cols-2 gap-3">
            {field('Birth Date', 'birth_date', 'text', 'e.g., 15 Mar 1845')}
            {field('Birth Place', 'birth_place', 'text', 'City, County, Country')}
          </div>
          {!formData.is_living && (
            <div className="grid grid-cols-2 gap-3">
              {field('Death Date', 'death_date', 'text', 'e.g., 20 Jun 1912')}
              {field('Death Place', 'death_place', 'text', 'City, County, Country')}
            </div>
          )}
          {field('Occupation', 'occupation', 'text', 'Primary occupation or profession')}
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Biography</label>
            <textarea
              value={formData.biography}
              onChange={e => setFormData(p => ({ ...p, biography: e.target.value }))}
              rows={3}
              placeholder={t('familyTree.briefBiographyOrNotableFacts')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Data Confidence (1–5)
            </label>
            <input
              type="range" min={1} max={5} value={formData.confidence_level}
              onChange={e => setFormData(p => ({ ...p, confidence_level: Number(e.target.value) }))}
              className="w-full accent-status-warning-500"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {['', 'Very uncertain', 'Somewhat uncertain', 'Moderate confidence', 'High confidence', 'Verified/Proven'][formData.confidence_level]}
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button
            onClick={handleSubmit}
            disabled={!formData.given_names.trim() || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium"
          >
            {saving ? 'Adding...' : 'Add Person'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
