/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, Wifi, WifiOff } from "lucide-react"
import type { StaffRFIDReader } from "./staff-rfid-types"
import { STATUS_COLORS, READER_TYPE_LABELS } from "./staff-rfid-data"

interface Props {
  readers: StaffRFIDReader[]
  onAddReader: () => void
}

export function StaffReadersTab({ readers, onAddReader }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">RFID Readers</h2>
        <button onClick={onAddReader} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium">
          <Plus className="w-4 h-4" />Add Reader
        </button>
      </div>

      {readers.length === 0 ? (
        <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No readers registered</p>
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
                      <span className={"px-2 py-0.5 text-xs font-medium rounded " + (STATUS_COLORS[reader.status] || "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70")}>{reader.status}</span>
                      <span className="px-2 py-0.5 text-xs font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded">{READER_TYPE_LABELS[reader.reader_type] || reader.reader_type}</span>
                      <span className="px-2 py-0.5 text-xs font-medium bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded">{reader.protocol.toUpperCase()}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <p className="font-mono">{reader.ip_address}:{reader.port}</p>
                  <p className="text-xs">SN: {reader.serial_number}</p>
                  {reader.last_heartbeat && <p className="text-xs">Last seen: {new Date(reader.last_heartbeat).toLocaleTimeString()}</p>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
