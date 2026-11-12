/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, X, Save } from "lucide-react"
import { BookDropStatus, BOOK_DROP_STATUSES, BACKDATE_MODES, BackdateMode } from "@/api/book-drop-api"
import { BookDropFormState } from "../hooks/useBookDrops"
import { clean } from '@/lib/utils'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface BookDropDetailProps {
  form: BookDropFormState
  isEditing: boolean
  isSaving: boolean
  onFormChange: (form: BookDropFormState) => void
  onSave: () => void
  onCancel: () => void
}

export const BookDropDetail: React.FC<BookDropDetailProps> = ({
  form,
  isEditing,
  isSaving,
  onFormChange,
  onSave,
  onCancel,
}) => {
  return (
    <ModalBackdrop onClose={onCancel} labelledBy="book-drop-modal-title">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-auto">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 id="book-drop-modal-title" className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {isEditing ? "Edit Book Drop" : "New Book Drop"}
          </h3>
          <button
            onClick={onCancel}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="book-drop-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Name <span className="text-status-danger-600">*</span>
              </label>
              <input
                id="book-drop-name"
                type="text"
                value={form.name}
                onChange={(e) => onFormChange({ ...form, name: e.target.value })}
                placeholder={t('placeholder.bookDropDetail.egMainEntranceBook')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="book-drop-code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Code <span className="text-status-danger-600">*</span>
              </label>
              <input
                id="book-drop-code"
                type="text"
                value={form.code}
                onChange={(e) => onFormChange({ ...form, code: e.target.value.toUpperCase() })}
                placeholder={t('placeholder.bookDropDetail.egBdmain')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="book-drop-branch-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Branch Location <span className="text-status-danger-600">*</span>
              </label>
              <input
                id="book-drop-branch-location"
                type="text"
                value={form.branch_location}
                onChange={(e) => onFormChange({ ...form, branch_location: e.target.value })}
                placeholder={t('placeholder.bookDropDetail.egMainLibrary')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="book-drop-physical-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Physical Location
              </label>
              <input
                id="book-drop-physical-location"
                type="text"
                value={form.physical_location || ""}
                onChange={(e) => onFormChange({ ...form, physical_location: e.target.value })}
                placeholder={t('placeholder.bookDropDetail.egOutsideMainEntrance')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>

          <div>
            <label htmlFor="book-drop-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              id="book-drop-description"
              value={form.description || ""}
              onChange={(e) => onFormChange({ ...form, description: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.optionalDescription')}
              rows={2}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
            />
          </div>

          {isEditing && (
            <div>
              <label htmlFor="book-drop-status" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Status
              </label>
              <select
                id="book-drop-status"
                value={form.status || "active"}
                onChange={(e) => onFormChange({ ...form, status: e.target.value as BookDropStatus })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              >
                {BOOK_DROP_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Backdating Settings */}
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
              Backdating Configuration
            </h4>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="book-drop-backdate-mode" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Backdate Mode
                </label>
                <select
                  id="book-drop-backdate-mode"
                  value={form.backdate_mode}
                  onChange={(e) => onFormChange({ ...form, backdate_mode: e.target.value as BackdateMode })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                >
                  {BACKDATE_MODES.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              {form.backdate_mode === "fixed_time" && (
                <div>
                  <label htmlFor="book-drop-fixed-time" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Fixed Time
                  </label>
                  <input
                    id="book-drop-fixed-time"
                    type="time"
                    value={form.backdate_fixed_time || ""}
                    onChange={(e) => onFormChange({ ...form, backdate_fixed_time: e.target.value })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              )}

              {form.backdate_mode === "hours_back" && (
                <div>
                  <label htmlFor="book-drop-hours-back" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Hours Back
                  </label>
                  <input
                    id="book-drop-hours-back"
                    type="number"
                    min="1"
                    max="72"
                    value={form.backdate_hours || ""}
                    onChange={(e) => onFormChange(clean({ ...form, backdate_hours: parseInt(e.target.value) || undefined }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              )}

              {form.backdate_mode === "days_back" && (
                <div>
                  <label htmlFor="book-drop-days-back" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Days Back
                  </label>
                  <input
                    id="book-drop-days-back"
                    type="number"
                    min="1"
                    max="7"
                    value={form.backdate_days || ""}
                    onChange={(e) => onFormChange(clean({ ...form, backdate_days: parseInt(e.target.value) || undefined }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              )}
            </div>

            <div className="mt-3 flex items-center gap-2">
              <input
                type="checkbox"
                id="exempt-fines"
                checked={form.exempt_overnight_fines}
                onChange={(e) => onFormChange({ ...form, exempt_overnight_fines: e.target.checked })}
                className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
              />
              <label htmlFor="exempt-fines" className="text-sm text-lsc-dark dark:text-lsc-cream">
                Exempt overnight fines for items returned to this book drop
              </label>
            </div>
          </div>

          {/* Processing Hours */}
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
              Processing Hours (Optional)
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="book-drop-start-time" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Start Time
                </label>
                <input
                  id="book-drop-start-time"
                  type="time"
                  value={form.processing_start_time || ""}
                  onChange={(e) => onFormChange({ ...form, processing_start_time: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div>
                <label htmlFor="book-drop-end-time" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  End Time
                </label>
                <input
                  id="book-drop-end-time"
                  type="time"
                  value={form.processing_end_time || ""}
                  onChange={(e) => onFormChange({ ...form, processing_end_time: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={isSaving || !form.name.trim() || !form.code.trim() || !form.branch_location.trim()}
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
