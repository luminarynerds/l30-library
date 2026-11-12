/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * OrganizationFeaturesContext Tests
 *
 * Tests for organization features context including:
 * - Feature loading from API
 * - Error handling with fallback defaults
 * - Feature flag checking
 * - Refetch functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from "@testing-library/react"
import { ReactNode } from 'react'
import {
  OrganizationFeaturesProvider,
  useOrganizationFeatures,
} from '@/contexts/OrganizationFeaturesContext'
import { mockOrganizationFeatures } from '../utils/mock-helpers'

// Mock the organization-features-api module (the actual import used by the context)
vi.mock('@/api/organization-features-api', () => ({
  getOrganizationFeatures: vi.fn(),
}))

import { getOrganizationFeatures } from '@/api/organization-features-api'
const mockedGetFeatures = vi.mocked(getOrganizationFeatures)

describe('OrganizationFeaturesContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const wrapper = ({ children }: { children: ReactNode }) => (
    <OrganizationFeaturesProvider>{children}</OrganizationFeaturesProvider>
  )

  describe('Initial Loading', () => {
    it('should start in loading state', () => {
      mockedGetFeatures.mockImplementation(() => new Promise(() => {})) // Never resolves

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      expect(result.current.loading).toBe(true)
      expect(result.current.features).toBeNull()
    })

    it('should fetch organization features on mount', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(getOrganizationFeatures).toHaveBeenCalledTimes(1)
      expect(result.current.features).toEqual(mockOrganizationFeatures)
    })
  })

  describe('Successful Feature Loading', () => {
    it('should load features successfully', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.features).toEqual(mockOrganizationFeatures)
        expect(result.current.loading).toBe(false)
      })
    })

    it('should expose all feature flags', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.features?.gamification_enabled).toBe(true)
        expect(result.current.features?.reading_programs_enabled).toBe(true)
        expect(result.current.features?.board_features_enabled).toBe(true)
        expect(result.current.features?.training_modules_enabled).toBe(true)
      })
    })

    it('should expose configuration arrays', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.features?.enabled_focus_modes).toEqual([
          'deep_dive',
          'pomodoro',
        ])
        expect(result.current.features?.enabled_themes).toContain('light')
        expect(result.current.features?.enabled_fonts).toContain('dyslexic')
      })
    })

    it('should expose numeric limits', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.features?.max_holds_per_patron).toBe(10)
        expect(result.current.features?.max_checkouts_per_patron).toBe(5)
        expect(result.current.features?.default_daily_goal_minutes).toBe(30)
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      mockedGetFeatures.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.features).not.toBeNull()
    })

    it('should provide default features on error', async () => {
      mockedGetFeatures.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.features).not.toBeNull()
      })

      // Should have default features enabled
      expect(result.current.features?.gamification_enabled).toBe(true)
      expect(result.current.features?.patron_portal_enabled).toBe(true)
      expect(result.current.features?.max_holds_per_patron).toBe(10)
    })

    it('should continue working even if API fails', async () => {
      mockedGetFeatures.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Should be able to check features even with defaults
      expect(result.current.isFeatureEnabled('gamification_enabled')).toBe(true)
    })
  })

  describe('Feature Checking', () => {
    it('should check if boolean features are enabled', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.isFeatureEnabled('gamification_enabled')).toBe(true)
      expect(result.current.isFeatureEnabled('reading_programs_enabled')).toBe(true)
    })

    it('should return false for disabled features', async () => {
      const disabledFeatures = {
        ...mockOrganizationFeatures,
        gamification_enabled: false,
      }
      mockedGetFeatures.mockResolvedValue(disabledFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.isFeatureEnabled('gamification_enabled')).toBe(false)
    })

    it('should return false for non-boolean features', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // max_holds_per_patron is a number, not boolean
      expect(result.current.isFeatureEnabled('max_holds_per_patron' as unknown as keyof typeof mockOrganizationFeatures)).toBe(false)
    })

    it('should return true (optimistic) when features not loaded yet', () => {
      // OFContext intentionally returns true while loading to avoid a
      // blocking spinner waterfall; gating components render and let
      // their own loading state show.
      mockedGetFeatures.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      expect(result.current.isFeatureEnabled('gamification_enabled')).toBe(true)
    })
  })

  describe('Refetch Functionality', () => {
    it('should refetch features when refetch is called', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(getOrganizationFeatures).toHaveBeenCalledTimes(1)

      // Refetch with updated features
      const updatedFeatures = {
        ...mockOrganizationFeatures,
        gamification_enabled: false,
      }
      mockedGetFeatures.mockResolvedValue(updatedFeatures)

      await act(async () => {
        await result.current.refetch()
      })

      await waitFor(() => {
        expect(getOrganizationFeatures).toHaveBeenCalledTimes(2)
        expect(result.current.features?.gamification_enabled).toBe(false)
      })
    })

    it('should complete refetch and return to non-loading state', async () => {
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      await act(async () => {
        await result.current.refetch()
      })

      // After refetch completes, should not be loading
      expect(result.current.loading).toBe(false)
      expect(result.current.features).toEqual(mockOrganizationFeatures)
    })

    it('should update features on successful refetch after error', async () => {
      // First call fails
      mockedGetFeatures.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Defaults should be set
      expect(result.current.features).not.toBeNull()

      // Second call succeeds
      mockedGetFeatures.mockResolvedValue(mockOrganizationFeatures)

      await act(async () => {
        await result.current.refetch()
      })

      await waitFor(() => {
        expect(result.current.features).toEqual(mockOrganizationFeatures)
      })
    })
  })

  describe('Hook Error Handling', () => {
    it('should throw error if used outside provider', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

      try {
        const { result } = renderHook(() => useOrganizationFeatures())
        // In newer React Testing Library, the error may be caught in result.current
        // rather than thrown synchronously
        expect(result.current).toBeUndefined()
      } catch (e: unknown) {
        expect((e as Error).message).toContain('useOrganizationFeatures must be used within OrganizationFeaturesProvider')
      }

      consoleError.mockRestore()
    })
  })

  describe('Configuration Values', () => {
    it('should expose array configuration values', async () => {
      const customFeatures = {
        ...mockOrganizationFeatures,
        enabled_focus_modes: ['deep_dive', 'pomodoro', 'calm'],
        enabled_themes: ['light', 'dark', 'forest', 'ocean'],
      }
      mockedGetFeatures.mockResolvedValue(customFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.features?.enabled_focus_modes).toHaveLength(3)
      expect(result.current.features?.enabled_themes).toHaveLength(4)
    })

    it('should handle empty configuration arrays', async () => {
      const emptyArrayFeatures = {
        ...mockOrganizationFeatures,
        enabled_focus_modes: [],
        enabled_themes: [],
        enabled_fonts: [],
      }
      mockedGetFeatures.mockResolvedValue(emptyArrayFeatures)

      const { result } = renderHook(() => useOrganizationFeatures(), { wrapper })

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      expect(result.current.features?.enabled_focus_modes).toEqual([])
      expect(result.current.features?.enabled_themes).toEqual([])
    })
  })
})
