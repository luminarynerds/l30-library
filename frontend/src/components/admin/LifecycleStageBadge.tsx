/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * LifecycleStageBadge — status indicator only (non-interactive).
 * CourseStatusActions — "Change status" button + action menu with plain verbs.
 *
 * Design rationale: the old pill WAS the dropdown (one element, two jobs).
 * Now the pill is a pure status indicator; actions live in a separate control.
 * Per-verb consequence text appears inline before the user commits.
 */
import * as Sentry from '@/lib/sentry-lazy'
import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { Circle, CheckCircle2, Archive, ChevronDown } from 'lucide-react'
import {
  transitionCourseStage,
  CourseStageTransitionError,
  type CourseLifecycleStage,
  type CourseListItemAdmin,
} from '@/api/domains/learning/courses-api'

// Client-side mirror of backend ALLOWED_TRANSITIONS
// (services/course_lifecycle_service.py). Backend is authoritative (it 400s
// with allowed_targets if this drifts), so a stale entry degrades to a
// rejected toast, never a silent wrong write.
const ALLOWED_TRANSITIONS: Record<CourseLifecycleStage, CourseLifecycleStage[]> = {
  draft: ['published', 'archived'],
  published: ['draft', 'archived'],
  archived: ['draft'],
}

type TFn = (key: string, paramsOrFallback?: Record<string, unknown> | string) => string

// Pill: non-interactive status indicator. Icon + text + color together (never color alone).
const PILL_CLASSES: Record<CourseLifecycleStage, string> = {
  draft:
    'border border-earth-300 text-earth-700 dark:border-earth-600 dark:text-earth-200',
  published:
    'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  archived:
    'border border-earth-300 text-earth-500/80 dark:border-earth-700 dark:text-earth-400/80',
}

function StageGlyph({ stage }: { stage: CourseLifecycleStage }) {
  const cls = 'w-3 h-3 shrink-0'
  switch (stage) {
    case 'draft':
      return <Circle className={cls} aria-hidden="true" />
    case 'published':
      return <CheckCircle2 className={cls} aria-hidden="true" />
    case 'archived':
      return <Archive className={cls} aria-hidden="true" />
  }
}

// Plain label for each stage.
function stageLabel(stage: CourseLifecycleStage, t: TFn): string {
  return t(`admin.adminCourses.stage_${stage}`)
}

// Human-readable consequence of taking an action. Depends on the source
// stage: archived->draft is "Restore", published->draft is "Unpublish".
function consequenceText(
  source: CourseLifecycleStage,
  target: CourseLifecycleStage,
  enrollmentCount: number,
  t: TFn,
): string {
  switch (target) {
    case 'published':
      return t('admin.adminCourses.actionConsequencePublish')
    case 'draft':
      return source === 'archived'
        ? t('admin.adminCourses.actionConsequenceRestore')
        : t('admin.adminCourses.actionConsequenceUnpublish', { count: enrollmentCount })
    case 'archived':
      return t('admin.adminCourses.actionConsequenceArchive', { count: enrollmentCount })
  }
}

// Plain verb label. archived->draft is "Restore", published->draft is "Unpublish".
function verbLabel(
  source: CourseLifecycleStage,
  target: CourseLifecycleStage,
  t: TFn,
): string {
  switch (target) {
    case 'published':
      return t('admin.adminCourses.actionPublish')
    case 'draft':
      return source === 'archived'
        ? t('admin.adminCourses.actionRestore')
        : t('admin.adminCourses.actionUnpublish')
    case 'archived':
      return t('admin.adminCourses.actionArchive')
  }
}

// -------------------------------------------------------------------------
// LifecycleStageBadge — pure status indicator, no interactivity
// -------------------------------------------------------------------------

export interface LifecycleStageBadgeProps {
  stage: CourseLifecycleStage
  t: TFn
}

