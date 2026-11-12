/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import RichTextEditor from "../RichTextEditor";
import { useTranslation } from '@/i18n';
import { Milestone, milestoneTypes } from "./strategic-types";
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  editingMilestone: Milestone;
  setEditingMilestone: (milestone: Milestone) => void;
  onSave: () => void;
  onClose: () => void;
}

export default function MilestoneModal({ editingMilestone, setEditingMilestone, onSave, onClose }: Props) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title={editingMilestone.id ? "Edit Milestone" : "Add Milestone"}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingMilestone.id ? "Edit Milestone" : "Add Milestone"}
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
              <input
                type="text"
                value={editingMilestone.title}
                onChange={(e) => setEditingMilestone({ ...editingMilestone, title: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.strategicAdmin.eg1000NewLibrary')}
              />
            </div>
            <div>
              <RichTextEditor
                label="Celebration Text"
                value={editingMilestone.celebration_text || ""}
                onChange={(value: string) => setEditingMilestone({ ...editingMilestone, celebration_text: value })}
                rows={3}
                placeholder={t('placeholder.strategicAdmin.publicCelebrationMessage')}
              />
            </div>
            <div>
              <RichTextEditor
                label="Impact Story"
                value={editingMilestone.impact_story || ""}
                onChange={(value: string) => setEditingMilestone({ ...editingMilestone, impact_story: value })}
                rows={4}
                placeholder={t('placeholder.strategicAdmin.communityImpactNarrative')}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Type</label>
                <select
                  value={editingMilestone.milestone_type}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, milestone_type: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  {milestoneTypes.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Achieved Date</label>
                <input
                  type="date"
                  value={editingMilestone.achieved_date?.split("T")[0] || ""}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, achieved_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Photo URL</label>
              <input
                type="text"
                value={editingMilestone.photo_url || ""}
                onChange={(e) => setEditingMilestone({ ...editingMilestone, photo_url: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.strategicAdmin.imagesmilestones')}
              />
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingMilestone.is_public}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, is_public: e.target.checked })}
                  className="w-4 h-4 rounded border-lsc-border"
                />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAdmin.showOnPublicPage2')}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingMilestone.is_featured}
                  onChange={(e) => setEditingMilestone({ ...editingMilestone, is_featured: e.target.checked })}
                  className="w-4 h-4 rounded border-lsc-border"
                />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAdmin.featuredHighlightOnHome')}</span>
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={!editingMilestone.title}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
            >
              Save Milestone
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
