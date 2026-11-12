/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Check } from "lucide-react"
import * as rfidSimulatorApi from "../../api/rfid-simulator-api"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateReaderModalProps {
  form: {
    name: string
    reader_type: rfidSimulatorApi.RFIDReaderType
    location: string
  }
  onSetForm: (form: { name: string; reader_type: rfidSimulatorApi.RFIDReaderType; location: string }) => void
  onClose: () => void
  onSubmit: (e: React.FormEvent) => void
}

export function CreateReaderModal({ form, onSetForm, onClose, onSubmit }: CreateReaderModalProps) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Create Simulated Reader">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Create Simulated Reader</h2>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark rounded-xl" aria-label={t('rFIDSimulator.closeCreateReaderForm')}><X aria-hidden="true" className="w-5 h-5" /></button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => onSetForm({ ...form, name: e.target.value })}
              placeholder={t('placeholder.rFIDSimulator.testReader1')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reader Type</label>
            <select
              value={form.reader_type}
              onChange={(e) => onSetForm({ ...form, reader_type: e.target.value as rfidSimulatorApi.RFIDReaderType })}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              {rfidSimulatorApi.READER_TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location</label>
            <input
              type="text"
              value={form.location}
              onChange={(e) => onSetForm({ ...form, location: e.target.value })}
              placeholder={t('placeholder.rFIDSimulator.testLocation')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream rounded-xl font-medium">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2">
              <Check className="w-4 h-4" />Create Reader
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