export function LifecycleStageBadge({ stage, t }: LifecycleStageBadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
        ${PILL_CLASSES[stage]}
      `}
      title={t(`admin.adminCourses.stageTooltip_${stage}`)}
    >
      <StageGlyph stage={stage} />
      {stageLabel(stage, t)}
    </span>
  )
}

// -------------------------------------------------------------------------
// CourseStatusActions — "Change status" button + action dropdown
// -------------------------------------------------------------------------

export interface CourseStatusActionsProps {
  course: CourseListItemAdmin
  t: TFn
  onTransitioned: (updated: CourseListItemAdmin) => void
}

export function CourseStatusActions({
  course,
  t,
  onTransitioned,
}: CourseStatusActionsProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  // When archive requires confirm (enrolled learners), hold pending target
  // and render inline two-step confirm inside the menu.
  const [confirmArchive, setConfirmArchive] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  const stage = course.lifecycle_stage
  const targets = ALLOWED_TRANSITIONS[stage] ?? []

  const close = useCallback(() => {
    setOpen(false)
    setConfirmArchive(false)
  }, [])

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) close()
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [open, close])

  // Focus first menu item when menu opens.
  useEffect(() => {
    if (!open || confirmArchive) return
    const first = menuRef.current?.querySelector<HTMLElement>(
      '[role="menuitem"]:not([disabled])',
    )
    first?.focus()
  }, [open, confirmArchive])

  const doTransition = useCallback(
    async (to: CourseLifecycleStage, confirm?: boolean) => {
      setBusy(true)
      try {
        const updated = await transitionCourseStage(course.id, {
          to_stage: to,
          ...(confirm ? { confirm: true } : {}),
        })
        onTransitioned(updated)
        toast.success(
          t('toast.adminCourses.stageChanged', {
            stage: stageLabel(to, t),
          }),
        )
        close()
      } catch (err: unknown) {
        if (err instanceof CourseStageTransitionError) {
          if (to === 'archived' && err.requiresConfirm && !confirm) {
            setConfirmArchive(true)
            setBusy(false)
            return
          }
          if (to === 'published' && /no lessons|empty course/i.test(err.message)) {
            toast.error(t('toast.adminCourses.stageCannotPublishEmpty'))
            close()
            return
          }
          if (err.allowedTargets && err.allowedTargets.length > 0) {
            const names = err.allowedTargets
              .map((s) => stageLabel(s, t))
              .join(', ')
            toast.error(
              t('toast.adminCourses.stageRejectedAllowed', { stages: names }),
            )
            close()
            return
          }
          toast.error(err.message || t('toast.adminCourses.stageChangeFailed'))
          close()
          return
        }
        Sentry.captureException(
          err instanceof Error ? err : new Error(String(err)),
        )
        toast.error(t('toast.adminCourses.stageChangeFailed'))
        close()
      } finally {
        setBusy(false)
      }
    },
    [course.id, onTransitioned, t, close],
  )

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return
    const items = menuRef.current?.querySelectorAll<HTMLElement>(
      '[role="menuitem"]:not([disabled])',
    )
    if (e.key === 'Escape') {
      e.preventDefault()
      close()
      buttonRef.current?.focus()
      return
    }
    if (!items?.length) return
    const idx = Array.from(items).indexOf(document.activeElement as HTMLElement)
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      items[(idx + 1) % items.length]!.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      items[(idx - 1 + items.length) % items.length]!.focus()
    } else if (e.key === 'Home') {
      e.preventDefault()
      items[0]!.focus()
    } else if (e.key === 'End') {
      e.preventDefault()
      items[items.length - 1]!.focus()
    }
  }

  if (targets.length === 0) return null

  return (
    <div
      className="relative inline-block"
      ref={wrapRef}
      onKeyDown={handleMenuKeyDown}
    >
      <button
        ref={buttonRef}
        type="button"
        onClick={() => (open ? close() : setOpen(true))}
        disabled={busy}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('aria.adminCourses.changeStage', {
          title: course.title,
          stage: stageLabel(stage, t),
        })}
        className="
          inline-flex items-center gap-1.5 px-3 py-2 rounded-lg
          min-h-[44px]
          text-sm font-medium
          border border-lsc-border dark:border-earth-700
          text-lsc-dark dark:text-lsc-cream
          hover:bg-lsc-cream/50 dark:hover:bg-earth-700
          motion-safe:transition-colors
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2
          dark:focus-visible:ring-offset-earth-800
          disabled:opacity-50 disabled:cursor-not-allowed
        "
      >
        {t('admin.adminCourses.changeStatusButton')}
        <ChevronDown
          className={`w-3.5 h-3.5 motion-safe:transition-transform ${open ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={t('aria.adminCourses.stageMenu', {
            title: course.title,
          })}
          className="
            absolute right-0 top-full mt-1 w-80 z-50 whitespace-normal
            bg-lsc-white dark:bg-earth-800
            rounded-xl shadow-lg border border-lsc-border dark:border-earth-700
            py-1
            motion-safe:transition-opacity
          "
        >
          {confirmArchive ? (
            <div className="px-4 py-3 space-y-3">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                {t('admin.adminCourses.actionArchive')}
              </p>
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                {t('admin.adminCourses.archiveConfirmBody', {
                  count: course.enrollment_count,
                })}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => doTransition('archived', true)}
                  disabled={busy}
                  className="
                    flex-1 px-3 py-2 rounded-lg text-sm font-medium
                    bg-status-danger-600 text-white hover:bg-status-danger-700
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-danger-500
                  "
                >
                  {t('admin.adminCourses.archiveConfirmButton')}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmArchive(false)}
                  disabled={busy}
                  className="
                    flex-1 px-3 py-2 rounded-lg text-sm font-medium
                    border border-lsc-border dark:border-earth-700
                    text-lsc-dark dark:text-lsc-cream
                    hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose
                  "
                >
                  {t('admin.adminCourses.archiveConfirmCancel')}
                </button>
              </div>
            </div>
          ) : (
            <>
              <p
                className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-lsc-dark/60 dark:text-lsc-cream/60"
                aria-hidden="true"
              >
                {t('admin.adminCourses.stageMenuHeading')}
              </p>
              {targets.map((target) => (
                <button
                  key={target}
                  type="button"
                  role="menuitem"
                  tabIndex={-1}
                  disabled={busy}
                  onClick={() => doTransition(target)}
                  className="
                    block w-full text-left px-4 py-3
                    hover:bg-lsc-cream dark:hover:bg-earth-700
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus-visible:outline-none focus-visible:bg-lsc-rose/10
                    border-b border-lsc-border/50 dark:border-earth-700/50 last:border-b-0
                  "
                >
                  <span className="flex items-center gap-2">
                    <StageGlyph stage={target} />
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                      {verbLabel(stage, target, t)}
                    </span>
                  </span>
                  <span className="block mt-0.5 pl-5 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                    {consequenceText(stage, target, course.enrollment_count, t)}
                  </span>
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}

// -------------------------------------------------------------------------
// Legacy combined export — wraps both components for callers that
// previously used LifecycleStageBadge as both status + action in one.
// AdminCoursesPage has been updated to use the split components directly,
// but external callers can use this wrapper during the transition.
// -------------------------------------------------------------------------

export interface LifecycleStageBadgeWithActionsProps {
  course: CourseListItemAdmin
  t: TFn
  onTransitioned: (updated: CourseListItemAdmin) => void
}

export function LifecycleStageBadgeWithActions({
  course,
  t,
  onTransitioned,
}: LifecycleStageBadgeWithActionsProps) {
  return (
    <div className="flex items-center gap-2">
      <LifecycleStageBadge stage={course.lifecycle_stage} t={t} />
      <CourseStatusActions course={course} t={t} onTransitioned={onTransitioned} />
    </div>
  )
}
