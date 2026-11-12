/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import RichTextEditor from "../RichTextEditor";
import { useTranslation } from '@/i18n';
import { Goal } from "./strategic-types";
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  editingGoal: Goal;
  setEditingGoal: (goal: Goal) => void;
  onSave: () => void;
  onClose: () => void;
}

export default function GoalModal({ editingGoal, setEditingGoal, onSave, onClose }: Props) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title={editingGoal.id ? "Edit Goal" : "Add Goal"}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingGoal.id ? "Edit Goal" : "Add Goal"}
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
              <input
                type="text"
                value={editingGoal.title}
                onChange={(e) => setEditingGoal({ ...editingGoal, title: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <RichTextEditor
                label="Description (Internal)"
                value={editingGoal.description || ""}
                onChange={(value: string) => setEditingGoal({ ...editingGoal, description: value })}
                rows={3}
                placeholder={t('strategicAdmin.detailedInternalDescriptionWithFormatting')}
              />
            </div>
            <div>
              <RichTextEditor
                label="Public Description"
                value={editingGoal.public_description || ""}
                onChange={(value: string) => setEditingGoal({ ...editingGoal, public_description: value })}
                rows={3}
                placeholder={t('strategicAdmin.simplifiedVersionForPublicDisplay')}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Category</label>
                <input
                  type="text"
                  value={editingGoal.category || ""}
                  onChange={(e) => setEditingGoal({ ...editingGoal, category: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('placeholder.strategicAdmin.communityTechnologyEtc')}
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Department</label>
                <input
                  type="text"
                  value={editingGoal.department || ""}
                  onChange={(e) => setEditingGoal({ ...editingGoal, department: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                  placeholder={t('strategicAdmin.youthServicesTechnicalEtc')}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Target Date</label>
                <input
                  type="date"
                  value={editingGoal.target_date?.split("T")[0] || ""}
                  onChange={(e) => setEditingGoal({ ...editingGoal, target_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Priority</label>
                <select
                  value={editingGoal.priority}
                  onChange={(e) => setEditingGoal({ ...editingGoal, priority: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value={1}>1 - Highest</option>
                  <option value={2}>2 - High</option>
                  <option value={3}>3 - Medium</option>
                  <option value={4}>4 - Low</option>
                  <option value={5}>5 - Lowest</option>
                </select>
              </div>
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingGoal.is_public}
                  onChange={(e) => setEditingGoal({ ...editingGoal, is_public: e.target.checked })}
                  className="w-4 h-4 rounded border-lsc-border"
                />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAdmin.showOnPublicPage')}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingGoal.staff_can_update}
                  onChange={(e) => setEditingGoal({ ...editingGoal, staff_can_update: e.target.checked })}
                  className="w-4 h-4 rounded border-lsc-border"
                />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('strategicAdmin.staffCanUpdateProgress')}</span>
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
              disabled={!editingGoal.title}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
            >
              Save Goal
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  );
}
