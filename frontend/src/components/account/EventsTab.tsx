/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Calendar, Clock, MapPin, RefreshCw, Loader2, X, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { fetchApi } from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'
import ConfirmDialog from '../ConfirmDialog'
import type { MyEventRegistration } from '../../services/api'

interface EventsTabProps {
  events: MyEventRegistration[]
  eventsLoading: boolean
  onRefresh: () => void
  onCancelled?: (registrationId: number) => void
}

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase()
  if (s === 'confirmed') return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
  if (s === 'waitlisted') return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'
  return 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
}

export function EventsTab({ events, eventsLoading, onRefresh, onCancelled }: EventsTabProps): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [confirmingReg, setConfirmingReg] = useState<MyEventRegistration | null>(null)

  async function performCancel(reg: MyEventRegistration): Promise<void> {
    if (!user?.email) {
      toast.error(t('account.failedToCancelRegistration'))
      setConfirmingReg(null)
      return
    }
    setCancellingId(reg.id)
    try {
      await fetchApi(`/events/${reg.event_id}/register/${reg.id}`, { method: 'DELETE' })
      // Optimistically drop the cancelled registration from the visible list so
      // the UI updates instantly even if the parent's refetch is gated by a
      // briefly-null auth token. The refetch still runs as a backup.
      onCancelled?.(reg.id)
      toast.success(t('account.registrationCancelled'))
      onRefresh()
    } catch (_err) {
      toast.error(t('account.failedToCancelRegistration'))
    } finally {
      setCancellingId(null)
      setConfirmingReg(null)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('account.myEvents')}
        </h2>
        <button
          onClick={onRefresh}
          disabled={eventsLoading}
          aria-label={t('account.refresh')}
          className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 ${eventsLoading ? 'motion-safe:animate-spin' : ''}`} />
          {t('account.refresh')}
        </button>
      </div>

      {eventsLoading && events.length === 0 ? (
        <div className="flex justify-center py-12" role="status">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : events.length === 0 ? (
        <div className="text-center py-12">
          <Calendar className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('account.noUpcomingEvents')}
          </p>
          <a href="/events" className="inline-flex items-center gap-1 text-lsc-rose hover:text-lsc-rose/80 text-sm font-medium">
            {t('account.browseEvents')}
            <ChevronRight className="w-4 h-4" />
          </a>
        </div>
      ) : (
        <ul className="space-y-3">
          {events.map((reg) => {
            const start = reg.event_start_time ? new Date(reg.event_start_time) : null
            const end = reg.event_end_time ? new Date(reg.event_end_time) : null
            const now = new Date()
            const diffDays = start ? Math.ceil((start.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)) : null
            const isToday = diffDays === 0
            const isTomorrow = diffDays === 1
            const isCancelling = cancellingId === reg.id
            return (
              <li
                key={reg.id}
                className={`p-4 rounded-xl border-2 border-lsc-border bg-lsc-cream dark:bg-earth-800 ${isToday ? 'ring-2 ring-lsc-rose' : ''}`}
              >
                <div className="flex items-start gap-4">
                  {start && (
                    <div className={`text-center flex-shrink-0 rounded-xl p-2 min-w-[56px] ${isToday ? 'bg-lsc-rose text-white' : 'bg-lsc-white dark:bg-earth-700'}`}>
                      <span className={`block text-xs font-medium ${isToday ? 'text-white/90' : 'text-lsc-rose'}`}>
                        {start.toLocaleDateString(getCurrentLocale(), { month: 'short' })}
                      </span>
                      <span className={`block text-xl font-bold ${isToday ? 'text-white' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                        {start.getDate()}
                      </span>
                      <span className={`block text-xs ${isToday ? 'text-white/90' : 'text-lsc-dark/60 dark:text-lsc-cream/60'}`}>
                        {start.toLocaleDateString(getCurrentLocale(), { weekday: 'short' })}
                      </span>
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <a
                        href={`/events/${reg.event_id}`}
                        className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg hover:text-lsc-rose"
                      >
                        {reg.event_title}
                      </a>
                      <span className={`px-3 py-1 text-xs rounded-full font-medium ${statusBadgeClass(reg.status)}`}>
                        {reg.status}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {start && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {start.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })}
                          {end ? ` – ${end.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })}` : ''}
                        </span>
                      )}
                      {reg.event_location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate">{reg.event_location}</span>
                        </span>
                      )}
                      {reg.event_category && (
                        <span className="px-2 py-0.5 rounded-full bg-lsc-white dark:bg-earth-700 text-xs">
                          {reg.event_category}
                        </span>
                      )}
                      {diffDays !== null && (isToday || isTomorrow || diffDays > 0) && (
                        <span className="text-xs">
                          {isToday
                            ? t('account.today')
                            : isTomorrow
                            ? t('account.tomorrow')
                            : t('account.inDays', { count: diffDays })}
                        </span>
                      )}
                    </div>

                    {reg.reminder_requested && (
                      <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
                        {t('account.reminderOn')}
                      </p>
                    )}

                    <div className="flex items-center gap-3 mt-3">
                      <a
                        href={`/events/${reg.event_id}`}
                        className="text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
                      >
                        {t('account.viewEvent')}
                      </a>
                      <button
                        onClick={() => setConfirmingReg(reg)}
                        disabled={isCancelling}
                        className="inline-flex items-center gap-1 text-sm text-status-danger-600 hover:text-status-danger-700 dark:text-status-danger-400 disabled:opacity-50"
                      >
                        {isCancelling ? (
                          <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        ) : (
                          <X className="w-4 h-4" />
                        )}
                        {t('account.cancelRegistration')}
                      </button>
                    </div>
                  </div>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      <ConfirmDialog
        isOpen={!!confirmingReg}
        title={t('account.cancelRegistration')}
        message={confirmingReg ? t('account.confirmCancelRegistration', { title: confirmingReg.event_title }) : ''}
        confirmText={t('account.cancelRegistration')}
        confirmVariant="danger"
        loading={cancellingId !== null}
        onConfirm={() => {
          if (confirmingReg) {
            void performCancel(confirmingReg)
          }
        }}
        onCancel={() => setConfirmingReg(null)}
      />
    </div>
  )
}
