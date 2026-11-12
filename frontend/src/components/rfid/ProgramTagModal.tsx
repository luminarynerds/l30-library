/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Tag } from "lucide-react"
import { ModalBackdrop } from "@/components/ui/ModalBackdrop"
import { useTranslation } from "@/i18n"
import type { StaffRFIDReader } from "./staff-rfid-types"

interface ProgramForm {
  item_barcode: string
  reader_id: number
}

interface Props {
  form: ProgramForm
  onChange: (form: ProgramForm) => void
  readers: StaffRFIDReader[]
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
}

export function ProgramTagModal({ form, onChange, readers, onSubmit, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Program RFID Tag">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Program RFID Tag</h2>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 rounded-xl" aria-label={t('staffRFID.closeProgramTagForm')}><X aria-hidden="true" className="w-5 h-5" /></button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Item Barcode *</label>
            <input type="text" value={form.item_barcode} onChange={(e) => onChange({ ...form, item_barcode: e.target.value })} placeholder={t('staffRFID.scanOrEnterItemBarcode')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Programming Reader *</label>
            <select value={form.reader_id} onChange={(e) => onChange({ ...form, reader_id: parseInt(e.target.value) })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required>
              <option value={0}>-- Select Reader --</option>
              {readers.filter(r => r.status === "online").map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffRFID.placeABlankRfidTag')}</p>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream rounded-xl font-medium">Cancel</button>
            <button type="submit" disabled={!form.item_barcode || !form.reader_id} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 text-white rounded-xl font-medium flex items-center gap-2"><Tag className="w-4 h-4" />Program Tag</button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
