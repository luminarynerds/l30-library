/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useScrollLock } from '../useScrollLock'

// Module-level state (lockCount, overflowSnapshot) is shared across tests
// in the same file. We drain locks via unmounts and reset body.style.overflow
// in beforeEach so each test starts from a clean slate.

describe('useScrollLock', () => {
  beforeEach(() => {
    document.body.style.overflow = ''
  })

  it('sets body.overflow to hidden on first mount', () => {
    const { unmount } = renderHook(() => useScrollLock(true))
    expect(document.body.style.overflow).toBe('hidden')
    unmount()
    expect(document.body.style.overflow).toBe('')
  })

  it('second mount while first still mounted does not change overflow', () => {
    const first = renderHook(() => useScrollLock(true))
    expect(document.body.style.overflow).toBe('hidden')

    const second = renderHook(() => useScrollLock(true))
    expect(document.body.style.overflow).toBe('hidden')

    first.unmount()
    // lock count is still 1 — stays hidden
    expect(document.body.style.overflow).toBe('hidden')

    second.unmount()
    // lock count is 0 — restores
    expect(document.body.style.overflow).toBe('')
  })

  it('first unmount keeps overflow hidden when second is still mounted', () => {
    const first = renderHook(() => useScrollLock(true))
    const second = renderHook(() => useScrollLock(true))

    first.unmount()
    expect(document.body.style.overflow).toBe('hidden')

    second.unmount()
    expect(document.body.style.overflow).toBe('')
  })

  it('second unmount restores to the original value, not empty string', () => {
    document.body.style.overflow = 'auto'

    const first = renderHook(() => useScrollLock(true))
    const second = renderHook(() => useScrollLock(true))

    first.unmount()
    second.unmount()

    expect(document.body.style.overflow).toBe('auto')
  })

  it('active: false is inert — overflow unchanged throughout lifecycle', () => {
    const { unmount } = renderHook(() => useScrollLock(false))
    expect(document.body.style.overflow).toBe('')
    unmount()
    expect(document.body.style.overflow).toBe('')
  })

  it('toggling active from false to true acquires the lock', () => {
    const { rerender, unmount } = renderHook(({ active }) => useScrollLock(active), {
      initialProps: { active: false },
    })
    expect(document.body.style.overflow).toBe('')

    act(() => {
      rerender({ active: true })
    })
    expect(document.body.style.overflow).toBe('hidden')

    unmount()
    expect(document.body.style.overflow).toBe('')
  })
})
