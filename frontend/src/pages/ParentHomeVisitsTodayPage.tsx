/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff "Today's route" home-visit day plan.
 *
 * Mounts at /staff/parent-onboarding/home-visits/today. Feature flag:
 * home_visit_day_plan_enabled. Renders an ordered list of the current
 * staff visitor's stops with:
 *
 *   - An interactive Leaflet+OpenStreetMap map (lazy-loaded so the
 *     entry chunk doesn't bloat -- see feedback_l30_perf_entry_chunk_audit).
 *   - A static-map fallback (no JS map, just an inline-tiled OSM image)
 *     for print, slow connections, prefers-reduced-motion.
 *   - Per-stop access notes (steps, dog, primary language, parking).
 *   - Manual up/down sort.
 *   - "Couldn't locate" badges + a manual-pin button for stops with
 *     no geocode.
 *
 * Accessibility:
 *   - sr-only ordered list summarizes every stop independent of the map.
 *     The map is enhancement, not the only path.
 *   - Default mode meets WCAG AA per feedback_l30_essentials_not_accessible_layer.
 *   - prefers-reduced-motion users land in static mode by default.
 *   - Each badge has icon + text (never color-only).
 */
import { useEffect, useMemo, useState, lazy, Suspense } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import {
  Loader2, MapPin, Clock, Printer, Map as MapIcon,
  Image as ImageIcon, RefreshCw, ArrowUp, ArrowDown,
  AlertTriangle, Pencil, Dog, Building2, Languages,
  ParkingCircle, RotateCcw,
} from 'lucide-react'
import toast from 'react-hot-toast'

import {
  getHomeVisitDayPlan,
  setHomeVisitDayPlanSort,
  setHomeVisitAccessNotes,
  geocodeHomeVisit,
  type DayPlanResponse,
  type DayPlanStop,
  type HomeVisitAccessNotesUpsert,
} from '@/api/parent-onboarding-api'
import { useTranslation } from '@/i18n'
import { usePiiAccessLog } from '@/hooks/usePiiAccessLog'
import { AdminShell } from '../components/shells/AdminShell'
import { todayLocalYMD } from './parentHomeVisitsHelpers'

// Lazy-import the map so Leaflet and its CSS only land in this route's chunk.
const DayPlanMap = lazy(() => import('../components/parent-onboarding/DayPlanMap'))

function detectStaticPreferred(): boolean {
  if (typeof window === 'undefined') return false
  // Prefer reduced motion users land in static mode by default.
  try {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return true
  } catch {
    /* matchMedia not supported -- fall through */
  }
  // Slow connection? Save the bandwidth.
  // navigator.connection is non-standard but supported in Chromium.
  const conn = (navigator as unknown as { connection?: { effectiveType?: string } })
    .connection
  const eff = conn?.effectiveType
  if (eff === 'slow-2g' || eff === '2g') return true
  return false
}

export default function ParentHomeVisitsTodayPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const logPii = usePiiAccessLog()

  // ISO date in viewer's local tz so a 5pm Pacific load shows today, not
  // tomorrow UTC. Datepicker is plain HTML for now; future spec extends.
  const [dateStr, setDateStr] = useState(todayLocalYMD())
  const [staticMode, setStaticMode] = useState<boolean>(detectStaticPreferred())
  const [editingPatronId, setEditingPatronId] = useState<number | null>(null)

  const queryKey = useMemo(() => ['day-plan', dateStr] as const, [dateStr])
  const { data, isLoading, error, refetch } = useQuery<DayPlanResponse>({
    queryKey,
    queryFn: () => getHomeVisitDayPlan(dateStr),
  })

  // PII audit: viewing this page reveals each patron's home address.
  // One row per unique patron, action='read'. Fire-and-forget.
  useEffect(() => {
    if (!data?.stops?.length) return
    const seen = new Set<number>()
    for (const stop of data.stops) {
      if (seen.has(stop.patron_id)) continue
      seen.add(stop.patron_id)
      logPii({
        patronId: stop.patron_id,
        subjectType: 'home_visit_address',
        action: 'read',
        reason: 'day_plan_view',
      })
    }
  }, [data, logPii])

  // Force static mode on @media print.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mql = window.matchMedia('print')
    const handler = (e: MediaQueryListEvent) => {
      if (e.matches) setStaticMode(true)
    }
    try {
      mql.addEventListener('change', handler)
      return () => mql.removeEventListener('change', handler)
    } catch {
      // Older Safari falls back to addListener.
      mql.addListener?.(handler)
      return () => mql.removeListener?.(handler)
    }
  }, [])

  const sortMutation = useMutation({
    mutationFn: (vars: { visitId: number; sortIndex: number | null }) =>
      setHomeVisitDayPlanSort(vars.visitId, vars.sortIndex),
    onSuccess: (resp) => {
      queryClient.setQueryData(queryKey, resp)
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.homeVisits.today.sortFailed', 'Could not reorder'))
    },
  })

  const geocodeMutation = useMutation({
    mutationFn: (visitId: number) => geocodeHomeVisit(visitId),
    onSuccess: () => {
      refetch()
    },
    onError: (err) => {
      Sentry.captureException(err)
      toast.error(
        t(
          'parentOnboarding.homeVisits.today.geocodeFailed',
          'Could not locate this address',
        ),
      )
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error) {
    Sentry.captureException(error)
    return (
      <AdminShell title={t('parentOnboarding.homeVisits.today.titleShort', "Today's route")}>
        <div className="max-w-4xl mx-auto p-6">
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center">
            <AlertTriangle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" aria-hidden="true" />
            <p className="text-status-danger-700 dark:text-status-danger-300">
              {t(
                'parentOnboarding.homeVisits.today.failedToLoad',
                'Failed to load your day plan',
              )}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="mt-3 px-4 py-2 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-sm"
            >
              {t('common.retry', 'Retry')}
            </button>
          </div>
        </div>
      </AdminShell>
    )
  }

  const stops = data?.stops ?? []
  const warnings = data?.warnings ?? []
  const stopsWithCoords = stops.filter(
    (s): s is DayPlanStop & { lat: number; lng: number } =>
      s.lat != null && s.lng != null,
  )

  const editingStop =
    editingPatronId != null
      ? stops.find((s) => s.patron_id === editingPatronId) ?? null
      : null

  const handleMoveUp = (idx: number) => {
    if (idx === 0) return
    const target = stops[idx]
    if (!target) return
    sortMutation.mutate({ visitId: target.visit_id, sortIndex: idx })
  }
  const handleMoveDown = (idx: number) => {
    if (idx >= stops.length - 1) return
    const target = stops[idx]
    if (!target) return
    sortMutation.mutate({ visitId: target.visit_id, sortIndex: idx + 2 })
  }
  const handleResetSort = (visitId: number) => {
    sortMutation.mutate({ visitId, sortIndex: null })
  }

  return (
    <AdminShell title={t('parentOnboarding.homeVisits.today.titleShort', "Today's route")}>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('parentOnboarding.homeVisits.today.title', { count: stops.length })}
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('parentOnboarding.homeVisits.today.totalDriving', {
                minutes: data?.total_drive_minutes ?? 0,
              })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('parentOnboarding.homeVisits.today.date', 'Date')}{' '}
              <input
                type="date"
                value={dateStr}
                onChange={(e) => setDateStr(e.target.value)}
                className="ml-1 px-2 py-1 rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-white dark:bg-lsc-dark text-sm"
              />
            </label>
            <button
              type="button"
              onClick={() => setStaticMode((m) => !m)}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20"
              aria-pressed={staticMode}
            >
              {staticMode ? (
                <>
                  <MapIcon className="w-4 h-4" aria-hidden="true" />
                  {t('parentOnboarding.homeVisits.today.interactiveMode', 'Interactive map')}
                </>
              ) : (
                <>
                  <ImageIcon className="w-4 h-4" aria-hidden="true" />
                  {t('parentOnboarding.homeVisits.today.staticMode', 'Static map')}
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20"
              data-testid="print-day-plan"
            >
              <Printer className="w-4 h-4" aria-hidden="true" />
              {t('parentOnboarding.homeVisits.today.print', 'Print')}
            </button>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-lsc-rose/10 text-lsc-rose hover:bg-lsc-rose/20"
              aria-label={t('common.refresh', 'Refresh')}
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* sr-only stop list. Always present, even with map. Screen-reader users
            get the full day plan without needing to interpret the map. */}
        <ol className="sr-only" aria-label={t('parentOnboarding.homeVisits.today.srListLabel', 'Day plan stops')}>
          {stops.map((s, idx) => (
            <li key={s.visit_id}>
              {t('parentOnboarding.homeVisits.today.srStop', {
                n: idx + 1,
                time: s.scheduled_time ?? '',
                name: s.patron_name ?? '',
                address: s.address ?? '',
              })}
            </li>
          ))}
        </ol>

        {/* Map (interactive or static). Always renders behind the address list
            below so the page is useful even if the map fails. */}
        {stops.length > 0 ? (
          staticMode ? (
            <StaticMapView stops={stopsWithCoords} />
          ) : (
            <Suspense
              fallback={
                <div className="h-64 bg-lsc-cream/40 dark:bg-lsc-dark/40 rounded-xl flex items-center justify-center">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
                </div>
              }
            >
              <DayPlanMap stops={stopsWithCoords} />
            </Suspense>
          )
        ) : null}

        {/* Empty state */}
        {stops.length === 0 ? (
          <div className="bg-lsc-cream/60 dark:bg-lsc-dark/40 rounded-xl p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('parentOnboarding.homeVisits.today.noVisitsToday', 'No visits scheduled for this date.')}
          </div>
        ) : null}

        {/* Address list (visible). Each card includes scheduled time, address,
            badges for access notes, and reorder controls. */}
        <ol className="space-y-3" aria-label={t('parentOnboarding.homeVisits.today.listLabel', 'Day plan stops')}>
          {stops.map((stop, idx) => (
            <li
              key={stop.visit_id}
              className="bg-white dark:bg-lsc-dark border border-lsc-dark/10 dark:border-lsc-cream/10 rounded-xl p-4 shadow-sm break-inside-avoid"
              data-testid={`day-plan-stop-${idx + 1}`}
            >
              {/* Leg from previous stop */}
              {stop.leg_from_previous ? (
                <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">
                  {t('parentOnboarding.homeVisits.today.leg', {
                    drive: stop.leg_from_previous.drive_minutes,
                    walk: stop.leg_from_previous.walk_minutes,
                  })}
                  {stop.leg_from_previous.provider === 'haversine' ? (
                    <span className="ml-2 italic">
                      {t(
                        'parentOnboarding.homeVisits.today.estimateOnly',
                        '(estimate only — routing unavailable)',
                      )}
                    </span>
                  ) : null}
                </div>
              ) : null}

              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('parentOnboarding.homeVisits.today.stopN', { n: idx + 1 })}
                    </span>
                    {stop.scheduled_time ? (
                      <span className="inline-flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <Clock className="w-3.5 h-3.5" aria-hidden="true" /> {stop.scheduled_time}
                      </span>
                    ) : null}
                    {stop.patron_name ? (
                      <span
                        className="text-sm text-lsc-dark dark:text-lsc-cream"
                        lang={stop.access_notes?.primary_language ?? undefined}
                      >
                        {stop.patron_name}
                      </span>
                    ) : null}
                    {stop.manual_order ? (
                      <span className="text-xs px-2 py-0.5 rounded bg-lsc-rose/10 text-lsc-rose">
                        {t('parentOnboarding.homeVisits.today.manualOrder', 'Manual order')}
                      </span>
                    ) : null}
                  </div>
                  {stop.address ? (
                    <div className="mt-1 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 inline-flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 inline" aria-hidden="true" />
                      {stop.address}
                    </div>
                  ) : null}
                  {/* No-geocode badge */}
                  {stop.lat == null || stop.lng == null ? (
                    <div className="mt-2 inline-flex items-center gap-2 text-xs text-status-warning-700 dark:text-status-warning-300 bg-status-warning-50 dark:bg-status-warning-900/20 px-2 py-1 rounded">
                      <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                      {t(
                        'parentOnboarding.homeVisits.today.noGeocode',
                        "Couldn't locate this address on the map",
                      )}
                      <button
                        type="button"
                        onClick={() => geocodeMutation.mutate(stop.visit_id)}
                        className="ml-2 underline"
                      >
                        {t('parentOnboarding.homeVisits.today.tryAgain', 'Try again')}
                      </button>
                    </div>
                  ) : null}

                  {/* Access-notes badges (icon + text, never color-only) */}
                  {stop.access_notes ? (
                    <ul className="mt-2 flex flex-wrap gap-2 text-xs">
                      {stop.access_notes.has_steps ? (
                        <Badge icon={<Building2 className="w-3 h-3" aria-hidden="true" />}>
                          {t('parentOnboarding.homeVisits.today.accessNotes.steps', 'Steps to entrance')}
                        </Badge>
                      ) : null}
                      {stop.access_notes.multi_floor ? (
                        <Badge icon={<Building2 className="w-3 h-3" aria-hidden="true" />}>
                          {t('parentOnboarding.homeVisits.today.accessNotes.multiFloor', 'Multi-floor')}
                          {stop.access_notes.has_elevator
                            ? ' (' + t('parentOnboarding.homeVisits.today.accessNotes.elevator', 'Elevator') + ')'
                            : ''}
                        </Badge>
                      ) : null}
                      {stop.access_notes.dog_on_premises ? (
                        <Badge icon={<Dog className="w-3 h-3" aria-hidden="true" />}>
                          {t('parentOnboarding.homeVisits.today.accessNotes.dog', 'Dog on premises')}
                          {stop.access_notes.dog_safety_note ? `: ${stop.access_notes.dog_safety_note}` : ''}
                        </Badge>
                      ) : null}
                      {stop.access_notes.primary_language ? (
                        <Badge icon={<Languages className="w-3 h-3" aria-hidden="true" />}>
                          {t('parentOnboarding.homeVisits.today.accessNotes.primaryLanguage', {
                            language: stop.access_notes.primary_language,
                          })}
                          {stop.access_notes.needs_interpreter
                            ? ' (' +
                              t('parentOnboarding.homeVisits.today.accessNotes.interpreter', 'Needs interpreter') +
                              ')'
                            : ''}
                        </Badge>
                      ) : null}
                      {stop.access_notes.parking_notes ? (
                        <Badge icon={<ParkingCircle className="w-3 h-3" aria-hidden="true" />}>
                          {stop.access_notes.parking_notes}
                        </Badge>
                      ) : null}
                    </ul>
                  ) : null}
                </div>

                {/* Right column: reorder + edit */}
                <div className="flex flex-col gap-1 print:hidden">
                  <button
                    type="button"
                    onClick={() => handleMoveUp(idx)}
                    disabled={idx === 0 || sortMutation.isPending}
                    aria-label={t('parentOnboarding.homeVisits.today.moveUp', 'Move up')}
                    className="p-1 rounded hover:bg-lsc-rose/10 disabled:opacity-40"
                    data-testid={`sort-up-${idx + 1}`}
                  >
                    <ArrowUp className="w-4 h-4" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMoveDown(idx)}
                    disabled={idx >= stops.length - 1 || sortMutation.isPending}
                    aria-label={t('parentOnboarding.homeVisits.today.moveDown', 'Move down')}
                    className="p-1 rounded hover:bg-lsc-rose/10 disabled:opacity-40"
                    data-testid={`sort-down-${idx + 1}`}
                  >
                    <ArrowDown className="w-4 h-4" aria-hidden="true" />
                  </button>
                  {stop.manual_order ? (
                    <button
                      type="button"
                      onClick={() => handleResetSort(stop.visit_id)}
                      aria-label={t('parentOnboarding.homeVisits.today.resetOrder', 'Reset order')}
                      className="p-1 rounded hover:bg-lsc-rose/10"
                      title={t('parentOnboarding.homeVisits.today.resetOrder', 'Reset order')}
                    >
                      <RotateCcw className="w-4 h-4" aria-hidden="true" />
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => setEditingPatronId(stop.patron_id)}
                    aria-label={t('parentOnboarding.homeVisits.today.editNotes', 'Edit access notes')}
                    className="p-1 rounded hover:bg-lsc-rose/10"
                  >
                    <Pencil className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ol>

        {/* Warnings */}
        {warnings.length > 0 ? (
          <div
            role="status"
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60"
          >
            {t('parentOnboarding.homeVisits.today.warningsCount', {
              n: warnings.length,
            })}
          </div>
        ) : null}

        {/* Print footer (visible only when printing) */}
        <div className="hidden print:block text-xs text-lsc-dark/60 mt-6">
          {t('parentOnboarding.homeVisits.today.printedAt', {
            when: new Date().toLocaleString(),
          })}
        </div>
      </div>

      {/* Edit access-notes modal */}
      {editingStop ? (
        <EditAccessNotesModal
          patronId={editingStop.patron_id}
          existing={editingStop.access_notes ?? null}
          patronName={editingStop.patron_name ?? undefined}
          onClose={() => setEditingPatronId(null)}
          onSaved={() => {
            setEditingPatronId(null)
            refetch()
          }}
        />
      ) : null}
    </AdminShell>
  )
}

function Badge({ children, icon }: { children: React.ReactNode; icon: React.ReactNode }) {
  return (
    <li className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-lsc-cream/60 dark:bg-lsc-dark/40 text-lsc-dark dark:text-lsc-cream">
      {icon}
      {children}
    </li>
  )
}

// Static map: server-cached PNG from staticmap.openstreetmap.de. Built on
// the fly; if it 502s we fall back to a plain "Map unavailable" message
// and the address list is still the source of truth.
function StaticMapView({
  stops,
}: {
  stops: Array<DayPlanStop & { lat: number; lng: number }>
}) {
  const { t } = useTranslation()
  const [failed, setFailed] = useState(false)

  if (stops.length === 0 || failed) {
    return (
      <div className="bg-lsc-cream/40 dark:bg-lsc-dark/40 rounded-xl p-6 text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t(
          'parentOnboarding.homeVisits.today.mapUnavailable',
          'Map unavailable. See address list below.',
        )}
      </div>
    )
  }

  // Build the staticmap URL client-side. Markers are 1..N numbered pins
  // matching the visible card numbering. We've already returned above if
  // stops is empty, so [0] is safe -- but TS noUncheckedIndexedAccess
  // doesn't know that, so the bang here is intentional.
  const first = stops[0]!
  const center = `${first.lat},${first.lng}`
  const markers = stops
    .map((s, i) => `&markers=${encodeURIComponent(`${s.lat},${s.lng},lightblue${i + 1}`)}`)
    .join('')
  const url = `https://staticmap.openstreetmap.de/staticmap.php?center=${center}&zoom=12&size=800x320${markers}`

  return (
    <img
      src={url}
      alt={t('parentOnboarding.homeVisits.today.staticMapAlt', { n: stops.length })}
      className="w-full h-auto rounded-xl border border-lsc-dark/10 dark:border-lsc-cream/10"
      onError={() => setFailed(true)}
      loading="lazy"
    />
  )
}

