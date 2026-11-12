/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Volunteer Configuration Service Tests
 *
 * Tests for getVolunteerRoles() and getSkillLevels() functions
 * Covers success cases, error handling, and data validation
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getVolunteerRoles, getSkillLevels } from '../volunteers';
import * as fetchApiModule from '@/api/fetchApi';
import * as Sentry from '@/lib/sentry-lazy';

vi.mock('@/api/fetchApi');
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}));

describe('Volunteer Configuration Service', () => {
  const mockFetchApi = vi.mocked(fetchApiModule.fetchApi);
  const mockedCapture = vi.mocked(Sentry.captureException);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getVolunteerRoles()', () => {
    it('should fetch and return volunteer roles successfully', async () => {
      const mockRoles = [
        { key: 'delivery', label: 'Delivery', description: 'Delivery services' },
        { key: 'programming', label: 'Programming', description: 'Program assistance' },
        { key: 'shelving', label: 'Shelving', description: 'Shelving items' },
      ];

      mockFetchApi.mockResolvedValue(mockRoles);

      const result = await getVolunteerRoles();

      expect(result).toEqual(mockRoles);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/volunteers/config/roles',
        {}
      );
      expect(result.length).toBeGreaterThan(0);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
    });

    it('should handle network errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new TypeError('Network error'));

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-volunteer';
      mockFetchApi.mockResolvedValue([]);

      await getVolunteerRoles(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        '/volunteers/config/roles',
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockRoles = [
        { key: 'delivery', label: 'Delivery', description: 'Delivery services' },
      ];

      mockFetchApi.mockResolvedValue(mockRoles);

      const result = await getVolunteerRoles();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
    });

    it('should handle timeout errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Request timeout'));

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
    });

    it('should handle undefined response gracefully', async () => {
      mockFetchApi.mockResolvedValue(undefined);

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
    });
  });

  describe('getSkillLevels()', () => {
    it('should fetch and return skill levels successfully', async () => {
      const mockLevels = [
        { key: 'beginner', label: 'Beginner', description: 'Beginning level' },
        { key: 'intermediate', label: 'Intermediate', description: 'Intermediate level' },
        { key: 'advanced', label: 'Advanced', description: 'Advanced level' },
        { key: 'expert', label: 'Expert', description: 'Expert level' },
      ];

      mockFetchApi.mockResolvedValue(mockLevels);

      const result = await getSkillLevels();

      expect(result).toEqual(mockLevels);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/volunteers/config/skill-levels',
        {}
      );
      expect(result).toHaveLength(4);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getSkillLevels();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getSkillLevels();

      expect(result).toEqual([]);
    });

    it('should handle network errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new TypeError('Network error'));

      const result = await getSkillLevels();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-skill';
      mockFetchApi.mockResolvedValue([]);

      await getSkillLevels(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        '/volunteers/config/skill-levels',
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockLevels = [
        { key: 'beginner', label: 'Beginner', description: 'Beginning level' },
      ];

      mockFetchApi.mockResolvedValue(mockLevels);

      const result = await getSkillLevels();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
    });

    it('should validate all four standard skill levels are present', async () => {
      const mockLevels = [
        { key: 'beginner', label: 'Beginner' },
        { key: 'intermediate', label: 'Intermediate' },
        { key: 'advanced', label: 'Advanced' },
        { key: 'expert', label: 'Expert' },
      ];

      mockFetchApi.mockResolvedValue(mockLevels);

      const result = await getSkillLevels();
      const keys = result.map(level => level.key);

      expect(keys).toContain('beginner');
      expect(keys).toContain('intermediate');
      expect(keys).toContain('advanced');
      expect(keys).toContain('expert');
    });

    it('should handle timeout errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Request timeout'));

      const result = await getSkillLevels();

      expect(result).toEqual([]);
    });

    it('should handle undefined response gracefully', async () => {
      mockFetchApi.mockResolvedValue(undefined);

      const result = await getSkillLevels();

      expect(result).toEqual([]);
    });
  });

  describe('Error Handling', () => {
    it('should report errors to Sentry', async () => {
      mockFetchApi.mockRejectedValue(new Error('Test error'));

      await getVolunteerRoles();

      expect(mockedCapture).toHaveBeenCalled();
    });

    it('should handle permission errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new Error('Unauthorized'));

      const result = await getSkillLevels();

      expect(result).toEqual([]);
    });

    it('should handle server errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new Error('Internal server error'));

      const result = await getVolunteerRoles();

      expect(result).toEqual([]);
    });
  });
});
