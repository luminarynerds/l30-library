/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Cpu, Play, Tag, AlertTriangle, Plus, Zap } from "lucide-react"
import type { RFIDReader, RFIDSession } from "./types"
import type { TagReadResult, SecurityAlertResult } from "../../api/rfid-simulator-api"

interface OverviewTabProps {
  readers: RFIDReader[]
  sessions: RFIDSession[]
  scanResults: TagReadResult[]
  securityAlerts: SecurityAlertResult[]
  onCreateReader: () => void
  onGoToTags: () => void
  onGoToSecurity: () => void
}

export function OverviewTab({
  readers,
  sessions,
  scanResults,
  securityAlerts,
  onCreateReader,
  onGoToTags,
  onGoToSecurity,
}: OverviewTabProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-rose/10 rounded-lg"><Cpu className="w-5 h-5 text-lsc-rose" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{readers.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Readers</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-success-500/10 rounded-lg"><Play className="w-5 h-5 text-status-success-500" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{sessions.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Sessions</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-earth-500/10 rounded-lg"><Tag className="w-5 h-5 text-earth-600" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{scanResults.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Test Scans</p>
            </div>
          </div>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-danger-500/10 rounded-lg"><AlertTriangle className="w-5 h-5 text-status-danger-500" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{securityAlerts.length}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Test Alerts</p>
            </div>
          </div>
        </div>
      </div>

      <div>
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Quick Actions</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <button
            onClick={onCreateReader}
            className="flex items-center gap-3 p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 transition-colors"
          >
            <Plus className="w-5 h-5 text-lsc-rose" />
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">Create Test Reader</span>
          </button>
          <button
            onClick={onGoToTags}
            className="flex items-center gap-3 p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 transition-colors"
          >
            <Zap className="w-5 h-5 text-earth-600" />
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">Simulate Tag Scan</span>
          </button>
          <button
            onClick={onGoToSecurity}
            className="flex items-center gap-3 p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 transition-colors"
          >
            <AlertTriangle className="w-5 h-5 text-status-danger-500" />
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">Test Security Alert</span>
          </button>
        </div>
      </div>

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-status-warning-600 mt-0.5" />
          <div>
            <p className="font-semibold text-status-warning-800 dark:text-status-warning-300">Development/Testing Only</p>
            <p className="text-sm text-status-warning-700 dark:text-status-warning-400 mt-1">
              The RFID simulator is only available in development and testing environments. It allows you to test RFID workflows without physical hardware.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
