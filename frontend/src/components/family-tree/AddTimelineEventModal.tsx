/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react';
import toast from 'react-hot-toast';
import { timelineApi, type TimelineEvent } from '@/api/genealogy-research-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop';

interface AddTimelineEventModalProps {
  projectId: number;
  personId: number;
  onClose: () => void;
  onCreated: () => void;
}

export function AddTimelineEventModal({ projectId, personId, onClose, onCreated }: AddTimelineEventModalProps) {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    event_type: 'birth',
    title: '',
    description: '',
    event_date: '',
    location: '',
  });
  const [saving, setSaving] = useState(false);

  const eventTypes = [
    'birth', 'death', 'marriage', 'divorce', 'immigration', 'emigration',
    'military_service', 'education', 'occupation', 'residence', 'religious', 'other'
  ];

  async function handleSubmit() {
    if (!formData.title.trim()) return;
    try {
      setSaving(true);
      await timelineApi.createEvent(projectId, {
        person_id: personId,
        project_id: projectId,
        ...formData,
      } as Partial<TimelineEvent>);
      toast.success(t('familyTree.eventAddedToTimeline'));
      onCreated();
    } catch {
      toast.error(t('familyTree.failedToAddEvent'));
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Add Timeline Event">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full p-6">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">Add Timeline Event</h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Event Type</label>
            <select value={formData.event_type} onChange={e => setFormData(p => ({ ...p, event_type: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              {eventTypes.map(type => <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
            <input type="text" value={formData.title} onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
              placeholder={t('placeholder.familyTree.egBornInCounty')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Date</label>
              <input type="text" value={formData.event_date} onChange={e => setFormData(p => ({ ...p, event_date: e.target.value }))}
                placeholder={t('placeholder.familyTree.eg15Mar1845')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Location</label>
              <input type="text" value={formData.location} onChange={e => setFormData(p => ({ ...p, location: e.target.value }))}
                placeholder={t('placeholder.familyTree.cityCountyCountry')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
            <textarea value={formData.description} onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
              rows={2} placeholder={t('placeholder.familyTree.additionalDetails')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-5">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button onClick={handleSubmit} disabled={!formData.title.trim() || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium">
            {saving ? 'Adding...' : 'Add Event'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
