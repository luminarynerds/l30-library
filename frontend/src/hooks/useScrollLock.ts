/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'

// Module-level ref-count + snapshot so multiple concurrent callers share one lock.
let lockCount = 0
let overflowSnapshot = ''

export function useScrollLock(active: boolean = true): void {
  useEffect(() => {
    if (!active) return

    if (lockCount === 0) {
      overflowSnapshot = document.body.style.overflow
      document.body.style.overflow = 'hidden'
    }
    lockCount++

    return () => {
      lockCount--
      if (lockCount === 0) {
        document.body.style.overflow = overflowSnapshot
        overflowSnapshot = ''
      }
    }
  }, [active])
}

export default useScrollLock
