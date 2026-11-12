/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Calculator,
  Clock,
  Shield,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  ChevronRight,
  Calendar,
  Info,
  Scale,
  FileText,
} from 'lucide-react'
import {
  calculateDeadline,
  checkFeeWaiverEligibility,
  checkExpungementEligibility,
  getDeadlineRules,
  type DeadlineCalculationResponse,
  type FeeWaiverEligibilityResponse,
  type ExpungementEligibilityResponse,
} from '@/api/legal-api'
import toast from 'react-hot-toast'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { clean } from '@/lib/utils'
import { parseDate } from '@/utils/format-utils'
import PageContainer from '@/components/layout/PageContainer'

type CalcTab = 'deadline' | 'fee-waiver' | 'expungement'

const TABS: { id: CalcTab; labelKey: string; label: string; icon: React.ReactNode; descriptionKey: string; description: string }[] = [
  {
    id: 'deadline',
    labelKey: 'legalCalculators.deadlineCalculatorLabel',
    label: 'Deadline Calculator',
    icon: <Clock className="w-5 h-5" />,
    descriptionKey: 'legalCalculators.calculateLegalDeadlinesAccountingFor',
    description: 'Calculate legal deadlines accounting for court holidays and business days',
  },
  {
    id: 'fee-waiver',
    labelKey: 'legalCalculators.feeWaiverEligibilityLabel',
    label: 'Fee Waiver Eligibility',
    icon: <Shield className="w-5 h-5" />,
    descriptionKey: 'legalCalculators.checkIfYouMayQualify',
    description: 'Check if you may qualify to have court filing fees waived',
  },
  {
    id: 'expungement',
    labelKey: 'legalCalculators.expungementEligibilityLabel',
    label: 'Expungement Eligibility',
    icon: <CheckCircle className="w-5 h-5" />,
    descriptionKey: 'legalCalculators.checkBasicEligibilityToHave',
    description: 'Check basic eligibility to have a criminal record expunged',
  },
]

// ==================== Deadline Calculator ====================

