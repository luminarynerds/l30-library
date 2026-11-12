/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Social Sharing Analytics API Service
 * Handles all requests to the sharing analytics dashboard endpoints
 */

import { API_BASE_URL } from '../../../constants/api';
import { getAccessToken } from '../../../utils/tokenStore';
import { getCurrentLocale } from '@/i18n'

export interface SharedResource {
  resource_id: number;
  resource_type: string;
  title: string;
  author?: string;
  share_count: number;
}

export interface PlatformBreakdown {
  platform: string;
  share_count: number;
  percentage: number;
}

export interface TopSharer {
  user_id: number;
  user_name: string;
  email: string;
  total_shares: number;
  favorite_platform?: string;
}

export interface ShareTrendDataPoint {
  date: string;
  total_shares: number;
  unique_sharers: number;
}

export interface TrendData {
  direction: 'up' | 'down' | 'stable';
  change_percentage: number;
  previous_value: number;
  current_value: number;
}

export interface StatsMetadata {
  generated_at: string;
  cached: boolean;
  cache_ttl: number;
  time_window: string;
}

export interface SharingDashboardResponse {
  top_shared_resources: SharedResource[];
  platform_breakdown: PlatformBreakdown[];
  total_shares: number;
  unique_sharers: number;
  avg_shares_per_user: number;
  top_sharers: TopSharer[];
  share_trends: ShareTrendDataPoint[];
  shares_trend?: TrendData;
  top_platform: string;
  top_platform_percentage: number;
  metadata: StatsMetadata;
}

export type ResourceType = 'book' | 'event' | 'reading_list' | 'author_profile' | 'staff_pick';

export const RESOURCE_TYPE_LABELS: Record<ResourceType, string> = {
  book: 'Books',
  event: 'Events',
  reading_list: 'Reading Lists',
  author_profile: 'Author Profiles',
  staff_pick: 'Staff Picks',
};

export interface SharingDashboardParams {
  days?: number;
  resourceTypes?: ResourceType[];
}

export async function getSharingDashboard(
  params: SharingDashboardParams | number = 30
): Promise<SharingDashboardResponse> {
  // Support legacy number-only call signature
  const { days = 30, resourceTypes } = typeof params === 'number'
    ? { days: params, resourceTypes: undefined }
    : params;

  if (days < 7 || days > 365) {
    throw new Error('Days parameter must be between 7 and 365');
  }

  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const searchParams = new URLSearchParams({ days: String(days) });
  if (resourceTypes && resourceTypes.length > 0) {
    searchParams.set('resource_type', resourceTypes.join(','));
  }

  const response = await fetch(
    `${API_BASE_URL}/admin/analytics/sharing-dashboard?${searchParams}`,
    {
      method: 'GET',
      credentials: 'include',
      headers,
    }
  );

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Access denied. Staff or admin role required.');
    }
    if (response.status === 404) {
      throw new Error('Sharing analytics endpoint not found');
    }
    throw new Error(`Failed to fetch sharing dashboard: ${response.statusText}`);
  }

  return response.json();
}

export function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function getPlatformColor(platform: string): string {
  const colors: Record<string, string> = {
    bluesky: '#0085FF',
    mastodon: '#6364FF',
    reddit: '#FF4500',
    email: '#EA4335',
    copy_link: '#4F46E5',
    whatsapp: '#25D366',
    telegram: '#0088cc',
  };
  return colors[platform] || '#6B7280';
}

export function getPlatformDisplayName(platform: string): string {
  const names: Record<string, string> = {
    bluesky: 'Bluesky',
    mastodon: 'Mastodon',
    reddit: 'Reddit',
    email: 'Email',
    copy_link: 'Copy Link',
    whatsapp: 'WhatsApp',
    telegram: 'Telegram',
  };
  return names[platform] || platform.charAt(0).toUpperCase() + platform.slice(1);
}