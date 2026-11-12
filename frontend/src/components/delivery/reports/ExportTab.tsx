/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Download } from "lucide-react"
import { useTranslation } from "@/i18n"

interface Props {
  exportType: 'deliveries' | 'patrons' | 'volunteers' | 'hours' | 'feedback'
  setExportType: (v: 'deliveries' | 'patrons' | 'volunteers' | 'hours' | 'feedback') => void
  exportFormat: 'csv' | 'json' | 'xlsx'
  setExportFormat: (v: 'csv' | 'json' | 'xlsx') => void
  exportStart: string
  setExportStart: (v: string) => void
  exportEnd: string
  setExportEnd: (v: string) => void
  onExport: () => void
  isPending: boolean
}

export function ExportTab({
  exportType,
  setExportType,
  exportFormat,
  setExportFormat,
  exportStart,
  setExportStart,
  exportEnd,
  setExportEnd,
  onExport,
  isPending,
}: Props) {
  const { t } = useTranslation()
  void t

  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Export Report Data</h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          Download home delivery service data in your preferred format for external analysis or record-keeping.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Report Type</label>
            <select
              value={exportType}
              onChange={(e) => setExportType(e.target.value as typeof exportType)}
              className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <option value="deliveries">Deliveries</option>
              <option value="patrons">Patron Records</option>
              <option value="volunteers">Volunteer Data</option>
              <option value="hours">Volunteer Hours</option>
              <option value="feedback">Patron Feedback</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Format</label>
            <div className="flex gap-3">
              {(['csv', 'xlsx', 'json'] as const).map((fmt) => (
                <label key={fmt} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    value={fmt}
                    checked={exportFormat === fmt}
                    onChange={() => setExportFormat(fmt)}
                    className="text-lsc-rose"
                  />
                  <span className="text-sm text-lsc-dark dark:text-lsc-cream uppercase">{fmt}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Start Date (optional)</label>
              <input
                type="date"
                value={exportStart}
                onChange={(e) => setExportStart(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">End Date (optional)</label>
              <input
                type="date"
                value={exportEnd}
                onChange={(e) => setExportEnd(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
          </div>

          <div className="p-3 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-earth-800 dark:text-lsc-rose-light">
            <strong>Privacy Note:</strong> Exported data contains personally identifiable information. Handle securely and in accordance with library privacy policies.
          </div>

          <button
            onClick={onExport}
            disabled={isPending}
            className="flex items-center gap-2 px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium"
          >
            {isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Download className="w-4 h-4" />}
            Export {exportType.charAt(0).toUpperCase() + exportType.slice(1)} as {exportFormat.toUpperCase()}
          </button>
        </div>
      </div>
    </div>
  )
}
