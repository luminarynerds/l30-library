/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { AlertCircle, CheckCircle, HelpCircle, Loader2, Phone } from 'lucide-react'
import { checkEligibility, type EligibilityResult } from '@/api/legal-api'
import { getCurrentLocale, useTranslation } from '@/i18n'

export default function EligibilityChecker(): React.ReactElement {
  const { t } = useTranslation()
  const [householdSize, setHouseholdSize] = useState<number>(1)
  const [income, setIncome] = useState<string>('')

  const mutation = useMutation({
    mutationFn: () =>
      checkEligibility({
        household_size: householdSize,
        income: parseInt(income.replace(/[^\d]/g, ''), 10) || 0,
      }),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const parsed = parseInt(income.replace(/[^\d]/g, ''), 10)
    if (!parsed || parsed < 0) return
    mutation.mutate()
  }

  const formatDollars = (val: string): string => {
    const num = parseInt(val.replace(/[^\d]/g, ''), 10)
    if (isNaN(num)) return ''
    return num.toLocaleString(getCurrentLocale())
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
          {t('components.legal.eligibilityChecker.checkIfYouMayQualify', 'Check if you may qualify for free legal help')}
        </h3>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 mb-4">
        <label className="flex-1">
          <span className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('components.legal.eligibilityChecker.householdSize', 'Household size')}</span>
          <select
            value={householdSize}
            onChange={(e) => setHouseholdSize(Number(e.target.value))}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50"
          >
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <option key={n} value={n}>{n === 8 ? '8+' : n}</option>
            ))}
          </select>
        </label>

        <label className="flex-1">
          <span className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">{t('components.legal.eligibilityChecker.annualHouseholdIncome', 'Annual household income')}</span>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/50 dark:text-lsc-cream/50">$</span>
            <input
              type="text"
              inputMode="numeric"
              value={income}
              onChange={(e) => setIncome(formatDollars(e.target.value))}
              placeholder="35,000"
              className="w-full pl-7 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500"
            />
          </div>
        </label>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={!income || mutation.isPending}
            className="px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              t('components.legal.eligibilityChecker.checkEligibility', 'Check eligibility')
            )}
          </button>
        </div>
      </form>

      {mutation.data && (
        <div className="space-y-3 mb-4">
          {mutation.data.results.map((r: EligibilityResult) => (
            <div
              key={r.provider_id}
              className={`flex items-start gap-3 p-3 rounded-xl border ${
                r.status === 'likely_eligible'
                  ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800'
                  : r.status === 'may_be_eligible'
                    ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800'
                    : 'bg-earth-50 dark:bg-earth-900/20 border-earth-200 dark:border-earth-700'
              }`}
            >
              {r.status === 'likely_eligible' ? (
                <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
              ) : r.status === 'may_be_eligible' ? (
                <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-earth-600 dark:text-earth-500 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p className="font-medium text-sm text-lsc-dark dark:text-earth-50">{r.provider_name}</p>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {r.status === 'likely_eligible' && t('components.legal.eligibilityChecker.youLikelyQualifyBased', 'You likely qualify based on income guidelines.')}
                  {r.status === 'may_be_eligible' && t('components.legal.eligibilityChecker.youReCloseTo', "You're close to the limit -- call to confirm.")}
                  {r.status === 'over_limit' && t('components.legal.eligibilityChecker.youMayNotQualify', 'You may not qualify based on income, but call anyway -- exceptions exist.')}
                </p>
                {r.phone && (
                  <a
                    href={`tel:${r.phone.replace(/[^\d+]/g, '')}`}
                    className="inline-flex items-center gap-1 text-xs text-lsc-rose dark:text-lsc-rose-light mt-1 hover:underline"
                  >
                    <Phone aria-hidden="true" className="w-3 h-3" />
                    {r.phone}
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
        {t(
          'components.legal.eligibilityChecker.thisIsAnEstimate',
          'This is an estimate based on federal poverty guidelines. Each provider makes their own eligibility determination. Call to confirm.',
        )}
      </p>
    </div>
  )
}
