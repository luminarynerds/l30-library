/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { RefreshCw, Square, Play } from "lucide-react"
import type * as rfidSimulatorApi from "../../api/rfid-simulator-api"
import type { RFIDSession } from "./types"

interface AutoScanTabProps {
  sessions: RFIDSession[]
  selectedSession: number
  onSelectSession: (id: number) => void
  autoScanForm: { interval_ms: number; include_registered: boolean; include_unregistered: boolean }
  onSetAutoScanForm: (form: { interval_ms: number; include_registered: boolean; include_unregistered: boolean }) => void
  autoScanStatus: rfidSimulatorApi.AutoScanStatus | null
  onStartAutoScan: () => void
  onStopAutoScan: (sessionId: number) => void
  onStopAllAutoScans: () => void
  onLoadAutoScanStatus: () => void
}

export function AutoScanTab({
  sessions,
  selectedSession,
  onSelectSession,
  autoScanForm,
  onSetAutoScanForm,
  autoScanStatus,
  onStartAutoScan,
  onStopAutoScan,
  onStopAllAutoScans,
  onLoadAutoScanStatus,
}: AutoScanTabProps) {
  return (
    <div className="space-y-6">
      <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />Start Auto-Scan
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Session *</label>
            <select
              value={selectedSession}
              onChange={(e) => onSelectSession(parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            >
              <option value={0}>-- Select Session --</option>
              {sessions.map(s => (
                <option key={s.id} value={s.id}>Session #{s.id} - {s.session_type.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Interval (ms)</label>
            <input
              type="number"
              value={autoScanForm.interval_ms}
              onChange={(e) => onSetAutoScanForm({ ...autoScanForm, interval_ms: parseInt(e.target.value) || 1000 })}
              min={100}
              max={10000}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="flex items-center gap-4 md:col-span-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoScanForm.include_registered}
                onChange={(e) => onSetAutoScanForm({ ...autoScanForm, include_registered: e.target.checked })}
                className="w-4 h-4 rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Registered Tags</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoScanForm.include_unregistered}
                onChange={(e) => onSetAutoScanForm({ ...autoScanForm, include_unregistered: e.target.checked })}
                className="w-4 h-4 rounded border-lsc-border"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Unregistered Tags</span>
            </label>
          </div>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onStopAllAutoScans}
            className="px-4 py-2 bg-earth-200 hover:bg-earth-300 dark:bg-earth-700 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium flex items-center gap-2"
          >
            <Square className="w-4 h-4" />Stop All
          </button>
          <button
            onClick={onStartAutoScan}
            disabled={!selectedSession}
            className="px-6 py-2 bg-status-success-600 hover:bg-status-success-700 disabled:bg-earth-300 disabled:cursor-not-allowed text-white rounded-xl font-medium flex items-center gap-2"
          >
            <Play className="w-4 h-4" />Start Auto-Scan
          </button>
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Active Auto-Scans</h3>
          <button
            onClick={onLoadAutoScanStatus}
            className="text-sm text-lsc-rose hover:underline flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" />Refresh
          </button>
        </div>
        {autoScanStatus && autoScanStatus.active_sessions.length > 0 ? (
          <div className="space-y-2">
            {autoScanStatus.active_sessions.map((sessionId) => {
              const info = autoScanStatus.sessions[sessionId.toString()]
              return (
                <div key={sessionId} className="flex items-center justify-between p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-xl">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-5 h-5 text-status-success-600 motion-safe:animate-spin" />
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">Session #{sessionId}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {info?.interval_ms}ms interval • {info?.scans_performed || 0} scans
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => onStopAutoScan(sessionId)}
                    className="px-3 py-1 bg-status-danger-100 dark:bg-status-danger-900/30 hover:bg-status-danger-200 text-status-danger-700 dark:text-status-danger-300 rounded-full text-sm font-medium flex items-center gap-1"
                  >
                    <Square className="w-3 h-3" />Stop
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-center py-4 text-lsc-dark/70 dark:text-lsc-cream/70">No active auto-scans</p>
        )}
      </div>
    </div>
  )
}
