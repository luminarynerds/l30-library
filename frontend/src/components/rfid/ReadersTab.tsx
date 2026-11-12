/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Wifi, WifiOff, Settings } from "lucide-react"
import * as rfidSimulatorApi from "../../api/rfid-simulator-api"
import { useTranslation } from "@/i18n"
import type { RFIDReader } from "./types"

interface ReadersTabProps {
  readers: RFIDReader[]
  statusForm: {
    reader_id: number
    status: rfidSimulatorApi.RFIDReaderStatus
    error_message: string
  }
  onSetStatusForm: (form: { reader_id: number; status: rfidSimulatorApi.RFIDReaderStatus; error_message: string }) => void
  onShowCreateReader: () => void
  onSimulateStatusChange: () => void
}

export function ReadersTab({
  readers,
  statusForm,
  onSetStatusForm,
  onShowCreateReader,
  onSimulateStatusChange,
}: ReadersTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Simulated Readers</h2>
        <button
          onClick={onShowCreateReader}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
        >
          <Plus className="w-4 h-4" />Create Reader
        </button>
      </div>

      {readers.length === 0 ? (
        <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">{t('rFIDSimulator.noReadersFoundCreateA')}</p>
      ) : (
        <div className="grid gap-4">
          {readers.map((reader) => (
            <div key={reader.id} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {reader.status === "online" ? <Wifi className="w-5 h-5 text-status-success-500" /> : <WifiOff className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />}
                  <div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{reader.name}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{reader.location || "No location set"}</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded ${rfidSimulatorApi.getStatusColorClass(reader.status as rfidSimulatorApi.RFIDReaderStatus)}`}>{reader.status}</span>
                      <span className="px-2 py-0.5 text-xs font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded">{rfidSimulatorApi.getReaderTypeLabel(reader.reader_type as rfidSimulatorApi.RFIDReaderType)}</span>
                    </div>
                  </div>
                </div>
                <p className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{reader.serial_number}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <Settings className="w-4 h-4" />Simulate Reader Status Change
        </h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Reader</label>
            <select
              value={statusForm.reader_id}
              onChange={(e) => onSetStatusForm({ ...statusForm, reader_id: parseInt(e.target.value) })}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>-- Select Reader --</option>
              {readers.map(r => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">New Status</label>
            <select
              value={statusForm.status}
              onChange={(e) => onSetStatusForm({ ...statusForm, status: e.target.value as rfidSimulatorApi.RFIDReaderStatus })}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              {rfidSimulatorApi.READER_STATUS_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Error Message (optional)</label>
            <input
              type="text"
              value={statusForm.error_message}
              onChange={(e) => onSetStatusForm({ ...statusForm, error_message: e.target.value })}
              placeholder={t('placeholder.rFIDSimulator.connectionTimeout')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onSimulateStatusChange}
            disabled={!statusForm.reader_id}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium"
          >
            Simulate Status Change
          </button>
        </div>
      </div>
    </div>
  )
}
