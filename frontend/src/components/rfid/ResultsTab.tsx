/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Tag, Settings } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { TagReadResult, ReaderStatusResult, TestTag } from "../../api/rfid-simulator-api"

interface ResultsTabProps {
  scanResults: TagReadResult[]
  statusChanges: ReaderStatusResult[]
  createdTags: TestTag[]
  onClearScanResults: () => void
  onClearStatusChanges: () => void
  onClearCreatedTags: () => void
}

export function ResultsTab({
  scanResults,
  statusChanges,
  createdTags,
  onClearScanResults,
  onClearStatusChanges,
  onClearCreatedTags,
}: ResultsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Tag className="w-4 h-4" />Scan Results ({scanResults.length})
          </h3>
          <button onClick={onClearScanResults} className="text-sm text-status-danger-600 hover:underline">Clear</button>
        </div>
        {scanResults.length === 0 ? (
          <p className="text-center py-4 text-lsc-dark/70 dark:text-lsc-cream/70">{t('rFIDSimulator.noScanResultsYet')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Tag ID</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Item</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Signal</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {scanResults.slice(0, 25).map((result, idx) => (
                  <tr key={idx} className="hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/50">
                    <td className="px-3 py-2 font-mono text-xs text-lsc-dark dark:text-lsc-cream">{result.tag_id.substring(0, 12)}...</td>
                    <td className="px-3 py-2">
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream">{result.item_title || "Unregistered"}</p>
                      {result.item_barcode && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{result.item_barcode}</p>}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {result.is_registered ? (
                          <span className="px-1.5 py-0.5 text-xs bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded">Registered</span>
                        ) : (
                          <span className="px-1.5 py-0.5 text-xs bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded">Unknown</span>
                        )}
                        {result.is_misplaced && (
                          <span className="px-1.5 py-0.5 text-xs bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded">Misplaced</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{result.signal_strength} dBm</td>
                    <td className="px-3 py-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(result.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Settings className="w-4 h-4" />Status Changes ({statusChanges.length})
          </h3>
          <button onClick={onClearStatusChanges} className="text-sm text-status-danger-600 hover:underline">Clear</button>
        </div>
        {statusChanges.length === 0 ? (
          <p className="text-center py-4 text-lsc-dark/70 dark:text-lsc-cream/70">{t('rFIDSimulator.noStatusChangesYet')}</p>
        ) : (
          <div className="space-y-2">
            {statusChanges.slice(0, 10).map((change, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-lsc-brown/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Settings className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <div>
                    <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{change.name}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {change.previous_status} &rarr; {change.new_status}
                      {change.error_message && ` (${change.error_message})`}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(change.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {createdTags.length > 0 && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Tag className="w-4 h-4" />Created Test Tags ({createdTags.length})
            </h3>
            <button onClick={onClearCreatedTags} className="text-sm text-status-danger-600 hover:underline">Clear</button>
          </div>
          <div className="grid md:grid-cols-2 gap-2">
            {createdTags.slice(0, 20).map((tag, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                <span className="font-mono text-xs text-lsc-dark dark:text-lsc-cream">{tag.tag_id.substring(0, 16)}...</span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{tag.item_barcode}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
