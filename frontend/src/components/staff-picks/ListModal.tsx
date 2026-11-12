/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2, Save } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ListFormState {
  title: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

interface ListModalProps {
  isEditing: boolean;
  form: ListFormState;
  onFormChange: (form: ListFormState) => void;
  onSave: () => void;
  onClose: () => void;
  isSaving: boolean;
}

export function ListModal({ isEditing, form, onFormChange, onSave, onClose, isSaving }: ListModalProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Create New List">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {isEditing ? "Edit List" : "Create New List"}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Title <span className="text-status-danger-500">*</span>
            </label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => onFormChange({ ...form, title: e.target.value })}
              placeholder={t('placeholder.staffPicks.egSummerReadingPicks')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              placeholder={t('staffPicks.aBriefDescriptionOfThis')}
              rows={3}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          {isEditing && (
            <>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Display Order
                </label>
                <input
                  type="number"
                  value={form.display_order}
                  onChange={(e) => onFormChange({ ...form, display_order: parseInt(e.target.value) || 0 })}
                  min={0}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Lower numbers appear first. Set to 0 for featured.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="list-active"
                  checked={form.is_active}
                  onChange={(e) => onFormChange({ ...form, is_active: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                <label htmlFor="list-active" className="text-sm text-lsc-dark dark:text-lsc-cream">
                  Published (visible to patrons)
                </label>
              </div>
            </>
          )}
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={isSaving || !form.title.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Save className="w-4 h-4" />
            {isEditing ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
