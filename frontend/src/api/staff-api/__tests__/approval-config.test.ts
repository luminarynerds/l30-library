/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Approval Configuration Service Tests
 *
 * Tests for getApprovalStatuses() function
 * Covers success cases, error handling, and data validation
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { getApprovalStatuses } from '../approval-config';
import * as fetchApiModule from '@/api/fetchApi';
import * as Sentry from '@/lib/sentry-lazy';

vi.mock('@/api/fetchApi');
vi.mock('@/lib/sentry-lazy', () => ({
  captureException: vi.fn(),
}));

describe('Approval Configuration Service', () => {
  const mockFetchApi = vi.mocked(fetchApiModule.fetchApi);
  const mockedCapture = vi.mocked(Sentry.captureException);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getApprovalStatuses()', () => {
    it('should fetch and return approval statuses successfully', async () => {
      const mockStatuses = [
        { key: 'pending', label: 'Pending', description: 'Awaiting review' },
        { key: 'approved', label: 'Approved', description: 'Request approved' },
        { key: 'rejected', label: 'Rejected', description: 'Request rejected' },
      ];

      mockFetchApi.mockResolvedValue(mockStatuses);

      const result = await getApprovalStatuses();

      expect(result).toEqual(mockStatuses);
      expect(mockFetchApi).toHaveBeenCalledWith(
        '/staff/patrons/config/approval-statuses',
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toHaveLength(3);
    });

    it('should return empty array on API error', async () => {
      mockFetchApi.mockRejectedValue(new Error('API Error'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
      expect(mockFetchApi).toHaveBeenCalled();
    });

    it('should return empty array when response is null', async () => {
      mockFetchApi.mockResolvedValue(null);

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should handle network errors gracefully', async () => {
      mockFetchApi.mockRejectedValue(new TypeError('Network error'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should pass authorization token when provided', async () => {
      const token = 'test-token-approval';
      mockFetchApi.mockResolvedValue([]);

      await getApprovalStatuses(token);

      expect(mockFetchApi).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: `Bearer ${token}` }
        })
      );
    });

    it('should validate returned data structure', async () => {
      const mockStatuses = [
        { key: 'pending', label: 'Pending', description: 'Awaiting review' },
      ];

      mockFetchApi.mockResolvedValue(mockStatuses);

      const result = await getApprovalStatuses();

      expect(result[0]).toHaveProperty('key');
      expect(result[0]).toHaveProperty('label');
      expect(typeof result[0]!.key).toBe('string');
      expect(typeof result[0]!.label).toBe('string');
    });

    it('should include all required status keys', async () => {
      const mockStatuses = [
        { key: 'pending', label: 'Pending' },
        { key: 'approved', label: 'Approved' },
        { key: 'rejected', label: 'Rejected' },
      ];

      mockFetchApi.mockResolvedValue(mockStatuses);

      const result = await getApprovalStatuses();
      const keys = result.map(status => status.key);

      expect(keys).toContain('pending');
      expect(keys).toContain('approved');
      expect(keys).toContain('rejected');
    });

    it('should handle undefined response gracefully', async () => {
      mockFetchApi.mockResolvedValue(undefined);

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should handle timeout errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Request timeout'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should handle authorization errors', async () => {
      mockFetchApi.mockRejectedValue(new Error('Forbidden'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });
  });

  describe('Error Handling', () => {
    it('should report errors to Sentry', async () => {
      mockFetchApi.mockRejectedValue(new Error('Test error'));

      await getApprovalStatuses();

      expect(mockedCapture).toHaveBeenCalled();
    });

    it('should handle HTTP 403 Forbidden', async () => {
      mockFetchApi.mockRejectedValue(new Error('403 Forbidden'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should handle HTTP 500 Server Error', async () => {
      mockFetchApi.mockRejectedValue(new Error('500 Internal Server Error'));

      const result = await getApprovalStatuses();

      expect(result).toEqual([]);
    });

    it('should handle malformed response gracefully', async () => {
      mockFetchApi.mockResolvedValue({ invalid: 'structure' });

      const result = await getApprovalStatuses();

      expect(result).toBeDefined();
    });
  });
});
