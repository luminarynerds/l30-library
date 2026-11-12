/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bell, LogIn, Settings, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  createSubscription,
  isDuplicateSubscriptionError,
  useBanTrackerSubscriptions,
} from '@/hooks/useBanTrackerSubscriptions'
import { SubscriptionForm, type SubscriptionFormValue } from '@/components/ban-tracker/SubscriptionForm'

const PANEL_CLASS =
  'bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6'

export function SubscribeCTA(): React.ReactElement {
  const { isAuthenticated } = useAuth()
  const { subscriptions, loading, refetch } = useBanTrackerSubscriptions()
  const [formOpen, setFormOpen] = useState(false)
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
      toast.success('Subscribed. We will let you know when new reports match.')
      setFormOpen(false)
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

  if (!isAuthenticated) {
    return (
      <section
        aria-labelledby="ban-tracker-cta-heading"
        className={PANEL_CLASS}
      >
        <div className="flex items-start gap-4">
          <Bell
            className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-1"
            aria-hidden="true"
          />
          <div className="flex-1">
            <h3
              id="ban-tracker-cta-heading"
              className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1"
            >
              Get alerts when new bans are reported
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Sign in to follow ban reports in your state, by category, or across our catalog.
            </p>
            <Link
              to="/login"
              state={{ from: '/ban-tracker' }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white text-sm font-semibold rounded-lg transition-colors"
            >
              <LogIn className="w-4 h-4" aria-hidden="true" />
              Sign in to subscribe
            </Link>
          </div>
        </div>
      </section>
    )
  }

  if (loading) {
    return (
      <section className={PANEL_CLASS} aria-busy="true">
        <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
          Loading your subscriptions…
        </div>
      </section>
    )
  }

  if (subscriptions.length > 0) {
    return (
      <section
        aria-labelledby="ban-tracker-cta-heading"
        className={PANEL_CLASS}
      >
        <div className="flex items-start gap-4">
          <Bell
            className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-1"
            aria-hidden="true"
          />
          <div className="flex-1">
            <h3
              id="ban-tracker-cta-heading"
              className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1"
            >
              You are following {subscriptions.length}{' '}
              {subscriptions.length === 1 ? 'category' : 'categories'}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Manage filters, frequency, and which alerts you receive.
            </p>
            <Link
              to="/account/ban-tracker-subscriptions"
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white text-sm font-semibold rounded-lg transition-colors"
            >
              <Settings className="w-4 h-4" aria-hidden="true" />
              Manage subscriptions
            </Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section
      aria-labelledby="ban-tracker-cta-heading"
      className={PANEL_CLASS}
    >
      <div className="flex items-start gap-4">
        <Bell
          className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-1"
          aria-hidden="true"
        />
        <div className="flex-1">
          <h3
            id="ban-tracker-cta-heading"
            className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1"
          >
            Get alerts when new bans are reported
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            Follow ban reports in your state, by category, or across our catalog. Daily or
            weekly digest, your choice.
          </p>
          {!formOpen ? (
            <button
              type="button"
              onClick={() => setFormOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white text-sm font-semibold rounded-lg transition-colors"
            >
              <Bell className="w-4 h-4" aria-hidden="true" />
              Get alerts
            </button>
          ) : (
            <SubscriptionForm
              idPrefix="ban-tracker-cta"
              submitLabel="Subscribe"
              submitting={submitting}
              onSubmit={handleCreate}
              onCancel={() => setFormOpen(false)}
            />
          )}
        </div>
      </div>
    </section>
  )
}

export default SubscribeCTA
