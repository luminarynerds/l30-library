/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2, Save } from 'lucide-react';
import type { StaffPicksItem } from '../../api/domains/content/staff-picks-api';
import { useTranslation } from '@/i18n';
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface EditItemModalProps {
  item: StaffPicksItem;
  notes: string;
  onNotesChange: (notes: string) => void;
  onSave: () => void;
  onClose: () => void;
  isSaving: boolean;
}

export function EditItemModal({ item, notes, onNotesChange, onSave, onClose, isSaving }: EditItemModalProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={onClose} title="Edit Item Notes">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Edit Item Notes
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="bg-lsc-cream dark:bg-lsc-brown/30 p-3 rounded-lg">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
              {item.catalog_item.title}
            </p>
            {item.catalog_item.author && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                by {item.catalog_item.author}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Staff Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => onNotesChange(e.target.value)}
              placeholder={t('staffPicks.whyYouRecommendThisBook2')}
              rows={4}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
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
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
      </div>
    </ModalBackdrop>
  );
}
