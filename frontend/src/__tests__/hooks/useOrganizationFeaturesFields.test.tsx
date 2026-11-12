/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useOrganizationFeaturesFields } from '@/hooks/useOrganizationFeaturesFields'
import api from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
  default: { patch: vi.fn() },
}))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

const refetch = vi.fn()
let mockFeatures: Record<string, unknown> | null = null

vi.mock('@/contexts/OrganizationFeaturesContext', () => ({
  useOrganizationFeatures: () => ({
    features: mockFeatures,
    loading: false,
    refetch,
  }),
}))

const mockedPatch = vi.mocked(api.patch)

describe('useOrganizationFeaturesFields', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedPatch.mockResolvedValue({ data: {} })
  })

  // Regression for 2026-05-21 mass-flip incident: a save with no user-touched
  // fields used to PATCH the whole form state (every flag), which combined
  // with caller defaults like {flag_key: false} would silently overwrite any
  // flag whose value never made it into form state from the server.
  it('does not PATCH untouched fields when value matches server state', async () => {
    mockFeatures = {
      gamification_enabled: true,
      learning_platform_enabled: true,
      events_enabled: true,
    }

    const { result } = renderHook(() =>
      useOrganizationFeaturesFields({
        gamification_enabled: false,
        learning_platform_enabled: false,
        events_enabled: false,
      }),
    )

    // Hook hydrates value from features on mount
    await waitFor(() => {
      expect(result.current.value.gamification_enabled).toBe(true)
    })

    await act(async () => {
      await result.current.save()
    })

    expect(mockedPatch).not.toHaveBeenCalled()
  })

  it('PATCHes only the fields the user changed', async () => {
    mockFeatures = {
      gamification_enabled: true,
      learning_platform_enabled: true,
      events_enabled: true,
    }

    const { result } = renderHook(() =>
      useOrganizationFeaturesFields({
        gamification_enabled: false,
        learning_platform_enabled: false,
        events_enabled: false,
      }),
    )

    await waitFor(() => {
      expect(result.current.value.gamification_enabled).toBe(true)
    })

    act(() => {
      result.current.setField('events_enabled', false)
    })

    await act(async () => {
      await result.current.save()
    })

    expect(mockedPatch).toHaveBeenCalledTimes(1)
    const [, payload] = mockedPatch.mock.calls[0] as [string, Record<string, unknown>]
    expect(payload).toEqual({ events_enabled: false })
    expect(payload).not.toHaveProperty('gamification_enabled')
    expect(payload).not.toHaveProperty('learning_platform_enabled')
  })

  // If the registry advertises a key the GET response doesn't return, the
  // form's value falls back to the caller's default (false). Pre-fix, save
  // would have PATCHed that false back to the server, creating/persisting
  // the column as false. Post-fix, the key isn't in serverState so it's
  // excluded from the payload.
  it('does not PATCH fields the server response omitted', async () => {
    mockFeatures = {
      gamification_enabled: true,
      // brand_new_feature_enabled intentionally omitted -- pretends GET
      // response is missing it
    }

    const { result } = renderHook(() =>
      useOrganizationFeaturesFields({
        gamification_enabled: false,
        brand_new_feature_enabled: false,
      }),
    )

    await waitFor(() => {
      expect(result.current.value.gamification_enabled).toBe(true)
    })

    // User touches the known field
    act(() => {
      result.current.setField('gamification_enabled', false)
    })

    await act(async () => {
      await result.current.save()
    })

    expect(mockedPatch).toHaveBeenCalledTimes(1)
    const [, payload] = mockedPatch.mock.calls[0] as [string, Record<string, unknown>]
    expect(payload).toEqual({ gamification_enabled: false })
    expect(payload).not.toHaveProperty('brand_new_feature_enabled')
  })

  // Regression: the features context re-polls every 30s, producing a new
  // `features` object each time. The hydration effect used to re-run on every
  // poll and wipe the user's unsaved toggles back to server state mid-edit.
  it('preserves unsaved edits when the features context re-polls', async () => {
    mockFeatures = { gamification_enabled: true, events_enabled: true }

    const { result, rerender } = renderHook(() =>
      useOrganizationFeaturesFields({
        gamification_enabled: false,
        events_enabled: false,
      }),
    )

    await waitFor(() => {
      expect(result.current.value.gamification_enabled).toBe(true)
    })

    act(() => {
      result.current.setField('events_enabled', false)
    })
    expect(result.current.value.events_enabled).toBe(false)

    // Simulate the 30s poll: same server data, new object identity
    mockFeatures = { gamification_enabled: true, events_enabled: true }
    rerender()

    // The unsaved edit must survive the poll
    expect(result.current.value.events_enabled).toBe(false)
  })

  it('refresh() discards local edits and rehydrates from server state', async () => {
    mockFeatures = { gamification_enabled: true, events_enabled: true }

    const { result, rerender } = renderHook(() =>
      useOrganizationFeaturesFields({
        gamification_enabled: false,
        events_enabled: false,
      }),
    )

    await waitFor(() => {
      expect(result.current.value.events_enabled).toBe(true)
    })

    act(() => {
      result.current.setField('events_enabled', false)
    })
    expect(result.current.value.events_enabled).toBe(false)

    await act(async () => {
      await result.current.refresh()
    })
    // The refetch triggered by refresh() lands as a new features object
    mockFeatures = { gamification_enabled: true, events_enabled: true }
    rerender()

    expect(refetch).toHaveBeenCalled()
    expect(result.current.value.events_enabled).toBe(true)
  })

  it('forwards a reason without PATCH-ing when nothing else changed', async () => {
    mockFeatures = { gamification_enabled: true }

    const { result } = renderHook(() =>
      useOrganizationFeaturesFields({ gamification_enabled: false }),
    )

    await waitFor(() => {
      expect(result.current.value.gamification_enabled).toBe(true)
    })

    await act(async () => {
      await result.current.save('audit context')
    })

    // No real changes -- reason alone shouldn't trigger an empty-body save.
    expect(mockedPatch).not.toHaveBeenCalled()
  })
})
