/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { relationshipsApi, type PersonSummary } from '@/api/genealogy-research-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop';

type RelationshipType = 'parent' | 'child' | 'spouse' | 'sibling';

interface AddRelationshipModalProps {
  projectId: number;
  anchorPersonId: number;
  persons: PersonSummary[];
  onClose: () => void;
  onCreated: () => void;
}

export function AddRelationshipModal({ projectId, anchorPersonId, persons, onClose, onCreated }: AddRelationshipModalProps) {
  const { t } = useTranslation();
  const anchor = persons.find(p => p.id === anchorPersonId);
  const [targetPersonId, setTargetPersonId] = useState('');
  const [relationshipType, setRelationshipType] = useState<RelationshipType>('parent');
  const [marriageDate, setMarriageDate] = useState('');
  const [marriagePlace, setMarriagePlace] = useState('');
  const [saving, setSaving] = useState(false);

  const relationshipOptions: { value: RelationshipType; label: string; desc: string }[] = [
    { value: 'parent', label: 'Parent', desc: 'This person is a parent of the one you are editing' },
    { value: 'child', label: 'Child', desc: 'This person is a child of the one you are editing' },
    { value: 'spouse', label: 'Spouse / Partner', desc: 'Married to or partnered with this person' },
    { value: 'sibling', label: 'Sibling', desc: 'This person and the one you are editing share a parent' },
  ];

  async function handleSubmit() {
    if (!targetPersonId) return;
    try {
      setSaving(true);
      await relationshipsApi.create(projectId, {
        person1_id: anchorPersonId,
        person2_id: Number(targetPersonId),
        relationship_type: relationshipType,
        ...(relationshipType === 'spouse' && marriageDate ? { marriage_date: marriageDate } : {}),
        ...(relationshipType === 'spouse' && marriagePlace ? { marriage_place: marriagePlace } : {}),
      });
      toast.success(t('toast.familyTree.relationshipCreated'));
      onCreated();
    } catch {
      toast.error(t('familyTree.failedToCreateRelationship'));
    } finally {
      setSaving(false);
    }
  }

  const otherPersons = persons.filter(p => p.id !== anchorPersonId);

  return (
    <ModalBackdrop onClose={onClose} title="Add Relationship">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full p-6">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">Add Relationship</h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Relating to: <span className="font-medium text-lsc-dark dark:text-lsc-cream">
            {anchor ? `${anchor.given_names} ${anchor.surname || ''}`.trim() : `Person #${anchorPersonId}`}
          </span>
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Relationship Type</label>
            <div className="space-y-2">
              {relationshipOptions.map(opt => (
                <label key={opt.value} className="flex items-start gap-3 p-2.5 rounded-lg border cursor-pointer hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 transition-colors"
                  style={{ borderColor: relationshipType === opt.value ? 'var(--accent-rose)' : undefined }}>
                  <input type="radio" value={opt.value} checked={relationshipType === opt.value}
                    onChange={() => setRelationshipType(opt.value)} className="mt-0.5 accent-status-warning-500" />
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{opt.label}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Select Person</label>
            <select value={targetPersonId} onChange={e => setTargetPersonId(e.target.value)}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              <option value="">Choose a person...</option>
              {otherPersons.map(p => (
                <option key={p.id} value={p.id}>
                  {p.given_names} {p.surname || ''} {p.birth_date ? `(b. ${p.birth_date})` : ''}
                </option>
              ))}
            </select>
          </div>

          {relationshipType === 'spouse' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Marriage Date</label>
                <input type="text" value={marriageDate} onChange={e => setMarriageDate(e.target.value)}
                  placeholder={t('placeholder.familyTree.eg12Jun1878')}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Marriage Place</label>
                <input type="text" value={marriagePlace} onChange={e => setMarriagePlace(e.target.value)}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button onClick={handleSubmit} disabled={!targetPersonId || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium">
            {saving ? 'Creating...' : 'Create Relationship'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
