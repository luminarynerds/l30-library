/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bell,
  ChevronLeft,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  AlertTriangle,
  PowerOff,
  Power,
} from 'lucide-react'
import toast from 'react-hot-toast'
import StandardPageLayout from '@/components/StandardPageLayout'
import { US_STATES_MAP } from '@/components/ban-tracker/ban-tracker-data'
import {
  createSubscription,
  deleteSubscription,
  isDuplicateSubscriptionError,
  updateSubscription,
  useBanTrackerSubscriptions,
  type BanTrackerSubscription,
} from '@/hooks/useBanTrackerSubscriptions'
import {
  SubscriptionForm,
  type SubscriptionFormValue,
} from '@/components/ban-tracker/SubscriptionForm'
import { usePageTitle } from '@/hooks/usePageTitle'
import { t } from '@/i18n'

function describeScope(sub: BanTrackerSubscription): string {
  if (sub.scope === 'any') return 'All ban reports nationwide'
  if (sub.scope === 'state') {
    const code = sub.state_filter ?? ''
    return `Ban reports in ${(US_STATES_MAP[code] ?? code) || 'a state'}`
  }
  if (sub.scope === 'catalog') return 'Books in our catalog'
  return sub.scope
}

function describeBanType(sub: BanTrackerSubscription): string {
  switch (sub.ban_type_filter) {
    case 'banned':
      return 'Banned only'
    case 'restricted':
      return 'Restricted only'
    case 'challenged':
      return 'Challenged only'
    default:
      return 'Any report type'
  }
}

function describeFrequency(sub: BanTrackerSubscription): string {
  return sub.frequency === 'daily' ? 'Daily digest' : 'Weekly digest'
}

function formatLastSent(value: string | null): string | null {
  if (!value) return null
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function SubscriptionCard({
  sub,
  onEdit,
  onDelete,
  onToggleActive,
}: {
  sub: BanTrackerSubscription
  onEdit: () => void
  onDelete: () => void
  onToggleActive: () => void
}): React.ReactElement {
  const lastSent = formatLastSent(sub.last_sent_at)
  return (
    <article
      className={`bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 ${
        sub.is_active ? '' : 'opacity-70'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            {describeScope(sub)}
          </h3>
          <ul className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-0.5">
            <li>{describeBanType(sub)}</li>
            <li>{describeFrequency(sub)}</li>
            {lastSent && <li>Last sent: {lastSent}</li>}
            {!sub.is_active && (
              <li className="text-status-warning-700 dark:text-status-warning-300">
                Paused
              </li>
            )}
          </ul>
        </div>
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg"
          >
            <Pencil className="w-4 h-4" aria-hidden="true" />
            Edit
          </button>
          <button
            type="button"
            onClick={onToggleActive}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg"
          >
            {sub.is_active ? (
              <>
                <PowerOff className="w-4 h-4" aria-hidden="true" />
                Pause
              </>
            ) : (
              <>
                <Power className="w-4 h-4" aria-hidden="true" />
                Resume
              </>
            )}
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-status-danger-700 dark:text-status-danger-300 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/30 rounded-lg"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>
    </article>
  )
}

export default function BanTrackerSubscriptionsPage(): React.ReactElement {
  usePageTitle(t('banTracker.pageTitle', 'My Ban Tracker Subscriptions'))
  const { subscriptions, loading, error, refetch } = useBanTrackerSubscriptions()
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleCreate = async (value: SubscriptionFormValue) => {
    setSubmitting(true)
    try {
      await createSubscription({
        scope: value.scope,
        frequency: value.frequency,
        state_filter: value.state_filter,
        ban_type_filter: value.ban_type_filter,
      })
      toast.success('Subscription created.')
      setCreating(false)
      await refetch()
    } catch (err: unknown) {
      if (isDuplicateSubscriptionError(err)) {
        toast.error('You already have a subscription with these filters.')
      } else {
        const message = err instanceof Error ? err.message : 'Could not create subscription'
        toast.error(message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleUpdate = (id: number) => async (value: SubscriptionFormValue) => {
    setSubmitting(true)
    try {
      await updateSubscription(id, {
        scope: value.scope,
        frequency: value.frequency,
        state_filter: value.state_filter,
        ban_type_filter: value.ban_type_filter,
      })
      toast.success('Subscription updated.')
      setEditingId(null)
      await refetch()
    } catch (err: unknown) {
      if (isDuplicateSubscriptionError(err)) {
        toast.error('A subscription with those filters already exists.')
      } else {
        const message = err instanceof Error ? err.message : 'Could not update subscription'
        toast.error(message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (sub: BanTrackerSubscription) => {
    const confirmed = window.confirm(
      `Delete subscription "${describeScope(sub)}"? You can always create a new one.`,
    )
    if (!confirmed) return
    try {
      await deleteSubscription(sub.id)
      toast.success('Subscription deleted.')
      await refetch()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Could not delete subscription'
      toast.error(message)
    }
  }

  const handleToggleActive = async (sub: BanTrackerSubscription) => {
    try {
      await updateSubscription(sub.id, { is_active: !sub.is_active })
      toast.success(sub.is_active ? 'Subscription paused.' : 'Subscription resumed.')
      await refetch()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Could not update subscription'
      toast.error(message)
    }
  }

  return (
    <StandardPageLayout
      title="My Ban Tracker Subscriptions"
      subtitle="Choose how often you hear about new book bans and which categories matter most."
      icon={Bell}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/ban-tracker"
          className="inline-flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          Back to Ban Tracker
        </Link>
        {!creating && (
          <button
            type="button"
            onClick={() => {
              setCreating(true)
              setEditingId(null)
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            New subscription
          </button>
        )}
      </div>

      {creating && (
        <section
          aria-labelledby="new-subscription-heading"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6"
        >
          <h2
            id="new-subscription-heading"
            className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4"
          >
            New subscription
          </h2>
          <SubscriptionForm
            idPrefix="ban-tracker-new"
            submitLabel="Create subscription"
            submitting={submitting}
            onSubmit={handleCreate}
            onCancel={() => setCreating(false)}
          />
        </section>
      )}

      {error && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-700 rounded-xl p-4 text-status-danger-700 dark:text-status-danger-300 text-sm flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          Loading subscriptions…
        </div>
      ) : subscriptions.length === 0 && !creating ? (
        <section className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
          <Bell
            className="w-10 h-10 mx-auto text-lsc-rose dark:text-lsc-rose-light mb-3"
            aria-hidden="true"
          />
          <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1">
            No subscriptions yet
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Create a subscription to start receiving digests when new ban reports match.
          </p>
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            Create your first subscription
          </button>
        </section>
      ) : (
        <ul className="space-y-3 list-none p-0">
          {subscriptions.map((sub) => (
            <li key={sub.id}>
              {editingId === sub.id ? (
                <section
                  aria-label={`Edit subscription ${sub.id}`}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6"
                >
                  <h3 className="font-serif text-base font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                    Edit subscription
                  </h3>
                  <SubscriptionForm
                    idPrefix={`ban-tracker-edit-${sub.id}`}
                    initial={sub}
                    submitLabel="Save changes"
                    submitting={submitting}
                    onSubmit={handleUpdate(sub.id)}
                    onCancel={() => setEditingId(null)}
                  />
                </section>
              ) : (
                <SubscriptionCard
                  sub={sub}
                  onEdit={() => {
                    setEditingId(sub.id)
                    setCreating(false)
                  }}
                  onDelete={() => handleDelete(sub)}
                  onToggleActive={() => handleToggleActive(sub)}
                />
              )}
            </li>
          ))}
        </ul>
      )}
    </StandardPageLayout>
  )
}
