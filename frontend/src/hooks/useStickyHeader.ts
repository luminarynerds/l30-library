/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useStickyHeader Hook
 *
 * Implements smart sticky header behavior:
 * - Header stays visible when scrolling up
 * - Header hides when scrolling down (after threshold)
 * - Header is always visible at top of page
 */

import { useState, useEffect, useRef, useCallback } from 'react'

interface StickyHeaderState {
  isSticky: boolean
  isVisible: boolean
  isAtTop: boolean
}

export function useStickyHeader(threshold: number = 100): StickyHeaderState {
  const [state, setState] = useState<StickyHeaderState>({
    isSticky: false,
    isVisible: true,
    isAtTop: true
  })

  const lastScrollY = useRef(0)
  const ticking = useRef(false)

  const updateState = useCallback(() => {
    const scrollY = window.scrollY
    const isAtTop = scrollY < threshold
    const isScrollingDown = scrollY > lastScrollY.current
    const scrollDelta = Math.abs(scrollY - lastScrollY.current)

    // Only update if scroll delta is significant (prevents jitter)
    if (scrollDelta < 5 && !isAtTop) {
      ticking.current = false
      return
    }

    setState({
      isSticky: scrollY > 0,
      isVisible: isAtTop || !isScrollingDown,
      isAtTop
    })

    lastScrollY.current = scrollY
    ticking.current = false
  }, [threshold])

  useEffect(() => {
    const handleScroll = () => {
      if (!ticking.current) {
        window.requestAnimationFrame(updateState)
        ticking.current = true
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [updateState])

  return state
}

export default useStickyHeader
