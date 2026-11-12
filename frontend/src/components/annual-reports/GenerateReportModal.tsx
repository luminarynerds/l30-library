/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import { X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface GenerateReportModalProps {
  onClose: () => void
  onGenerate: (fiscalYear: number, stateCode: string, libraryName: string) => Promise<void>
  isLoading: boolean
  states: Array<{ code: string; name: string }>
  fiscalYears: number[]
}

export default function GenerateReportModal({
  onClose,
  onGenerate,
  isLoading,
  states,
  fiscalYears,
}: GenerateReportModalProps): React.ReactElement {
  const { t } = useTranslation()
  const [fiscalYear, setFiscalYear] = useState<number>(fiscalYears[0] ?? new Date().getFullYear())
  const [stateCode, setStateCode] = useState<string>(states[0]?.code || '')
  const [libraryName, setLibraryName] = useState<string>('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!fiscalYear || !stateCode || !libraryName.trim()) {
      toast.error(t('components.annualReports.generateReport.pleaseFillInAllFields'))
      return
    }

    try {
      await onGenerate(fiscalYear, stateCode, libraryName)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="Generate Annual Report">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Generate Annual Report</h2>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-earth-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Fiscal Year */}
          <div>
            <label htmlFor="fiscalYear" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Fiscal Year *
            </label>
            <select
              id="fiscalYear"
              value={fiscalYear}
              onChange={(e) => setFiscalYear(parseInt(e.target.value))}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 dark:bg-earth-800 dark:text-earth-50"
            >
              {fiscalYears.map((year) => (
                <option key={year} value={year}>
                  FY{year}
                </option>
              ))}
            </select>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Standard fiscal year runs July - June
            </p>
          </div>

          {/* State Code */}
          <div>
            <label htmlFor="stateCode" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              State *
            </label>
            <select
              id="stateCode"
              value={stateCode}
              onChange={(e) => setStateCode(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 dark:bg-earth-800 dark:text-earth-50"
            >
              {states.map((state) => (
                <option key={state.code} value={state.code}>
                  {state.name}
                </option>
              ))}
            </select>
          </div>

          {/* Library Name */}
          <div>
            <label
              htmlFor="libraryName"
              className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2"
            >
              Library Name *
            </label>
            <input
              id="libraryName"
              type="text"
              value={libraryName}
              onChange={(e) => setLibraryName(e.target.value)}
              disabled={isLoading}
              placeholder={t('placeholder.annual-reports.enterLibraryName')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 dark:bg-earth-800 dark:text-earth-50"
            />
          </div>

          {/* Info Box */}
          <div className="bg-earth-50 dark:bg-earth-700/40 border border-lsc-border dark:border-earth-700 rounded p-3">
            <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
              <strong>Auto-populated fields:</strong> The system will automatically aggregate:
              circulation, patrons, collection, programs, finance, staff, facility, and technology
              data.
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {isLoading ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
