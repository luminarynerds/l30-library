/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useFocusAndAnnounce - shared focus-on-view-change primitive
 *
 * On drill-in / drill-out navigation (e.g. list -> detail, detail -> back) a
 * sighted user sees the view swap, but a screen-reader / keyboard user is left
 * with focus on a stale or detached node and no notification that anything
 * changed. This hook does both jobs in one place:
 *
 *   1. Moves keyboard focus to the new view's heading on mount.
 *   2. Announces the change via the existing polite live region
 *      (`announceToScreenReader` from useUnifiedAccessibility).
 *
 * It deliberately reuses the app's single shared announcer rather than mounting
 * a second live region, and it focuses the heading you already render rather
 * than trapping focus (use useFocusTrap for modals/dialogs instead).
 *
 * The heading element should be focusable: give it `tabIndex={-1}` and an
 * `outline-none` class so the programmatic focus does not draw a focus ring.
 *
 * @example
 * ```tsx
 * const headingRef = useRef<HTMLHeadingElement>(null)
 * useFocusAndAnnounce(headingRef, `Opened article: ${article.title}`)
 * // ...
 * <h2 ref={headingRef} tabIndex={-1} className="outline-none">{article.title}</h2>
 * ```
 */
import { useEffect, type RefObject } from 'react'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'

export function useFocusAndAnnounce(
  ref: RefObject<HTMLElement | null>,
  message: string,
  /** Re-run when this value changes (e.g. the selected article id). */
  deps: unknown = undefined,
  /**
   * When false, neither focus nor announcement fires. Use this to suppress the
   * initial-mount focus-steal on drill-OUT targets (e.g. a list heading should
   * only grab focus once the user has actually returned from a detail view).
   */
  enabled: boolean = true,
): void {
  const { announceToScreenReader } = useUnifiedAccessibility()

  useEffect(() => {
    if (!enabled) return
    if (message) {
      announceToScreenReader(message)
    }
    // Defer focus so the heading is in the DOM and any transition has settled.
    const id = window.setTimeout(() => {
      ref.current?.focus()
    }, 0)
    return () => window.clearTimeout(id)
    // announceToScreenReader is stable (useCallback); message + deps drive re-runs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deps, enabled])
}

export default useFocusAndAnnounce
