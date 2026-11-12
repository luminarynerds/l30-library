/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { US_STATES_LIST, US_STATES_MAP } from '@/components/ban-tracker/ban-tracker-data'
import type {
  BanTrackerSubscription,
  SubscriptionBanType,
  SubscriptionFrequency,
  SubscriptionScope,
} from '@/hooks/useBanTrackerSubscriptions'

const SCOPE_OPTIONS: { value: SubscriptionScope; label: string }[] = [
  { value: 'any', label: 'All ban reports nationwide' },
  { value: 'state', label: 'A specific state' },
  { value: 'catalog', label: 'Books in our catalog' },
]

const BAN_TYPE_OPTIONS: { value: '' | SubscriptionBanType; label: string }[] = [
  { value: '', label: 'Any (banned, restricted, or challenged)' },
  { value: 'banned', label: 'Banned only' },
  { value: 'restricted', label: 'Restricted only' },
  { value: 'challenged', label: 'Challenged only' },
]

const FREQUENCY_OPTIONS: { value: SubscriptionFrequency; label: string }[] = [
  { value: 'weekly', label: 'Weekly digest' },
  { value: 'daily', label: 'Daily digest' },
]

export interface SubscriptionFormValue {
  scope: SubscriptionScope
  state_filter: string | null
  ban_type_filter: SubscriptionBanType | null
  frequency: SubscriptionFrequency
}

interface SubscriptionFormProps {
  initial?: BanTrackerSubscription | null
  submitting: boolean
  submitLabel: string
  /**
   * Stable suffix used to disambiguate label/input ids when multiple form
   * instances render on the same page (e.g. the CTA on the public page plus
   * an inline edit form on the management page).
   */
  idPrefix: string
  onSubmit: (value: SubscriptionFormValue) => void
  onCancel: () => void
}

function coerceScope(v: string | undefined): SubscriptionScope {
  return v === 'state' || v === 'catalog' ? v : 'any'
}

function coerceBanType(v: string | null | undefined): '' | SubscriptionBanType {
  if (v === 'banned' || v === 'restricted' || v === 'challenged') return v
  return ''
}

function coerceFrequency(v: string | undefined): SubscriptionFrequency {
  return v === 'daily' ? 'daily' : 'weekly'
}

export function SubscriptionForm({
  initial,
  submitting,
  submitLabel,
  idPrefix,
  onSubmit,
  onCancel,
}: SubscriptionFormProps): React.ReactElement {
  const [scope, setScope] = useState<SubscriptionScope>(coerceScope(initial?.scope))
  const [stateFilter, setStateFilter] = useState<string>(initial?.state_filter ?? '')
  const [banTypeFilter, setBanTypeFilter] = useState<'' | SubscriptionBanType>(
    coerceBanType(initial?.ban_type_filter),
  )
  const [frequency, setFrequency] = useState<SubscriptionFrequency>(coerceFrequency(initial?.frequency))

  const stateRequired = scope === 'state'
  const stateInvalid = stateRequired && !stateFilter

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (stateInvalid) return
    onSubmit({
      scope,
      state_filter: scope === 'state' ? stateFilter : null,
      ban_type_filter: banTypeFilter || null,
      frequency,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor={`${idPrefix}-scope`}
          className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
        >
          What to follow
        </label>
        <select
          id={`${idPrefix}-scope`}
          value={scope}
          onChange={(e) => setScope(e.target.value as SubscriptionScope)}
          className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
        >
          {SCOPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {scope === 'state' && (
        <div>
          <label
            htmlFor={`${idPrefix}-state`}
            className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
          >
            State<span aria-hidden="true"> *</span>
          </label>
          <select
            id={`${idPrefix}-state`}
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            required
            aria-invalid={stateInvalid}
            className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          >
            <option value="">Select state…</option>
            {US_STATES_LIST.map((s) => (
              <option key={s} value={s}>
                {US_STATES_MAP[s] ?? s}
              </option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label
          htmlFor={`${idPrefix}-ban-type`}
          className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
        >
          Report type
        </label>
        <select
          id={`${idPrefix}-ban-type`}
          value={banTypeFilter}
          onChange={(e) => setBanTypeFilter(e.target.value as '' | SubscriptionBanType)}
          className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
        >
          {BAN_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value || 'any'} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label
          htmlFor={`${idPrefix}-frequency`}
          className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
        >
          How often
        </label>
        <select
          id={`${idPrefix}-frequency`}
          value={frequency}
          onChange={(e) => setFrequency(e.target.value as SubscriptionFrequency)}
          className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
        >
          {FREQUENCY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting || stateInvalid}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
          {submitting ? 'Saving…' : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

export default SubscriptionForm
