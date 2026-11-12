/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Save, Loader2 } from "lucide-react"
import { useTranslation } from "@/i18n"
import { TAG_COLORS } from "../../api/patron-segmentation-api"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface TagForm {
  id: number
  name: string
  color: string
  description: string
  is_active: boolean
}

interface Props {
  form: TagForm
  onChange: (form: TagForm) => void
  isEditing: boolean
  isSaving: boolean
  onSave: () => void
  onClose: () => void
}

export function TagModal({ form, onChange, isEditing, isSaving, onSave, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title={isEditing ? "Edit Tag" : "Create Tag"}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {isEditing ? "Edit Tag" : "Create Tag"}
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
              Name <span className="text-status-danger-500">*</span>
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => onChange({ ...form, name: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.egVipPatron')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Color
            </label>
            <div className="flex flex-wrap gap-2">
              {TAG_COLORS.map((color) => (
                <button
                  key={color.value}
                  onClick={() => onChange({ ...form, color: color.value })}
                  className={`w-8 h-8 rounded-full ${color.classes} ${
                    form.color === color.value ? "ring-2 ring-offset-2 ring-lsc-rose" : ""
                  }`}
                  title={color.label}
                />
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) => onChange({ ...form, description: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.optionalDescription')}
              rows={2}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          {isEditing && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="tag-active"
                checked={form.is_active}
                onChange={(e) => onChange({ ...form, is_active: e.target.checked })}
                className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
              />
              <label htmlFor="tag-active" className="text-sm text-lsc-dark dark:text-lsc-cream">
                Active
              </label>
            </div>
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
            disabled={isSaving || !form.name.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Save className="w-4 h-4" />
            {isEditing ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
