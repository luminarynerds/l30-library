/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Mail, Loader2 } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { GroupDetail } from "../../api/patron-segmentation-api"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface MessageForm {
  subject: string
  message: string
}

interface Props {
  selectedGroup: GroupDetail
  form: MessageForm
  onChange: (form: MessageForm) => void
  isSaving: boolean
  onSend: () => void
  onClose: () => void
}

export function MessageModal({ selectedGroup, form, onChange, isSaving, onSend, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title={`Send Message to ${selectedGroup.name}`}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Send Message to {selectedGroup.name}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            This message will be sent to {selectedGroup.member_count} members.
          </p>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Subject <span className="text-status-danger-500">*</span>
            </label>
            <input
              type="text"
              value={form.subject}
              onChange={(e) => onChange({ ...form, subject: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.messageSubject')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Message <span className="text-status-danger-500">*</span>
            </label>
            <textarea
              value={form.message}
              onChange={(e) => onChange({ ...form, message: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.yourMessage')}
              rows={5}
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
            onClick={onSend}
            disabled={isSaving || !form.subject.trim() || !form.message.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
            <Mail className="w-4 h-4" />
            Send
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
