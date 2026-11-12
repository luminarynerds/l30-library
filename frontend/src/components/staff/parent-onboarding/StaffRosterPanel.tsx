/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import * as Sentry from "@/lib/sentry-lazy"
import {
  getChildcareRoster,
  updateChildcareRegistration,
  type ChildcareRegistration,
  type ChildcareRegistrationStatus,
} from '@/api/parent-onboarding-api'
import { useTranslation } from '@/i18n'

function formatChildAge(months: number | undefined | null): string {
  if (months == null) return ''
  const safe = Math.max(0, Math.floor(months))
  const y = Math.floor(safe / 12)
  const m = safe % 12
  if (y === 0) return `${m}mo`
  return `${y}y ${m}m`
}

function regStatusBadgeClasses(status: ChildcareRegistrationStatus | string): string {
  const map: Record<string, string> = {
    registered: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
    checked_in: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
    checked_out: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
    no_show: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    cancelled: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
  }
  return map[status as string] ?? 'bg-earth-100 text-earth-800'
}

export function StaffRosterPanel({
  sessionId,
  pickupFlagOn,
  onCheckout,
  onMarkNoShow,
}: {
  sessionId: number
  pickupFlagOn: boolean
  onCheckout: (reg: ChildcareRegistration) => void
  onMarkNoShow: (reg: ChildcareRegistration) => void
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['childcare-roster', sessionId],
    queryFn: () => getChildcareRoster(sessionId),
  })

  const checkInMutation = useMutation({
    mutationFn: (registrationId: number) =>
      updateChildcareRegistration(registrationId, { status: 'checked_in' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['childcare-roster', sessionId] })
      queryClient.invalidateQueries({ queryKey: ['childcare-sessions'] })
      toast.success(t('parentOnboarding.childcare.roster.checkInButton'))
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.childcare.roster.checkInError'))
    },
  })

  if (isLoading) return <p className="text-xs">{t('parentOnboarding.childcare.roster.loading')}</p>
  if (error) return <p className="text-xs text-status-danger-700">{t('parentOnboarding.childcare.roster.loadFailed')}</p>
  const entries = data?.entries ?? []
  if (entries.length === 0) {
    return <p className="text-xs">{t('parentOnboarding.childcare.roster.empty')}</p>
  }

  const counts = data?.counts ?? entries.reduce(
    (acc, e) => {
      const s = e.registration.status as string
      if (s === 'registered') acc.registered++
      else if (s === 'checked_in') acc.checked_in++
      else if (s === 'checked_out') acc.checked_out++
      else if (s === 'no_show') acc.no_show++
      else if (s === 'cancelled') acc.cancelled++
      return acc
    },
    { registered: 0, checked_in: 0, checked_out: 0, no_show: 0, cancelled: 0 },
  )

  return (
    <div className="space-y-2 text-xs">
      {/* Count chips */}
      <ul
        className="flex flex-wrap gap-1.5"
        aria-label={t('parentOnboarding.childcare.roster.countsLabel')}
      >
        <li className={`px-2 py-0.5 rounded ${regStatusBadgeClasses('registered')}`}>
          {t('parentOnboarding.childcare.roster.countRegistered', { count: counts.registered })}
        </li>
        <li className={`px-2 py-0.5 rounded ${regStatusBadgeClasses('checked_in')}`}>
          {t('parentOnboarding.childcare.roster.countCheckedIn', { count: counts.checked_in })}
        </li>
        <li className={`px-2 py-0.5 rounded ${regStatusBadgeClasses('checked_out')}`}>
          {t('parentOnboarding.childcare.roster.countCheckedOut', { count: counts.checked_out })}
        </li>
        <li className={`px-2 py-0.5 rounded ${regStatusBadgeClasses('no_show')}`}>
          {t('parentOnboarding.childcare.roster.countNoShow', { count: counts.no_show })}
        </li>
      </ul>

      <ul className="space-y-2" data-testid="roster-row-list">
        {entries.map((e) => {
          const reg = e.registration
          const status = reg.status as string
          const hasAllergy = !!(reg.special_needs_notes && /allerg/i.test(reg.special_needs_notes))
          const isRegistered = status === 'registered'
          const isCheckedIn = status === 'checked_in'
          const isCheckedOut = status === 'checked_out'
          const ageDisplay = formatChildAge(reg.child_age_months)
          return (
            <li
              key={reg.id}
              className="flex items-start justify-between gap-2 p-2 rounded border border-lsc-border dark:border-earth-700"
              data-testid={`roster-row-${reg.id}`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium">{reg.child_name}</span>
                  {ageDisplay && (
                    <span className="text-lsc-dark/60 dark:text-lsc-cream/60">{ageDisplay}</span>
                  )}
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded ${regStatusBadgeClasses(status)}`}
                  >
                    {status.replace(/_/g, ' ')}
                  </span>
                  {hasAllergy && (
                    <span
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400"
                      aria-label={t('parentOnboarding.childcare.roster.allergyChip', { text: reg.special_needs_notes ?? '' })}
                    >
                      <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                      <span>{t('parentOnboarding.childcare.roster.allergyChipShort')}</span>
                    </span>
                  )}
                </div>
                <div className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                  {t('parentOnboarding.childcare.roster.parentLine', { name: e.parent_name })}
                </div>
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                {isRegistered && (
                  <>
                    <button
                      type="button"
                      onClick={() => checkInMutation.mutate(reg.id)}
                      disabled={checkInMutation.isPending}
                      data-testid={`check-in-${reg.id}`}
                      className="px-2 py-1 text-xs rounded bg-status-success-700 text-white disabled:opacity-50"
                    >
                      {t('parentOnboarding.childcare.roster.checkInButton')}
                    </button>
                    <button
                      type="button"
                      onClick={() => onMarkNoShow(reg)}
                      data-testid={`mark-no-show-${reg.id}`}
                      className="px-2 py-1 text-xs rounded border border-status-danger-300 text-status-danger-700 dark:text-status-danger-300"
                    >
                      {t('parentOnboarding.childcare.roster.noShowButton')}
                    </button>
                  </>
                )}
                {isCheckedIn && (
                  <button
                    type="button"
                    onClick={() => onCheckout(reg)}
                    disabled={!pickupFlagOn}
                    title={pickupFlagOn ? undefined : t('parentOnboarding.childcare.roster.checkoutNeedsFlag')}
                    data-testid={`check-out-${reg.id}`}
                    className="px-2 py-1 text-xs rounded bg-lsc-rose text-white disabled:opacity-50"
                  >
                    {t('parentOnboarding.childcare.roster.checkOutButton')}
                  </button>
                )}
                {isCheckedOut && (
                  <span className="px-2 py-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    {t('parentOnboarding.childcare.roster.alreadyCheckedOut')}
                  </span>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
