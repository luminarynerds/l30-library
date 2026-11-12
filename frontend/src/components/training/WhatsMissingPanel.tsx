/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * "What's missing" roll-up panel. Previously a persistent column; now opened
 * from the header badge. Per-item dismiss persists in localStorage keyed by
 * courseId; scoped aria-live announces count delta only; amber tone, no
 * celebration animation at count=0.
 *
 * A11y: each "Skip" button has a descriptive aria-label that names its target
 * so a screen-reader list isn't N identical "Skip for now"s.
 */
import { useEffect, useMemo, useState } from 'react'
import {
  collectAllIssues,
  getDismissedIssueKeys,
  type AuthoringCourse,
  type AuthoringModule,
  type IssueScope,
} from '@/lib/authoring-checks'

interface Props {
  courseId: number | string
  course: AuthoringCourse
  modules: AuthoringModule[]
  onNavigate?: (scope: IssueScope) => void
}

type DismissedMap = Record<string, true>

function storageKey(courseId: Props['courseId']) {
  return `lsc_authoring_dismissed_${courseId}`
}

function loadDismissed(courseId: Props['courseId']): DismissedMap {
  const keys = getDismissedIssueKeys(courseId)
  const map: DismissedMap = {}
  keys.forEach((k) => { map[k] = true })
  return map
}

function saveDismissed(courseId: Props['courseId'], map: DismissedMap) {
  try {
    localStorage.setItem(storageKey(courseId), JSON.stringify(map))
  } catch {
    /* localStorage full / unavailable - skip persistence */
  }
}

export default function WhatsMissingPanel({ courseId, course, modules, onNavigate }: Props) {
  const [dismissed, setDismissed] = useState<DismissedMap>(() => loadDismissed(courseId))
  const [showHidden, setShowHidden] = useState(false)
  const [announce, setAnnounce] = useState('')
  const [prevCount, setPrevCount] = useState(0)

  const allIssues = useMemo(() => collectAllIssues(course, modules), [course, modules])

  const visibleIssues = useMemo(
    () => allIssues.filter(i => !dismissed[i.code]),
    [allIssues, dismissed],
  )
  const hiddenCount = allIssues.length - visibleIssues.length
  const count = visibleIssues.length

  // Announce count delta only (not full list) for screen readers.
  useEffect(() => {
    if (count !== prevCount) {
      if (count === 0) setAnnounce('Ready to publish.')
      else if (count > prevCount) setAnnounce(`${count - prevCount} new item${count - prevCount === 1 ? '' : 's'} to finish.`)
      else setAnnounce(`${count} item${count === 1 ? '' : 's'} to finish.`)
      setPrevCount(count)
    }
  }, [count, prevCount])

  const handleSkip = (code: string) => {
    const next = { ...dismissed, [code]: true as const }
    setDismissed(next)
    saveDismissed(courseId, next)
  }

  return (
    <section role="region" aria-labelledby="whats-missing-heading" className="w-full">
      <h3
        id="whats-missing-heading"
        className="text-sm font-semibold text-status-warning-800 dark:text-status-warning-200"
      >
        {count === 0 ? 'Ready to publish' : `${count} thing${count === 1 ? '' : 's'} to finish`}
      </h3>

      <div aria-live="polite" aria-atomic="false" className="sr-only">{announce}</div>

      {count > 0 && (
        <ul className="mt-2 space-y-2">
          {visibleIssues.map((issue) => (
            <li key={issue.code} className="text-sm flex items-start gap-2">
              {onNavigate && issue.scope.kind === 'lesson' && issue.scope.lessonId !== undefined ? (
                <button
                  type="button"
                  onClick={() => onNavigate(issue.scope)}
                  className="flex-1 text-left text-status-warning-900 dark:text-status-warning-100 underline-offset-2 hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                  aria-label={`Go to: ${issue.message}`}
                >
                  {issue.message}
                </button>
              ) : (
                <span className="flex-1 text-status-warning-900 dark:text-status-warning-100">
                  {issue.message}
                </span>
              )}
              <button
                type="button"
                onClick={() => handleSkip(issue.code)}
                aria-label={`Dismiss: ${issue.message}`}
                className="text-xs underline text-status-warning-700 dark:text-status-warning-300 focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded shrink-0"
              >
                Skip for now
              </button>
            </li>
          ))}
        </ul>
      )}

      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setShowHidden(s => !s)}
          className="mt-3 text-xs text-status-warning-700 dark:text-status-warning-300 underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
        >
          {showHidden ? `${hiddenCount} hidden — hide` : `${hiddenCount} hidden — show`}
        </button>
      )}

      {showHidden && hiddenCount > 0 && (
        <ul className="mt-2 space-y-1">
          {allIssues.filter(i => dismissed[i.code]).map((issue) => (
            <li key={issue.code} className="text-xs text-status-warning-700 dark:text-status-warning-300">
              {issue.message}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
