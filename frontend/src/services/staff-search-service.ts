/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Staff Search Service
 *
 * Manages search functionality including caching, recent searches,
 * and local persistence.
 */

import { unifiedSearch, getRecentSearches } from '../api/staff-search-api';
import type { StaffSearchResponse } from '../api/staff-search-api';

const RECENT_SEARCHES_KEY = 'lsc:recent_staff_searches';
const SEARCH_CACHE_KEY = 'lsc:search_cache';
const MAX_RECENT_SEARCHES = 10;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

interface CacheEntry {
  data: StaffSearchResponse;
  timestamp: number;
}

export class StaffSearchService {
  private searchCache: Map<string, CacheEntry> = new Map();
  private abortController: AbortController | null = null;

  async search(
    query: string,
    options?: {
      page?: number;
      per_page?: number;
      types?: string[];
      useCache?: boolean;
    }
  ): Promise<StaffSearchResponse | null> {
    if (!query.trim()) {
      return null;
    }

    const cacheKey = this.getCacheKey(query, options);

    // Check cache first
    if (options?.useCache !== false) {
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        return cached;
      }
    }

    // Cancel any pending request
    if (this.abortController) {
      this.abortController.abort();
    }
    this.abortController = new AbortController();

    try {
      const response = await unifiedSearch(query, {
        page: options?.page || 1,
        per_page: options?.per_page || 20,
        ...(options?.types !== undefined ? { types: options.types } : {}),
        signal: this.abortController.signal,
      });

      if (response.success && response.data) {
        this.setInCache(cacheKey, response.data);
        this.addToRecentSearches(query);
        return response.data;
      }

      return null;
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
      return null;
    }
  }

  async getRecentSearches(limit?: number): Promise<string[]> {
    try {
      const response = await getRecentSearches(limit);
      if (response.success && response.data) {
        return response.data.searches;
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    }

    // Fallback to local storage
    return this.getLocalRecentSearches();
  }

  private getLocalRecentSearches(): string[] {
    try {
      const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  private addToRecentSearches(query: string): void {
    try {
      let searches = this.getLocalRecentSearches();

      // Remove if already exists and add to beginning
      searches = searches.filter(s => s !== query);
      searches.unshift(query);

      // Keep only max number of searches
      searches = searches.slice(0, MAX_RECENT_SEARCHES);

      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(searches));
    } catch (_error) {
      Sentry.captureMessage('Failed to save recent search:', 'warning');
    }
  }

  clearRecentSearches(): void {
    try {
      localStorage.removeItem(RECENT_SEARCHES_KEY);
    } catch (_error) {
      Sentry.captureMessage('Failed to clear recent searches:', 'warning');
    }
  }

  removeRecentSearch(query: string): void {
    try {
      let searches = this.getLocalRecentSearches();
      searches = searches.filter(s => s !== query);
      localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(searches));
    } catch (_error) {
      Sentry.captureMessage('Failed to remove recent search:', 'warning');
    }
  }

  cancelSearch(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  clearCache(): void {
    this.searchCache.clear();
    try {
      localStorage.removeItem(SEARCH_CACHE_KEY);
    } catch {
      // Ignore
    }
  }

  // Private helper methods

  private getCacheKey(
    query: string,
    options?: { page?: number; per_page?: number; types?: string[] }
  ): string {
    const typesPart = options?.types?.sort().join(',') || '';
    return `${query}:p${options?.page || 1}:pp${options?.per_page || 20}:${typesPart}`;
  }

  private getFromCache(key: string): StaffSearchResponse | null {
    const entry = this.searchCache.get(key);
    if (!entry) {
      return null;
    }

    // Check if cache has expired
    if (Date.now() - entry.timestamp > CACHE_TTL) {
      this.searchCache.delete(key);
      return null;
    }

    return entry.data;
  }

  private setInCache(key: string, data: StaffSearchResponse): void {
    this.searchCache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }
}

// Create singleton instance
export const staffSearchService = new StaffSearchService();
