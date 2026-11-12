/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Onboarding Configuration Service Tests
 *
 * Tests for getFollowUpPeriods() function
 * Covers success cases, error handling, and data validation
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getFollowUpPeriods } from '../onboarding-config';
import * as fetchApiModule from '@/api/fetchApi';
import * as Sentry from '@/lib/sentry-lazy';

vi.mock('@/api/fetchApi');
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}));

describe('Onboarding Configuration Service', () => {
  const mockFetchApi = vi.mocked(fetchApiModule.fetchApi);
  const mockedCapture = vi.mocked(Sentry.captureException);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getFollowUpPeriods()', () => {
    it('should fetch and return follow-up periods successfully', async () => {
      const mockPeriods = [
        { key: 'one_week', label: '1 Week', days_offset: 7 },
        { key: 'two_weeks', label: '2 Weeks', days_offset: 14 },
        { key: 'one_month', label: '1 Month', days_offset: 30 },
        { key: 'thirty_days', label: '30 Days', days_offset: 30 },
      ];

      mockFetchApi.mockResolvedValue(mockPeriods);

      const result = await getFollowUpPeriods();

      expect(result).toEqual(mockPeriods);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/onboarding/config/follow-up-periods',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toHaveLength(4);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });

    it('should handle network errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new TypeError('Network error'));

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-789';
      mockFetchApi.mockResolvedValue([]);

      await getFollowUpPeriods(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockPeriods = [
        { key: 'one_week', label: '1 Week', days_offset: 7 },
      ];

      mockFetchApi.mockResolvedValue(mockPeriods);

      const result = await getFollowUpPeriods();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(result[0]).toHaveProperty('days_offset');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
      expect(typeof result[0]!.days_offset).toBe('number');
    });

    it('should validate days_offset is positive integer', async () => {
      const mockPeriods = [
        { key: 'one_week', label: '1 Week', days_offset: 7 },
        { key: 'two_weeks', label: '2 Weeks', days_offset: 14 },
      ];

      mockFetchApi.mockResolvedValue(mockPeriods);

      const result = await getFollowUpPeriods();

      result.forEach(period => {
        expect(period.days_offset).toBeGreaterThan(0);
        expect(Number.isInteger(period.days_offset)).toBe(true);
      });
    });

    it('should handle undefined response gracefully', async () => {
      mockFetchApi.mockResolvedValue(undefined);

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });

    it('should handle timeout errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Request timeout'));

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });

    it('should handle malformed response gracefully', async () => {
      mockFetchApi.mockResolvedValue('invalid data');

      const result = await getFollowUpPeriods();

      // Should still return the response as-is, error handling in component
      expect(result).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should report errors to Sentry', async () => {
      mockFetchApi.mockRejectedValue(new Error('Test error'));

      await getFollowUpPeriods();

      expect(mockedCapture).toHaveBeenCalled();
    });

    it('should handle permission errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Unauthorized'));

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });

    it('should handle server errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Internal server error'));

      const result = await getFollowUpPeriods();

      expect(result).toEqual([]);
    });
  });
});
