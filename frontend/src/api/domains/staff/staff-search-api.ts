/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Search API Client
 *
 * Provides access to advanced unified staff search functionality
 * for searching across patrons, items, checkouts, and events.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { clean } from '@/lib/utils'
import { getAccessToken } from '@/utils/tokenStore'
import type { ApiResponse } from './types'

export interface StaffSearchMetadata {
  [key: string]: unknown;
}

export interface StaffSearchResult {
  id: string;
  entity_type: 'patron' | 'item' | 'checkout' | 'event';
  title: string;
  subtitle?: string;
  snippet?: string;
  url?: string;
  score: number;
  source: string;
  metadata: StaffSearchMetadata;
}

export interface StaffSearchResponse {
  query: string;
  total_results: number;
  results: StaffSearchResult[];
  page: number;
  per_page: number;
  has_more: boolean;
  suggestions: string[];
}

export interface RecentSearchesResponse {
  searches: string[];
}

function getStaffToken(): string | null {
  return getAccessToken()
}

export async function unifiedSearch(
  query: string,
  options?: {
    page?: number;
    per_page?: number;
    types?: string[];
    signal?: AbortSignal;
  }
): Promise<ApiResponse<StaffSearchResponse>> {
  const token = getStaffToken()
  if (!token) {
    return {
      success: false,
      error: 'Authentication required',
    }
  }

  const params = new URLSearchParams();
  params.append('q', query);

  if (options?.page) {
    params.append('page', options.page.toString());
  }
  if (options?.per_page) {
    params.append('per_page', options.per_page.toString());
  }
  if (options?.types && options.types.length > 0) {
    params.append('types', options.types.join(','));
  }

  try {
    const data = await fetchApi<StaffSearchResponse>(
      `/staff/search/unified?${params.toString()}`,
      clean({
        method: 'GET',
        token,
        signal: options?.signal,
      })
    )

    return {
      success: true,
      data,
    };
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return {
        success: false,
        error: 'Search cancelled',
      };
    }

    if (isApiError(error)) {
      return {
        success: false,
        error: error.userMessage || error.detail || 'Search failed',
      }
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Search failed',
    };
  }
}

export async function getRecentSearches(
  limit?: number
): Promise<ApiResponse<RecentSearchesResponse>> {
  const token = getStaffToken()
  if (!token) {
    return {
      success: false,
      error: 'Authentication required',
    }
  }

  const params = new URLSearchParams();
  if (limit) {
    params.append('limit', limit.toString());
  }

  try {
    const data = await fetchApi<RecentSearchesResponse>(
      `/staff/search/recent?${params.toString()}`,
      {
        method: 'GET',
        token,
      }
    )

    return {
      success: true,
      data,
    };
  } catch (error) {
    if (isApiError(error)) {
      return {
        success: false,
        error: error.userMessage || error.detail || 'Failed to fetch recent searches',
      }
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch recent searches',
    };
  }
}
