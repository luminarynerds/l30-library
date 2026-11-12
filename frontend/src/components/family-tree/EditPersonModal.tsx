/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { personsApi, type Person } from '@/api/genealogy-research-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop';

interface EditPersonModalProps {
  projectId: number;
  person: Person;
  onClose: () => void;
  onSaved: () => void;
}

export function EditPersonModal({ projectId, person, onClose, onSaved }: EditPersonModalProps) {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    given_names: person.given_names,
    surname: person.surname || '',
    maiden_name: person.maiden_name || '',
    birth_date: person.birth_date || '',
    birth_place: person.birth_place || '',
    death_date: person.death_date || '',
    death_place: person.death_place || '',
    gender: person.gender || '',
    is_living: person.is_living,
    occupation: person.occupation || '',
    biography: person.biography || '',
    confidence_level: person.confidence_level,
  });
  const [saving, setSaving] = useState(false);

  async function handleSubmit() {
    try {
      setSaving(true);
      await personsApi.update(projectId, person.id, formData as Partial<Person>);
      toast.success(t('toast.familyTree.personUpdated'));
      onSaved();
    } catch {
      toast.error(t('familyTree.failedToUpdatePerson'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Edit Person">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">Edit Person</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Given Names *</label>
              <input type="text" value={formData.given_names} onChange={e => setFormData(p => ({ ...p, given_names: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Surname</label>
              <input type="text" value={formData.surname} onChange={e => setFormData(p => ({ ...p, surname: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Gender</label>
            <select value={formData.gender} onChange={e => setFormData(p => ({ ...p, gender: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
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
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Birth Date</label>
              <input type="text" value={formData.birth_date} onChange={e => setFormData(p => ({ ...p, birth_date: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Birth Place</label>
              <input type="text" value={formData.birth_place} onChange={e => setFormData(p => ({ ...p, birth_place: e.target.value }))}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          {!formData.is_living && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Death Date</label>
                <input type="text" value={formData.death_date} onChange={e => setFormData(p => ({ ...p, death_date: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Death Place</label>
                <input type="text" value={formData.death_place} onChange={e => setFormData(p => ({ ...p, death_place: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Occupation</label>
            <input type="text" value={formData.occupation} onChange={e => setFormData(p => ({ ...p, occupation: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Biography</label>
            <textarea value={formData.biography} onChange={e => setFormData(p => ({ ...p, biography: e.target.value }))}
              rows={3} className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button onClick={handleSubmit} disabled={!formData.given_names.trim() || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium">
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