function DeadlineCalculator() {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    rule_id: '',
    rule_slug: '',
    start_date: new Date().toISOString().split('T')[0] ?? '',
    reminder_email: '',
    enable_reminders: false,
    user_notes: '',
  })
  const [result, setResult] = useState<DeadlineCalculationResponse | null>(null)

  const { data: rules, isLoading: rulesLoading } = useQuery({
    queryKey: ['deadline-rules'],
    queryFn: () => getDeadlineRules(),
  })

  const calcMutation = useMutation({
    mutationFn: () => calculateDeadline({
      rule_id: form.rule_id ? Number(form.rule_id) : null,
      rule_slug: form.rule_slug || null,
      start_date: form.start_date,
      reminder_email: form.enable_reminders && form.reminder_email ? form.reminder_email : null,
      enable_reminders: form.enable_reminders,
      user_notes: form.user_notes || null,
    }),
    onSuccess: (data) => {
      setResult(data)
    },
    onError: () => toast.error(t('legalCalculators.failedToCalculateDeadlinePlease')),
  })

  const formatDate = (dateStr: string) => {
    return parseDate(dateStr)?.toLocaleDateString(getCurrentLocale(), {
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
    }) ?? '-'
  }

  const getDaysClass = (days: number) => {
    if (days < 0) return 'text-status-danger-600 dark:text-status-danger-400'
    if (days <= 7) return 'text-status-warning-600 dark:text-status-warning-400'
    return 'text-status-success-600 dark:text-status-success-400'
  }

  return (
    <div className="space-y-6">
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-earth-800 dark:text-lsc-rose-light/80 text-sm">{t('legalCalculators.howThisWorks', 'How this works')}</p>
            <p className="text-sm text-lsc-rose dark:text-lsc-rose-light mt-1">
              {t('legalCalculators.selectADeadlineRuleAnd', 'Select a deadline rule and enter your start date (e.g., the date you were served, the incident date, or the date of a court order). The calculator accounts for weekends, court holidays, and jurisdiction-specific rules.')}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-5">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.selectDeadlineRule', 'Select Deadline Rule')} *
          </label>
          {rulesLoading ? (
            <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              {t('legalCalculators.loadingRules', 'Loading rules...')}
            </div>
          ) : (
            <select
              value={form.rule_id}
              onChange={e => setForm(f => ({ ...f, rule_id: e.target.value, rule_slug: '' }))}
              className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
            >
              <option value="">{t('legalCalculators.selectADeadlineType')}</option>
              {rules?.map(rule => (
                <option key={rule.id} value={rule.id}>
                  {rule.name} ({rule.days} {rule.use_business_days ? t('legalCalculators.business', 'business') : t('legalCalculators.calendar', 'calendar')} {t('legalCalculators.days', 'days')})
                  {rule.jurisdiction ? ` — ${rule.jurisdiction}` : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Show selected rule details */}
        {form.rule_id && rules && (
          (() => {
            const selectedRule = rules.find(r => r.id === Number(form.rule_id))
            if (!selectedRule) return null
            return (
              <div className="bg-lsc-cream dark:bg-earth-900/50 rounded-xl p-4 text-sm">
                <p className="font-medium text-lsc-dark dark:text-earth-50 mb-2">{selectedRule.name}</p>
                {selectedRule.description && <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">{selectedRule.description}</p>}
                <div className="grid grid-cols-2 gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span>{t('legalCalculators.daysX', { days: selectedRule.days })}</span>
                  <span>{t('legalCalculators.typeX', { type: selectedRule.use_business_days ? t('legalCalculators.businessDays', 'Business days') : t('legalCalculators.calendarDays', 'Calendar days') })}</span>
                  {selectedRule.exclude_holidays && <span>{t('legalCalculators.excludesHolidays', 'Excludes holidays')}</span>}
                  {selectedRule.legal_citation && <span>{t('legalCalculators.citeX', { citation: selectedRule.legal_citation })}</span>}
                </div>
              </div>
            )
          })()
        )}

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.startDate', 'Start Date')} *
          </label>
          <input
            type="date"
            value={form.start_date}
            onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.notesOptional', 'Notes (optional)')}
          </label>
          <input
            type="text"
            value={form.user_notes}
            onChange={e => setForm(f => ({ ...f, user_notes: e.target.value }))}
            placeholder={t('placeholder.legalCalculators.egServedOnJan')}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          />
        </div>

        <div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.enable_reminders}
              onChange={e => setForm(f => ({ ...f, enable_reminders: e.target.checked }))}
              className="w-4 h-4 accent-lsc-rose"
            />
            <span className="text-sm text-lsc-dark dark:text-earth-50">{t('legalCalculators.emailMeRemindersBeforeThe')}</span>
          </label>
        </div>

        {form.enable_reminders && (
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('legalCalculators.emailAddress', 'Email Address')}
            </label>
            <input
              type="email"
              value={form.reminder_email}
              onChange={e => setForm(f => ({ ...f, reminder_email: e.target.value }))}
              placeholder={t('placeholder.betaFeedback.youremailcom')}
              className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
            />
          </div>
        )}

        <button
          onClick={() => calcMutation.mutate()}
          disabled={!form.rule_id || !form.start_date || calcMutation.isPending}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium disabled:opacity-50"
        >
          {calcMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Calculator className="w-4 h-4" />
          )}
          {calcMutation.isPending ? t('legalCalculators.calculating', 'Calculating...') : t('legalCalculators.calculateDeadline', 'Calculate Deadline')}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50 mb-5">{t('legalCalculators.yourDeadline', 'Your Deadline')}</h3>

          <div className="grid sm:grid-cols-3 gap-4 mb-6">
            <div className="bg-lsc-cream dark:bg-earth-900/50 rounded-xl p-4 text-center">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('legalCalculators.startDate', 'Start Date')}</p>
              <p className="font-semibold text-lsc-dark dark:text-earth-50">{formatDate(result.start_date)}</p>
            </div>
            <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl p-4 text-center">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('legalCalculators.deadline', 'Deadline')}</p>
              <p className="font-semibold text-lsc-dark dark:text-earth-50">{formatDate(result.deadline_date)}</p>
            </div>
            <div className={`rounded-xl p-4 text-center ${result.days_until_deadline < 0 ? 'bg-status-danger-50 dark:bg-status-danger-900/20' : result.days_until_deadline <= 7 ? 'bg-status-warning-50 dark:bg-status-warning-900/20' : 'bg-status-success-50 dark:bg-status-success-900/20'}`}>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('legalCalculators.daysUntilDeadline', 'Days Until Deadline')}</p>
              <p className={`text-2xl font-bold ${getDaysClass(result.days_until_deadline)}`}>
                {result.days_until_deadline < 0 ? t('legalCalculators.passed', 'PASSED') : result.days_until_deadline}
              </p>
              {result.days_until_deadline >= 0 && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('legalCalculators.daysRemaining', 'days remaining')}</p>}
            </div>
          </div>

          {result.days_until_deadline < 0 && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0" />
                <p className="text-sm text-status-danger-700 dark:text-status-danger-300">
                  {t('legalCalculators.thisDeadlineHasPassed', 'This deadline has passed. You may need to file a motion explaining the delay or seek emergency legal assistance. Contact a legal aid provider immediately.')}
                </p>
              </div>
            </div>
          )}

          {result.warning_dates && result.warning_dates.length > 0 && (
            <div>
              <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('legalCalculators.reminderDates', 'Reminder Dates')}</p>
              <div className="space-y-2">
                {result.warning_dates.map(date => (
                  <div key={date} className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Calendar className="w-4 h-4 text-status-warning-500" />
                    {formatDate(date)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.user_notes && (
            <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('legalCalculators.notesX', { notes: result.user_notes })}</p>
            </div>
          )}
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
        <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
          <strong>{t('legalCalculators.important', 'Important:')}</strong> {t('legalCalculators.thisCalculatorProvidesAnEstimate', 'This calculator provides an estimate only. Court dates can be affected by local rules, emergency orders, and other factors. Always confirm deadlines with the court clerk or a licensed attorney.')}
        </p>
      </div>
    </div>
  )
}

// ==================== Fee Waiver Eligibility ====================

function FeeWaiverCalculator() {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    jurisdiction: '',
    household_size: 1,
    annual_income: 0,
    receives_public_benefits: [] as string[],
  })
  const [result, setResult] = useState<FeeWaiverEligibilityResponse | null>(null)

  const benefitOptions = [
    { value: 'medi-cal', label: t('legalCalculators.mediCalMedicaid', 'Medi-Cal / Medicaid') },
    { value: 'calworks', label: t('legalCalculators.calworksTanf', 'CalWORKs / TANF') },
    { value: 'ssi', label: t('legalCalculators.ssiSsdi', 'SSI / SSDI') },
    { value: 'snap', label: t('legalCalculators.snapFoodStamps', 'SNAP / Food Stamps') },
    { value: 'county_relief', label: t('legalCalculators.countyRelief', 'County Relief') },
    { value: 'general_assistance', label: t('legalCalculators.generalAssistance', 'General Assistance') },
  ]

  const checkMutation = useMutation({
    mutationFn: () => checkFeeWaiverEligibility({
      jurisdiction: form.jurisdiction,
      household_size: form.household_size,
      annual_income: form.annual_income,
      receives_public_benefits: form.receives_public_benefits,
    }),
    onSuccess: (data) => setResult(data),
    onError: () => toast.error(t('legalCalculators.failedToCheckEligibilityPlease')),
  })

  const toggleBenefit = (value: string) => {
    setForm(f => ({
      ...f,
      receives_public_benefits: f.receives_public_benefits.includes(value)
        ? f.receives_public_benefits.filter(b => b !== value)
        : [...f.receives_public_benefits, value],
    }))
  }

  return (
    <div className="space-y-6">
      <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-status-success-800 dark:text-status-success-200 text-sm">{t('legalCalculators.aboutFeeWaivers', 'About Fee Waivers')}</p>
            <p className="text-sm text-status-success-700 dark:text-status-success-300 mt-1">
              {t('legalCalculators.ifYouCannotAfford', 'If you cannot afford court filing fees, you may qualify for a fee waiver (also called a "fee waiver" or "IFP — In Forma Pauperis"). This tool provides a preliminary estimate — the court makes the final determination.')}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-5">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.jurisdictionState', 'Jurisdiction / State')} *
          </label>
          <input
            type="text"
            value={form.jurisdiction}
            onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
            placeholder={t('placeholder.legalCalculators.egCaliforniaSanFrancisco')}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('legalCalculators.householdSize', 'Household Size')} *
            </label>
            <input
              type="number"
              value={form.household_size}
              onChange={e => setForm(f => ({ ...f, household_size: Number(e.target.value) }))}
              min={1}
              max={20}
              className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('legalCalculators.includeYourselfAndDependents')}</p>
          </div>
          <div>
            <label htmlFor="fee-waiver-income" className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('legalCalculators.annualHouseholdIncome', 'Annual Household Income')} *
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70">$</span>
              <input
                id="fee-waiver-income"
                type="number"
                value={form.annual_income}
                onChange={e => setForm(f => ({ ...f, annual_income: Number(e.target.value) }))}
                min={0}
                className="w-full pl-7 pr-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
              />
            </div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('legalCalculators.grossIncomeBeforeTaxes')}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">
            {t('legalCalculators.doYouReceiveAnyOf', 'Do you receive any of these public benefits?')}
          </label>
          <div className="grid sm:grid-cols-2 gap-2">
            {benefitOptions.map(option => (
              <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.receives_public_benefits.includes(option.value)}
                  onChange={() => toggleBenefit(option.value)}
                  className="w-4 h-4 accent-lsc-rose"
                />
                <span className="text-sm text-lsc-dark dark:text-earth-50">{option.label}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={() => checkMutation.mutate()}
          disabled={!form.jurisdiction || checkMutation.isPending}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium disabled:opacity-50"
        >
          {checkMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Shield className="w-4 h-4" />
          )}
          {checkMutation.isPending ? t('legalCalculators.checking', 'Checking...') : t('legalCalculators.checkEligibility', 'Check Eligibility')}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-5">
            {result.is_eligible ? (
              <CheckCircle className="w-7 h-7 text-status-success-600 dark:text-status-success-400" />
            ) : (
              <XCircle className="w-7 h-7 text-status-danger-500 dark:text-status-danger-400" />
            )}
            <div>
              <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
                {result.is_eligible ? t('legalCalculators.youMayQualifyForA', 'You May Qualify for a Fee Waiver') : t('legalCalculators.youMayNotQualifyFor', 'You May Not Qualify for a Full Fee Waiver')}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{result.eligibility_reason}</p>
            </div>
          </div>

          {result.automatic_eligibility && (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-3 mb-4">
              <p className="text-sm text-status-success-700 dark:text-status-success-300 font-medium">
                {t('legalCalculators.youMayAutomaticallyQualifyBased', 'You may automatically qualify based on your public benefits.')}
              </p>
            </div>
          )}

          {result.partial_waiver_available && (
            <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-3 mb-4">
              <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">
                {t('legalCalculators.aPartialFeeWaiver', "A partial fee waiver may be available even if you don't qualify for a full waiver.")}
              </p>
            </div>
          )}

          {result.required_documentation && result.required_documentation.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('legalCalculators.requiredDocumentation', 'Required Documentation')}</p>
              <ul className="space-y-1">
                {result.required_documentation.map((doc, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <ChevronRight className="w-4 h-4 text-lsc-rose flex-shrink-0" />
                    {doc}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.next_steps && result.next_steps.length > 0 && (
            <div>
              <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('legalCalculators.nextSteps', 'Next Steps')}</p>
              <ul className="space-y-1">
                {result.next_steps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="w-5 h-5 bg-lsc-rose text-white rounded-full flex items-center justify-center text-xs flex-shrink-0 mt-0.5">{idx + 1}</span>
                    {step}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.form_title && (
            <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-lsc-rose" />
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('legalCalculators.applicableForm', 'Applicable form:')} <span className="font-medium text-lsc-dark dark:text-earth-50">{result.form_title}</span>
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
        <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
          <strong>{t('legalCalculators.disclaimer', 'Disclaimer:')}</strong> {t('legalCalculators.thisIsAPreliminary', "This is a preliminary estimate only. Income limits vary by jurisdiction and are updated periodically. The court clerk's office makes the final determination on fee waiver applications. Contact your local self-help center for assistance completing the application.")}
        </p>
      </div>
    </div>
  )
}

// ==================== Expungement Eligibility ====================

function ExpungementCalculator() {
  const { t } = useTranslation()
  const [form, setForm] = useState({
    jurisdiction: '',
    offense_category: '',
    offense_type: '',
    conviction_date: '',
    sentence_completed_date: '',
  })
  const [result, setResult] = useState<ExpungementEligibilityResponse | null>(null)

  const offenseCategories = [
    { value: 'misdemeanor', label: t('legalCalculators.misdemeanor', 'Misdemeanor') },
    { value: 'felony', label: t('legalCalculators.felony', 'Felony') },
    { value: 'infraction', label: t('legalCalculators.infraction', 'Infraction') },
    { value: 'wobbler', label: t('legalCalculators.wobblerFelonymisdemeanor', 'Wobbler (felony/misdemeanor)') },
  ]

  const checkMutation = useMutation({
    mutationFn: () => checkExpungementEligibility(clean({
      jurisdiction: form.jurisdiction,
      offense_category: form.offense_category,
      offense_type: form.offense_type || null,
      conviction_date: form.conviction_date,
      sentence_completed_date: form.sentence_completed_date || undefined,
    })),
    onSuccess: (data) => setResult(data),
    onError: () => toast.error(t('legalCalculators.failedToCheckEligibilityPlease2')),
  })

  const formatDate = (dateStr: string) => {
    if (!dateStr) return null
    return parseDate(dateStr)?.toLocaleDateString(getCurrentLocale(), { month: 'long', day: 'numeric', year: 'numeric' }) ?? null
  }

  return (
    <div className="space-y-6">
      <div className="bg-category-50 dark:bg-category-900/20 border border-category-200 dark:border-category-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-category-600 dark:text-category-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-category-800 dark:text-category-200 text-sm">{t('legalCalculators.aboutExpungement', 'About Expungement')}</p>
            <p className="text-sm text-category-700 dark:text-category-300 mt-1">
              {t('legalCalculators.expungementAllowsCertainCriminal', 'Expungement allows certain criminal convictions to be dismissed from your record, which can help with employment, housing, and other opportunities. This tool provides a basic eligibility check — many factors affect actual eligibility. Consulting with an attorney is strongly recommended.')}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-5">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.jurisdictionState', 'Jurisdiction / State')} *
          </label>
          <input
            type="text"
            value={form.jurisdiction}
            onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
            placeholder={t('placeholder.legalCalculators.egCaliforniaTexas')}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.offenseCategory', 'Offense Category')} *
          </label>
          <select
            value={form.offense_category}
            onChange={e => setForm(f => ({ ...f, offense_category: e.target.value }))}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          >
            <option value="">{t('legalCalculators.selectOffenseType', 'Select offense type...')}</option>
            {offenseCategories.map(cat => (
              <option key={cat.value} value={cat.value}>{cat.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
            {t('legalCalculators.offenseDescriptionOptional', 'Offense Description (optional)')}
          </label>
          <input
            type="text"
            value={form.offense_type}
            onChange={e => setForm(f => ({ ...f, offense_type: e.target.value }))}
            placeholder={t('placeholder.legalCalculators.egPettyTheftDrug')}
            className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
          />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('legalCalculators.convictionDate', 'Conviction Date')} *
            </label>
            <input
              type="date"
              value={form.conviction_date}
              onChange={e => setForm(f => ({ ...f, conviction_date: e.target.value }))}
              className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
              {t('legalCalculators.sentenceCompletionDateIf', 'Sentence Completion Date (if applicable)')}
            </label>
            <input
              type="date"
              value={form.sentence_completed_date}
              onChange={e => setForm(f => ({ ...f, sentence_completed_date: e.target.value }))}
              className="w-full px-3 py-2.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('legalCalculators.includeProbationCompletion', 'Include probation completion')}</p>
          </div>
        </div>

        <button
          onClick={() => checkMutation.mutate()}
          disabled={!form.jurisdiction || !form.offense_category || !form.conviction_date || checkMutation.isPending}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium disabled:opacity-50"
        >
          {checkMutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <CheckCircle className="w-4 h-4" />
          )}
          {checkMutation.isPending ? t('legalCalculators.checking', 'Checking...') : t('legalCalculators.checkEligibility', 'Check Eligibility')}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-3 mb-5">
            {result.is_eligible ? (
              <CheckCircle className="w-7 h-7 text-status-success-600 dark:text-status-success-400" />
            ) : (
              <XCircle className="w-7 h-7 text-status-danger-500 dark:text-status-danger-400" />
            )}
            <div>
              <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
                {result.is_eligible ? t('legalCalculators.youMayBeEligible', 'You May Be Eligible for Expungement') : t('legalCalculators.youMayNotCurrentlyBe', 'You May Not Currently Be Eligible')}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{result.eligibility_notes}</p>
            </div>
          </div>

          {!result.waiting_period_met && result.waiting_period_end_date && (
            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-3 mb-4">
              <p className="text-sm text-status-warning-700 dark:text-status-warning-300">
                {t('legalCalculators.youMayBeEligibleAfter', 'You may be eligible after the waiting period ends:')} <strong>{formatDate(result.waiting_period_end_date)}</strong>
              </p>
            </div>
          )}

          {result.requirements && result.requirements.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('legalCalculators.requirements', 'Requirements')}</p>
              <ul className="space-y-1">
                {result.requirements.map((req, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
                    {req}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {result.exclusions && result.exclusions.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-2">{t('legalCalculators.potentialExclusions', 'Potential Exclusions')}</p>
              <ul className="space-y-1">
                {result.exclusions.map((excl, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <XCircle className="w-4 h-4 text-status-danger-500 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
                    {excl}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(result.estimated_timeline || result.estimated_cost !== null) && (
            <div className="grid sm:grid-cols-2 gap-4 mb-4 pt-4 border-t border-lsc-border dark:border-earth-700">
              {result.estimated_timeline && (
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('legalCalculators.estimatedTimeline', 'Estimated Timeline')}</p>
                  <p className="text-sm font-medium text-lsc-dark dark:text-earth-50">{result.estimated_timeline}</p>
                </div>
              )}
              {result.estimated_cost !== null && result.estimated_cost !== undefined && (
                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('legalCalculators.estimatedCost', 'Estimated Cost')}</p>
                  <p className="text-sm font-medium text-lsc-dark dark:text-earth-50">${result.estimated_cost}</p>
                </div>
              )}
            </div>
          )}

          {/* Help Links */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <a
              href="/legal"
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 text-sm font-medium"
            >
              <Scale className="w-4 h-4" />
              {t('legalCalculators.findLegalAid', 'Find Legal Aid')}
            </a>
            <a
              href="/legal/wizard"
              className="flex items-center gap-2 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm font-medium"
            >
              <FileText className="w-4 h-4" />
              {t('legalCalculators.findExpungementForms', 'Find Expungement Forms')}
            </a>
          </div>
        </div>
      )}

      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
        <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
          <strong>{t('legalCalculators.important', 'Important:')}</strong> {t('legalCalculators.expungementLawsAreComplex', 'Expungement laws are complex and vary significantly by state. Certain offenses (serious felonies, sex offenses) are generally not eligible. This tool provides a basic eligibility estimate only and is not a substitute for legal advice. Consult with an attorney or contact legal aid for help with your specific situation.')}
        </p>
      </div>
    </div>
  )
}

// ==================== Main Page ====================

export default function LegalCalculatorsPage(): React.ReactElement {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<CalcTab>('deadline')

  const TAB_CONTENT: Record<CalcTab, React.ReactNode> = {
    'deadline': <DeadlineCalculator />,
    'fee-waiver': <FeeWaiverCalculator />,
    'expungement': <ExpungementCalculator />,
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Calculator className="w-7 h-7 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                {t('legalCalculators.legalCalculators', 'Legal Calculators')}
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
                {t('legalCalculators.freeToolsToHelp', 'Free tools to help you understand deadlines, fees, and eligibility')}
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      <PageContainer className="py-6">
        {/* Emergency Help */}
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 mb-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-status-danger-800 dark:text-status-danger-200 text-sm">{t('legalCalculators.needImmediateLegalHelp')}</p>
              <p className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-0.5">
                {t('legalCalculators.forEmergenciesContactThe', 'For emergencies, contact the Legal Aid Hotline:')}&nbsp;
                <a href="tel:18005555555" className="font-medium underline">1-800-555-5555</a>
                &nbsp;{t('legalCalculators.orVisitThe', 'or visit the')} <a href="/legal" className="font-medium underline">{t('legalCalculators.legalResourceCenter', 'Legal Resource Center')}</a>.
              </p>
            </div>
          </div>
        </div>

        {/* Calculator selection cards (desktop) */}
        <div className="hidden sm:grid sm:grid-cols-3 gap-4 mb-6">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`text-left p-4 rounded-xl border-2 transition-all ${
                activeTab === tab.id
                  ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                  : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
              }`}
            >
              <div className={`mb-2 ${activeTab === tab.id ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                {tab.icon}
              </div>
              <p className={`font-semibold text-sm mb-1 ${activeTab === tab.id ? 'text-lsc-rose' : 'text-lsc-dark dark:text-earth-50'}`}>
                {t(tab.labelKey, tab.label)}
              </p>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t(tab.descriptionKey, tab.description)}</p>
            </button>
          ))}
        </div>

        {/* Mobile Tab Strip */}
        <div className="sm:hidden flex gap-2 overflow-x-auto scrollbar-hide pb-1 mb-6">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap flex-shrink-0 border ${
                activeTab === tab.id
                  ? 'bg-lsc-rose text-white border-lsc-rose'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700'
              }`}
            >
              {tab.icon}
              {t(tab.labelKey, tab.label)}
            </button>
          ))}
        </div>

        {/* Calculator Content */}
        {TAB_CONTENT[activeTab]}

        {/* Bottom Links */}
        <div className="mt-8 pt-6 border-t border-lsc-border dark:border-earth-700">
          <p className="text-sm font-medium text-lsc-dark dark:text-earth-50 mb-3">{t('legalCalculators.moreLegalResources', 'More Legal Resources')}</p>
          <div className="flex flex-wrap gap-3">
            <a href="/legal" className="flex items-center gap-1.5 text-sm text-lsc-rose hover:underline">
              <Scale className="w-4 h-4" />
              {t('legalCalculators.legalResourceCenter', 'Legal Resource Center')}
            </a>
            <a href="/legal/wizard" className="flex items-center gap-1.5 text-sm text-lsc-rose hover:underline">
              <FileText className="w-4 h-4" />
              {t('legalCalculators.documentWizard', 'Document Wizard')}
            </a>
            <a href="/legal?tab=clinics" className="flex items-center gap-1.5 text-sm text-lsc-rose hover:underline">
              <Calendar className="w-4 h-4" />
              {t('legalCalculators.freeLegalClinics', 'Free Legal Clinics')}
            </a>
          </div>
        </div>
      </PageContainer>
    </div>
  )
}
