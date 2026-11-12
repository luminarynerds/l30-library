/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Training Configuration Service Tests
 *
 * Tests for getRatingScales() and getLessonTypes() functions
 * Covers success cases, error handling, and data validation
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getRatingScales, getLessonTypes } from '../training-config';
import * as fetchApiModule from '@/api/fetchApi';
import * as Sentry from '@/lib/sentry-lazy';

// Mock the fetchApi module
vi.mock('@/api/fetchApi');
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}));

describe('Training Configuration Service', () => {
  const mockFetchApi = vi.mocked(fetchApiModule.fetchApi);
  const mockedCapture = vi.mocked(Sentry.captureException);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getRatingScales()', () => {
    it('should fetch and return rating scales successfully', async () => {
      const mockScales = [
        { key: 'poor', label: 'Poor', description: 'Poor quality' },
        { key: 'fair', label: 'Fair', description: 'Fair quality' },
        { key: 'good', label: 'Good', description: 'Good quality' },
        { key: 'very_good', label: 'Very Good', description: 'Very good quality' },
        { key: 'excellent', label: 'Excellent', description: 'Excellent quality' },
      ];

      mockFetchApi.mockResolvedValue(mockScales);

      const result = await getRatingScales();

      expect(result).toEqual(mockScales);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/staff/training/config/rating-scales',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toHaveLength(5);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getRatingScales();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getRatingScales();

      expect(result).toEqual([]);
    });

    it('should handle network errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new TypeError('Network error'));

      const result = await getRatingScales();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-123';
      mockFetchApi.mockResolvedValue([]);

      await getRatingScales(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockScales = [
        { key: 'poor', label: 'Poor' },
      ];

      mockFetchApi.mockResolvedValue(mockScales);

      const result = await getRatingScales();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
    });
  });

  describe('getLessonTypes()', () => {
    it('should fetch and return lesson types successfully', async () => {
      const mockTypes = [
        { key: 'in_person', label: 'In-Person', description: 'Face-to-face training' },
        { key: 'online', label: 'Online', description: 'Online training' },
      ];

      mockFetchApi.mockResolvedValue(mockTypes);

      const result = await getLessonTypes();

      expect(result).toEqual(mockTypes);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/staff/training/config/lesson-types',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toHaveLength(2);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getLessonTypes();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getLessonTypes();

      expect(result).toEqual([]);
    });

    it('should handle network timeouts gracefully', async () => {
      mockFetchApi.mockRejectedValue(new Error('Request timeout'));

      const result = await getLessonTypes();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-456';
      mockFetchApi.mockResolvedValue([]);

      await getLessonTypes(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockTypes = [
        { key: 'in_person', label: 'In-Person' },
      ];

      mockFetchApi.mockResolvedValue(mockTypes);

      const result = await getLessonTypes();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
    });
  });

  describe('Error Handling', () => {
    it('should report errors to Sentry', async () => {
      mockFetchApi.mockRejectedValue(new Error('Test error'));

      await getRatingScales();

      expect(mockedCapture).toHaveBeenCalled();
    });

    it('should handle undefined response gracefully', async () => {
      mockFetchApi.mockResolvedValue(undefined);

      const result = await getRatingScales();

      expect(result).toEqual([]);
    });
  });
});
