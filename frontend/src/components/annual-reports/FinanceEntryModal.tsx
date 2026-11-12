/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from '@/lib/sentry-lazy'
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import {
  AnnualReport,
  FinanceEntryPayload,
  enterAnnualReportFinance,
} from '@/api/annual-reports-api'
import { useAuth } from '@/contexts/AuthContext'

interface FinanceEntryModalProps {
  report: AnnualReport
  onClose: () => void
  onSaved: () => Promise<void>
}

type RevenueKey = 'local' | 'state' | 'federal' | 'other'
type ExpenditureKey = 'salaries' | 'benefits' | 'print' | 'electronic' | 'other'

const REVENUE_FIELDS: { key: RevenueKey; label: string }[] = [
  { key: 'local', label: 'Local' },
  { key: 'state', label: 'State' },
  { key: 'federal', label: 'Federal' },
  { key: 'other', label: 'Other' },
]

const EXPENDITURE_FIELDS: { key: ExpenditureKey; label: string }[] = [
  { key: 'salaries', label: 'Staff salaries' },
  { key: 'benefits', label: 'Staff benefits' },
  { key: 'print', label: 'Collection — print' },
  { key: 'electronic', label: 'Collection — electronic' },
  { key: 'other', label: 'Other operating' },
]

const EMPTY_REVENUE: Record<RevenueKey, string> = { local: '', state: '', federal: '', other: '' }
const EMPTY_EXPENDITURE: Record<ExpenditureKey, string> = {
  salaries: '',
  benefits: '',
  print: '',
  electronic: '',
  other: '',
}

const toNumber = (value: string): number => {
  const n = parseFloat(value)
  return Number.isFinite(n) && n > 0 ? n : 0
}

const sumValues = (values: string[]): number => values.reduce((acc, v) => acc + toNumber(v), 0)

const formatMoney = (n: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)

export default function FinanceEntryModal({
  report,
  onClose,
  onSaved,
}: FinanceEntryModalProps): React.ReactElement {
  const { token } = useAuth()
  const [isSaving, setIsSaving] = useState(false)
  const [revenue, setRevenue] = useState<Record<RevenueKey, string>>({ ...EMPTY_REVENUE })
  const [expenditure, setExpenditure] = useState<Record<ExpenditureKey, string>>({
    ...EMPTY_EXPENDITURE,
  })
  const [capitalOutlay, setCapitalOutlay] = useState('')
  const [capitalRevenue, setCapitalRevenue] = useState<Record<RevenueKey, string>>({
    ...EMPTY_REVENUE,
  })

  // Totals are derived from the line items so revenue/expenditure always reconcile
  // to their components — matching the server-side 422 reconciliation check.
  const revenueTotal = sumValues(Object.values(revenue))
  const expenditureTotal = sumValues(Object.values(expenditure))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) {
      toast.error('Authentication required')
      return
    }

    const payload: FinanceEntryPayload = {
      total_operating_revenue: revenueTotal,
      revenue: {
        local: toNumber(revenue.local),
        state: toNumber(revenue.state),
        federal: toNumber(revenue.federal),
        other: toNumber(revenue.other),
      },
      total_operating_expenditure: expenditureTotal,
      expenditure: {
        salaries: toNumber(expenditure.salaries),
        benefits: toNumber(expenditure.benefits),
        print: toNumber(expenditure.print),
        electronic: toNumber(expenditure.electronic),
        other: toNumber(expenditure.other),
      },
      capital_outlay: toNumber(capitalOutlay),
      capital_revenue: {
        local: toNumber(capitalRevenue.local),
        state: toNumber(capitalRevenue.state),
        federal: toNumber(capitalRevenue.federal),
        other: toNumber(capitalRevenue.other),
      },
    }

    setIsSaving(true)
    try {
      await enterAnnualReportFinance(token, report.id, payload)
      toast.success('Finance saved')
      await onSaved()
      onClose()
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error('Failed to save finance')
    } finally {
      setIsSaving(false)
    }
  }

  const inputClass =
    'w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light disabled:opacity-50 dark:bg-earth-800 dark:text-earth-50'

  const renderMoneyInput = (id: string, label: string, value: string, onChange: (v: string) => void) => (
    <div key={id}>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
      >
        {label}
      </label>
      <input
        id={id}
        type="number"
        min="0"
        step="0.01"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={isSaving}
        placeholder="0.00"
        className={inputClass}
      />
    </div>
  )

  return (
    <ModalBackdrop onClose={onClose} title="Enter Finance">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
            Enter Finance — FY{report.fiscal_year}
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Director-entered finance. Totals are computed from the line items.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Operating Revenue */}
          <fieldset>
            <legend className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream mb-3">
              Operating Revenue
            </legend>
            <div className="grid grid-cols-2 gap-3">
              {REVENUE_FIELDS.map((f) =>
                renderMoneyInput(`revenue-${f.key}`, f.label, revenue[f.key], (v) =>
                  setRevenue((prev) => ({ ...prev, [f.key]: v }))
                )
              )}
            </div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mt-3">
              Total operating revenue:{' '}
              <span data-testid="revenue-total">{formatMoney(revenueTotal)}</span>
            </p>
          </fieldset>

          {/* Operating Expenditure */}
          <fieldset>
            <legend className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream mb-3">
              Operating Expenditure
            </legend>
            <div className="grid grid-cols-2 gap-3">
              {EXPENDITURE_FIELDS.map((f) =>
                renderMoneyInput(`expenditure-${f.key}`, f.label, expenditure[f.key], (v) =>
                  setExpenditure((prev) => ({ ...prev, [f.key]: v }))
                )
              )}
            </div>
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mt-3">
              Total operating expenditure:{' '}
              <span data-testid="expenditure-total">{formatMoney(expenditureTotal)}</span>
            </p>
          </fieldset>

          {/* Capital */}
          <fieldset>
            <legend className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream mb-3">
              Capital
            </legend>
            <div className="grid grid-cols-2 gap-3">
              {renderMoneyInput('capital-outlay', 'Capital outlay', capitalOutlay, setCapitalOutlay)}
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3 mb-2">
              Capital revenue by source (optional)
            </p>
            <div className="grid grid-cols-2 gap-3">
              {REVENUE_FIELDS.map((f) =>
                renderMoneyInput(`capital-revenue-${f.key}`, f.label, capitalRevenue[f.key], (v) =>
                  setCapitalRevenue((prev) => ({ ...prev, [f.key]: v }))
                )
              )}
            </div>
          </fieldset>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {isSaving ? 'Saving...' : 'Save Finance'}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
