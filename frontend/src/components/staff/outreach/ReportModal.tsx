/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X } from 'lucide-react'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  reportStartDate: string
  setReportStartDate: (d: string) => void
  reportEndDate: string
  setReportEndDate: (d: string) => void
  isPending: boolean
  onGenerate: () => void
  onClose: () => void
}

export function ReportModal({ reportStartDate, setReportStartDate, reportEndDate, setReportEndDate, isPending, onGenerate, onClose }: Props) {
  return (
    <ModalBackdrop onClose={onClose} title="Regenerate Statistics">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Regenerate Statistics</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Start Date</label>
              <input
                type="date"
                value={reportStartDate}
                onChange={(e) => setReportStartDate(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">End Date</label>
              <input
                type="date"
                value={reportEndDate}
                onChange={(e) => setReportEndDate(e.target.value)}
                className="w-full px-3 py-2 bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
              Cancel
            </button>
            <button
              onClick={onGenerate}
              disabled={isPending}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg"
            >
              Generate
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
