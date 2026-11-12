/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Save, Loader2 } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { TerminalFormData } from "../types"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface TerminalModalProps {
  isEditing: boolean
  isSaving: boolean
  terminalForm: TerminalFormData
  setTerminalForm: (form: TerminalFormData) => void
  onSave: () => void
  onClose: () => void
}

export function TerminalModal({
  isEditing,
  isSaving,
  terminalForm,
  setTerminalForm,
  onSave,
  onClose,
}: TerminalModalProps) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-auto">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {isEditing ? "Edit Terminal" : "Create Terminal"}
          </h3>
          <button
            onClick={onClose}
            aria-label={t('aria.addRoleModal.closeModal')}
            className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="terminal-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Terminal ID <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="terminal-id"
                type="text"
                value={terminalForm.terminal_id}
                onChange={(e) => setTerminalForm({ ...terminalForm, terminal_id: e.target.value })}
                disabled={isEditing}
                placeholder={t('placeholder.staffSIP2.egSc001')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
              />
            </div>
            <div>
              <label htmlFor="terminal-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Name <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="terminal-name"
                type="text"
                value={terminalForm.name}
                onChange={(e) => setTerminalForm({ ...terminalForm, name: e.target.value })}
                placeholder={t('placeholder.staffSIP2.egMainEntranceCheckout')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label htmlFor="terminal-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <input
              id="terminal-description"
              type="text"
              value={terminalForm.description}
              onChange={(e) => setTerminalForm({ ...terminalForm, description: e.target.value })}
              placeholder={t('placeholder.staffPatronSegmentation.optionalDescription')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="terminal-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Location
              </label>
              <input
                id="terminal-location"
                type="text"
                value={terminalForm.location}
                onChange={(e) => setTerminalForm({ ...terminalForm, location: e.target.value })}
                placeholder={t('placeholder.staffSIP2.egFirstFloor')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <div>
              <label htmlFor="terminal-institution-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Institution ID
              </label>
              <input
                id="terminal-institution-id"
                type="text"
                value={terminalForm.institution_id}
                onChange={(e) => setTerminalForm({ ...terminalForm, institution_id: e.target.value })}
                placeholder={t('placeholder.cashDrawer.optional')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label htmlFor="terminal-password" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Password {!isEditing && "(for SIP2 authentication)"}
            </label>
            <input
              id="terminal-password"
              type="password"
              value={terminalForm.password}
              onChange={(e) => setTerminalForm({ ...terminalForm, password: e.target.value })}
              placeholder={isEditing ? "Leave blank to keep current" : "Set a password"}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">
              Permissions
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={terminalForm.allow_checkout}
                  onChange={(e) => setTerminalForm({ ...terminalForm, allow_checkout: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                Allow Checkout
              </label>
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={terminalForm.allow_checkin}
                  onChange={(e) => setTerminalForm({ ...terminalForm, allow_checkin: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                Allow Checkin
              </label>
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={terminalForm.allow_renewal}
                  onChange={(e) => setTerminalForm({ ...terminalForm, allow_renewal: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                Allow Renewal
              </label>
              <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={terminalForm.allow_patron_info}
                  onChange={(e) => setTerminalForm({ ...terminalForm, allow_patron_info: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
                />
                Allow Patron Info
              </label>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="terminal-active"
              checked={terminalForm.is_active}
              onChange={(e) => setTerminalForm({ ...terminalForm, is_active: e.target.checked })}
              className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
            />
            <label htmlFor="terminal-active" className="text-sm text-lsc-dark dark:text-lsc-cream">
              Terminal is active
            </label>
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
            disabled={isSaving || !terminalForm.terminal_id.trim() || !terminalForm.name.trim()}
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
