/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, X, Play } from "lucide-react"
import { BookDrop } from "@/api/book-drop-api"
import { SessionFormState } from "../hooks/useBookDropProcessing"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface SessionModalProps {
  form: SessionFormState
  isSaving: boolean
  bookDrops: BookDrop[]
  onFormChange: (form: SessionFormState) => void
  onSubmit: () => void
  onCancel: () => void
}

export const SessionModal: React.FC<SessionModalProps> = ({
  form,
  isSaving,
  bookDrops,
  onFormChange,
  onSubmit,
  onCancel,
}) => {
  const { t } = useTranslation()
  return (
    <ModalBackdrop onClose={onCancel} title="Start Check-in Session">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Start Check-in Session
          </h3>
          <button
            onClick={onCancel}
            aria-label={t('common.close')}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label htmlFor="session-branch-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Branch Location <span className="text-status-danger-600">*</span>
            </label>
            <input
              id="session-branch-location"
              type="text"
              required
              aria-required="true"
              value={form.branch_location}
              onChange={(e) => onFormChange({ ...form, branch_location: e.target.value })}
              placeholder={t('placeholder.bookDropDetail.egMainLibrary')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          <div>
            <label htmlFor="session-book-drop" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Book Drop (Optional)
            </label>
            <select
              id="session-book-drop"
              value={form.book_drop_id || ""}
              onChange={(e) => onFormChange({ ...form, book_drop_id: e.target.value ? parseInt(e.target.value) : undefined })}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">{t('session.noBookDropManualCheck')}</option>
              {bookDrops.filter((d) => d.status === "active").map((drop) => (
                <option key={drop.id} value={drop.id}>
                  {drop.name} ({drop.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="session-workstation-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Workstation ID (Optional)
            </label>
            <input
              id="session-workstation-id"
              type="text"
              value={form.workstation_id}
              onChange={(e) => onFormChange({ ...form, workstation_id: e.target.value })}
              placeholder={t('placeholder.sessionModal.egCirc01')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          {!form.book_drop_id && (
            <div>
              <label htmlFor="session-backdate-to" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Manual Backdate To (Optional)
              </label>
              <input
                id="session-backdate-to"
                type="datetime-local"
                value={form.backdate_to}
                onChange={(e) => onFormChange({ ...form, backdate_to: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          )}
        </div>
        <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={isSaving || !form.branch_location.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Play className="w-4 h-4" />
            Start Session
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
