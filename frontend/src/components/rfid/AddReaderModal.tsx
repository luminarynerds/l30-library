/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Check } from "lucide-react"
import { useTranslation } from "@/i18n"
import { READER_TYPES, READER_TYPE_LABELS } from "./staff-rfid-data"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ReaderForm {
  name: string
  serial_number: string
  location: string
  reader_type: string
  protocol: string
  ip_address: string
  port: number
}

interface Props {
  form: ReaderForm
  onChange: (form: ReaderForm) => void
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
}

export function AddReaderModal({ form, onChange, onSubmit, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Register RFID Reader">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Register RFID Reader</h2>
          <button onClick={onClose} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 rounded-xl" aria-label={t('aria.staffRFID.closeReaderForm')}><X aria-hidden="true" className="w-5 h-5" /></button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="rfid-reader-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Name *</label>
            <input id="rfid-reader-name" type="text" value={form.name} onChange={(e) => onChange({ ...form, name: e.target.value })} placeholder={t('placeholder.staffRFID.mainDeskReader1')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required />
          </div>
          <div>
            <label htmlFor="rfid-reader-serial" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Serial Number *</label>
            <input id="rfid-reader-serial" type="text" value={form.serial_number} onChange={(e) => onChange({ ...form, serial_number: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono" required />
          </div>
          <div>
            <label htmlFor="rfid-reader-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location</label>
            <input id="rfid-reader-location" type="text" value={form.location} onChange={(e) => onChange({ ...form, location: e.target.value })} placeholder={t('placeholder.staffRFID.mainEntranceGate1')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="rfid-reader-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reader Type</label>
              <select id="rfid-reader-type" value={form.reader_type} onChange={(e) => onChange({ ...form, reader_type: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                {READER_TYPES.map(rt => <option key={rt} value={rt}>{READER_TYPE_LABELS[rt]}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="rfid-reader-protocol" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Protocol</label>
              <select id="rfid-reader-protocol" value={form.protocol} onChange={(e) => onChange({ ...form, protocol: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">
                <option value="sip2">SIP2</option>
                <option value="ncip">NCIP</option>
                <option value="rest_api">REST API</option>
                <option value="tcp_socket">TCP Socket</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="rfid-reader-ip-address" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">IP Address</label>
              <input id="rfid-reader-ip-address" type="text" value={form.ip_address} onChange={(e) => onChange({ ...form, ip_address: e.target.value })} placeholder={t('placeholder.staffRFID.1921681100')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono" />
            </div>
            <div>
              <label htmlFor="rfid-reader-port" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Port</label>
              <input id="rfid-reader-port" type="number" value={form.port || ""} onChange={(e) => onChange({ ...form, port: parseInt(e.target.value) || 0 })} placeholder={t('placeholder.staffRFID.6001')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button type="button" onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream rounded-xl font-medium">Cancel</button>
            <button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Check className="w-4 h-4" />Register</button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
