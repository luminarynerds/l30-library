/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import { useAutoSave } from '@/hooks/useAutoSave'

// Tests the REAL hook (src/hooks/useAutoSave.tsx). A previous version of this
// file tested an inlined copy that had drifted from the implementation, so it
// covered nothing real and rotted (15 failing). These exercise the shipped hook,
// including the "don't save just for loading a record" baseline behaviour.

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('starts idle and does not save on mount', () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useAutoSave({ data: 'a', onSave }))
    expect(result.current.status).toBe('idle')
    expect(result.current.lastSaved).toBeNull()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('saves after the debounce delay when data changes', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 2000 }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    expect(onSave).not.toHaveBeenCalled()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(onSave).toHaveBeenCalledExactlyOnceWith('updated')
  })

  it('debounces rapid changes into a single save with the latest value', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 2000 }),
      { initialProps: { data: 'v1' } },
    )
    rerender({ data: 'v2' })
    await act(async () => { await vi.advanceTimersByTimeAsync(500) })
    rerender({ data: 'v3' })
    await act(async () => { await vi.advanceTimersByTimeAsync(500) })
    rerender({ data: 'v4' })
    expect(onSave).not.toHaveBeenCalled()
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(onSave).toHaveBeenCalledExactlyOnceWith('v4')
  })

  it('honours a custom delay', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 5000 }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    await act(async () => { await vi.advanceTimersByTimeAsync(4999) })
    expect(onSave).not.toHaveBeenCalled()
    await act(async () => { await vi.advanceTimersByTimeAsync(1) })
    expect(onSave).toHaveBeenCalledOnce()
  })

  it('forceSave saves immediately and cancels the pending debounce', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 2000 }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    await act(async () => { await result.current.forceSave() })
    expect(onSave).toHaveBeenCalledExactlyOnceWith('updated')
    // The previously-scheduled debounce must not fire a second save.
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(onSave).toHaveBeenCalledOnce()
  })

  it('does not save while disabled', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 1000, enabled: false }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(onSave).not.toHaveBeenCalled()
  })

  it('does not save just because it became enabled (record finished loading)', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    const { rerender } = renderHook(
      ({ data, enabled }) => useAutoSave({ data, onSave, delay: 2000, enabled }),
      { initialProps: { data: 'empty', enabled: false } },
    )
    // Load completes: autosave turns on and data becomes the loaded record.
    rerender({ data: 'loaded record', enabled: true })
    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    expect(onSave).not.toHaveBeenCalled()
    // A genuine edit after load still autosaves.
    rerender({ data: 'edited record', enabled: true })
    await act(async () => { await vi.advanceTimersByTimeAsync(2500) })
    expect(onSave).toHaveBeenCalledExactlyOnceWith('edited record')
  })

  it('transitions status idle -> saving -> saved', async () => {
    let resolveSave: () => void = () => {}
    const onSave = vi.fn().mockImplementation(() => new Promise<void>((r) => { resolveSave = r }))
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 1000 }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(result.current.status).toBe('saving')
    await act(async () => { resolveSave(); await Promise.resolve() })
    expect(result.current.status).toBe('saved')
    expect(result.current.lastSaved).toBeInstanceOf(Date)
  })

  it('sets status error when onSave rejects', async () => {
    const err = new Error('save failed')
    const onSave = vi.fn().mockRejectedValue(err)
    const { result, rerender } = renderHook(
      ({ data }) => useAutoSave({ data, onSave, delay: 1000 }),
      { initialProps: { data: 'initial' } },
    )
    rerender({ data: 'updated' })
    await act(async () => { await vi.advanceTimersByTimeAsync(1000) })
    expect(result.current.status).toBe('error')
    expect(result.current.error).toBe(err)
  })
})