// Inline edit-access-notes modal. Kept inline (not its own file) because
// it's only used here and adds modest LOC; if a second consumer ever
// appears, extract.
function EditAccessNotesModal({
  patronId,
  patronName,
  existing,
  onClose,
  onSaved,
}: {
  patronId: number
  patronName?: string
  existing: DayPlanStop['access_notes']
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<HomeVisitAccessNotesUpsert>({
    has_steps: existing?.has_steps ?? false,
    has_elevator: existing?.has_elevator ?? false,
    multi_floor: existing?.multi_floor ?? false,
    dog_on_premises: existing?.dog_on_premises ?? false,
    dog_safety_note: existing?.dog_safety_note ?? '',
    primary_language: existing?.primary_language ?? '',
    needs_interpreter: existing?.needs_interpreter ?? false,
    buzzer_or_intercom: existing?.buzzer_or_intercom ?? '',
    parking_notes: existing?.parking_notes ?? '',
    other_notes: existing?.other_notes ?? '',
  })
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      // Normalize empty strings to null so we don't pollute the DB with ''s.
      const normalized: HomeVisitAccessNotesUpsert = Object.fromEntries(
        Object.entries(draft).map(([k, v]) => [k, v === '' ? null : v]),
      )
      await setHomeVisitAccessNotes(patronId, normalized)
      toast.success(t('parentOnboarding.homeVisits.today.notesSaved', 'Notes saved'))
      onSaved()
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('parentOnboarding.homeVisits.today.notesSaveFailed', 'Could not save notes'))
    } finally {
      setSaving(false)
    }
  }

  // Close on Escape; keyboard-equivalent of the backdrop click. The backdrop
  // itself is intentionally not focusable -- it's a visual surface, not an
  // actionable element. Keyboard users get Escape + the Cancel button.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('parentOnboarding.homeVisits.today.editNotes', 'Edit access notes')}
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="document"
        className="bg-white dark:bg-lsc-dark rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold mb-1">
          {t('parentOnboarding.homeVisits.today.editNotes', 'Edit access notes')}
        </h2>
        {patronName ? (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{patronName}</p>
        ) : null}
        <p className="text-xs bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-700 dark:text-status-warning-300 px-3 py-2 rounded mb-4">
          {t(
            'parentOnboarding.homeVisits.today.notesPiiBanner',
            'These notes apply to all future visits to this family. Sensitive details — keep professional.',
          )}
        </p>

        <div className="space-y-3 text-sm">
          <Check
            label={t('parentOnboarding.homeVisits.today.accessNotes.steps', 'Steps to entrance')}
            checked={!!draft.has_steps}
            onChange={(v) => setDraft((d) => ({ ...d, has_steps: v }))}
          />
          <Check
            label={t('parentOnboarding.homeVisits.today.accessNotes.multiFloor', 'Multi-floor')}
            checked={!!draft.multi_floor}
            onChange={(v) => setDraft((d) => ({ ...d, multi_floor: v }))}
          />
          {draft.multi_floor ? (
            <Check
              label={t('parentOnboarding.homeVisits.today.accessNotes.elevator', 'Elevator')}
              checked={!!draft.has_elevator}
              onChange={(v) => setDraft((d) => ({ ...d, has_elevator: v }))}
            />
          ) : null}
          <Check
            label={t('parentOnboarding.homeVisits.today.accessNotes.dog', 'Dog on premises')}
            checked={!!draft.dog_on_premises}
            onChange={(v) => setDraft((d) => ({ ...d, dog_on_premises: v }))}
          />
          {draft.dog_on_premises ? (
            <Text
              label={t('parentOnboarding.homeVisits.today.dogSafetyLabel', 'Dog safety note')}
              value={String(draft.dog_safety_note ?? '')}
              onChange={(v) => setDraft((d) => ({ ...d, dog_safety_note: v }))}
            />
          ) : null}
          <Text
            label={t('parentOnboarding.homeVisits.today.primaryLanguageLabel', 'Primary language')}
            value={String(draft.primary_language ?? '')}
            onChange={(v) => setDraft((d) => ({ ...d, primary_language: v }))}
            placeholder="es-MX"
          />
          <Check
            label={t('parentOnboarding.homeVisits.today.accessNotes.interpreter', 'Needs interpreter')}
            checked={!!draft.needs_interpreter}
            onChange={(v) => setDraft((d) => ({ ...d, needs_interpreter: v }))}
          />
          <Text
            label={t('parentOnboarding.homeVisits.today.buzzerLabel', 'Buzzer / intercom')}
            value={String(draft.buzzer_or_intercom ?? '')}
            onChange={(v) => setDraft((d) => ({ ...d, buzzer_or_intercom: v }))}
          />
          <Text
            label={t('parentOnboarding.homeVisits.today.parkingLabel', 'Parking notes')}
            value={String(draft.parking_notes ?? '')}
            onChange={(v) => setDraft((d) => ({ ...d, parking_notes: v }))}
          />
          <Text
            label={t('parentOnboarding.homeVisits.today.otherLabel', 'Other notes')}
            value={String(draft.other_notes ?? '')}
            onChange={(v) => setDraft((d) => ({ ...d, other_notes: v }))}
          />
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm bg-lsc-cream/60 dark:bg-lsc-dark/40 text-lsc-dark dark:text-lsc-cream"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-sm bg-lsc-rose text-white disabled:opacity-60"
          >
            {saving
              ? t('common.saving', 'Saving...')
              : t('common.save', 'Save')}
          </button>
        </div>
      </div>
    </div>
  )
}

function Check({
  label, checked, onChange,
}: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4"
      />
      <span>{label}</span>
    </label>
  )
}

function Text({
  label, value, onChange, placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <label className="flex flex-col">
      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 px-2 py-1 rounded border border-lsc-dark/20 dark:border-lsc-cream/20 bg-white dark:bg-lsc-dark"
      />
    </label>
  )
}
