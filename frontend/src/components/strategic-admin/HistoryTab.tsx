/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Edit2, Trash2, Image, Save } from "lucide-react";
import { useTranslation } from '@/i18n';
import { TimelineEvent, Plan } from "./strategic-types";

interface Props {
  planForm: Plan;
  editingEvent: TimelineEvent | null;
  setEditingEvent: (event: TimelineEvent | null) => void;
  setEditingEventIndex: (index: number | null) => void;
  saving: boolean;
  onSave: () => void;
  onSaveEvent: () => void;
  onEditEvent: (index: number) => void;
  onDeleteEvent: (index: number) => void;
}

export default function HistoryTab({
  planForm,
  editingEvent,
  setEditingEvent,
  setEditingEventIndex,
  saving,
  onSave,
  onSaveEvent,
  onEditEvent,
  onDeleteEvent,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Library History Timeline</h2>
        <button
          onClick={() => { setEditingEvent({ year: new Date().getFullYear(), title: "", description: "", image_url: "" }); setEditingEventIndex(null); }}
          className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
        >
          <Plus className="h-4 w-4" /> Add Event
        </button>
      </div>

      {editingEvent && (
        <div className="p-4 bg-lsc-cream dark:bg-lsc-dark/20 border-b border-lsc-border dark:border-earth-700">
          <div className="grid md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Year</label>
              <input
                type="number"
                value={editingEvent.year}
                onChange={(e) => setEditingEvent({ ...editingEvent, year: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div className="md:col-span-3">
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title</label>
              <input
                type="text"
                value={editingEvent.title}
                onChange={(e) => setEditingEvent({ ...editingEvent, title: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.strategicAdmin.egLibraryFounded')}
              />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
              <textarea
                value={editingEvent.description || ""}
                onChange={(e) => setEditingEvent({ ...editingEvent, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Image URL</label>
              <input
                type="text"
                value={editingEvent.image_url || ""}
                onChange={(e) => setEditingEvent({ ...editingEvent, image_url: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.strategicAdmin.imageshistory')}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={onSaveEvent}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose"
            >
              Save Event
            </button>
            <button
              onClick={() => { setEditingEvent(null); setEditingEventIndex(null); }}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {planForm.history_timeline.length === 0 ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No timeline events yet. Add your library's history.
          </div>
        ) : (
          planForm.history_timeline.map((event, i) => (
            <div key={i} className="p-4 flex items-start gap-4">
              <div className="text-2xl font-bold text-lsc-rose w-16">{event.year}</div>
              <div className="flex-1">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{event.title}</h3>
                {event.description && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{event.description}</p>
                )}
                {event.image_url && (
                  <span className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1 flex items-center gap-1">
                    <Image className="h-3 w-3" /> {event.image_url}
                  </span>
                )}
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => onEditEvent(i)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                >
                  <Edit2 className="h-4 w-4" />
                </button>
                <button
                  onClick={() => onDeleteEvent(i)}
                  className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {planForm.history_timeline.length > 0 && (
        <div className="p-4 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onSave}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose"
          >
            <Save className="h-4 w-4" /> Save Timeline Changes
          </button>
        </div>
      )}
    </div>
  );
}
