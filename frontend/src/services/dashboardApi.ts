/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Dashboard API client with typed endpoint functions.
 * All data is fetched fresh from the backend without hardcoding.
 */

import { get, post } from '@/lib/api-client';

// Types (should match backend schemas)
export interface CirculationSnapshot {
  active_checkouts: number;
  returned_total: number;
  overdue_items: number;
  checked_out_today: number;
  returned_today: number;
  active_holds: number;
  circulation_rate: number;
}

export interface OverdueItemDetail {
  checkout_id: number;
  due_date: string;
  checked_out_at: string;
  item_title: string;
  item_author: string | null;
  item_isbn: string | null;
  item_type: string;
  patron_id: number;
  patron_name: string;
  patron_email: string | null;
  patron_phone: string | null;
  fine_amount: number;
  fine_status: string;
  days_overdue: number;
}

export interface OverdueItemsResponse {
  items: OverdueItemDetail[];
  total: number;
  skip: number;
  limit: number;
}

export interface PopularItem {
  item_id: number;
  title: string;
  author: string | null;
  item_type: string;
  isbn: string | null;
  subjects: string[];
  checkout_count: number;
  hold_count: number;
}

export interface PopularItemsResponse {
  items: PopularItem[];
  days_range: number;
  total: number;
}

export interface ThemeMetric {
  theme: string;
  checkout_count: number;
  unique_items: number;
  utilization_rate: number;
  turnover_ratio: number;
  velocity_score: number;
}

export interface ThemeVelocityResponse {
  metrics: ThemeMetric[];
  days_range: number;
}

export interface HoldQueueStatus {
  total_pending: number;
  ready_for_pickup: number;
  expiring_soon_count: number;
  average_wait_days: number;
  longest_wait_days: number;
  queue_health: 'healthy' | 'warning';
}

export interface HealthComponent {
  name: string;
  score: number;
  weight: number;
}

export interface CollectionHealthResponse {
  overall_score: number;
  components: HealthComponent[];
  status: 'Excellent' | 'Good' | 'Fair' | 'Poor';
}

export interface SystemAlert {
  id: string;
  priority: 'critical' | 'warning' | 'info';
  category: string;
  title: string;
  message: string;
  action_url: string | null;
}

export interface SystemAlertsResponse {
  alerts: SystemAlert[];
}

export interface ComparisonStats {
  checkouts_today: number;
  checkouts_last_week: number;
  checkouts_last_year: number;
  returns_today: number;
  returns_last_week: number;
  returns_last_year: number;
  checkout_trend_percent: number;
  return_trend_percent: number;
}

export interface TrendingItem {
  item_id: number;
  title: string;
  author: string | null;
  item_type: string;
  checkout_count_today: number;
  checkout_count_week: number;
  hold_count: number;
  velocity_score: number;
}

export interface TrendingItemsResponse {
  items: TrendingItem[];
  timestamp: string;
}

export interface BusiestHour {
  hour: number;
  activity_count: number;
  activity_type: string;
  is_peak_now: boolean;
  upcoming_peak_in_minutes: number | null;
}

export interface ActivePatronsData {
  active_today: number;
  active_this_hour: number;
  peak_hour_expected: number | null;
}

export interface DashboardMetricsResponse {
  circulation_snapshot: CirculationSnapshot;
  holds_queue: HoldQueueStatus;
  overdue_count: number;
  collection_health: CollectionHealthResponse;
  timestamp: string;
}

export interface QuickActionRequest {
  action_type: 'mark_returned' | 'send_overdue_notice' | 'waive_fine';
  target_id: number;
  reason?: string;
}

export interface QuickActionResponse {
  success: boolean;
  message: string;
}

/**
 * Dashboard API client with all endpoints.
 * All methods return fresh data from the database.
 */
export const dashboardApi = {
  async getCompleteMetrics(): Promise<DashboardMetricsResponse> {
    const response = await get<DashboardMetricsResponse>('/staff/dashboard/metrics');
    return response;
  },

  async getCirculationSnapshot(): Promise<CirculationSnapshot> {
    const response = await get<CirculationSnapshot>('/staff/dashboard/circulation');
    return response;
  },

  async getOverdueItems(
    skip: number = 0,
    limit: number = 20
  ): Promise<OverdueItemsResponse> {
    return get<OverdueItemsResponse>(`/staff/dashboard/overdue?skip=${skip}&limit=${limit}`);
  },

  async getPopularItems(
    days: number = 90,
    limit: number = 20
  ): Promise<PopularItemsResponse> {
    return get<PopularItemsResponse>(`/staff/dashboard/popular-items?days=${days}&limit=${limit}`);
  },

  async getThemeVelocity(days: number = 90): Promise<ThemeVelocityResponse> {
    return get<ThemeVelocityResponse>(`/staff/dashboard/theme-velocity?days=${days}`);
  },

  async getHoldQueueStatus(): Promise<HoldQueueStatus> {
    const response = await get<HoldQueueStatus>('/staff/dashboard/holds-queue');
    return response;
  },

  async getSystemAlerts(): Promise<SystemAlertsResponse> {
    const response = await get<SystemAlertsResponse>('/staff/dashboard/alerts');
    return response;
  },

  async getCollectionHealth(): Promise<CollectionHealthResponse> {
    const response = await get<CollectionHealthResponse>('/staff/dashboard/collection-health');
    return response;
  },

  async markItemReturned(checkoutId: number): Promise<QuickActionResponse> {
    const response = await post<QuickActionResponse>('/staff/dashboard/quick-actions', {
      action_type: 'mark_returned',
      target_id: checkoutId,
    });
    return response;
  },

  async sendOverdueNotice(checkoutId: number): Promise<QuickActionResponse> {
    const response = await post<QuickActionResponse>('/staff/dashboard/quick-actions', {
      action_type: 'send_overdue_notice',
      target_id: checkoutId,
    });
    return response;
  },

  async waiveFine(
    fineId: number,
    reason: string
  ): Promise<QuickActionResponse> {
    const response = await post<QuickActionResponse>('/staff/dashboard/quick-actions', {
      action_type: 'waive_fine',
      target_id: fineId,
      reason,
    });
    return response;
  },

  async getComparisonStats(): Promise<ComparisonStats> {
    const response = await get<ComparisonStats>('/staff/dashboard/comparison');
    return response;
  },

  async getTrendingItems(limit: number = 10): Promise<TrendingItemsResponse> {
    return get<TrendingItemsResponse>(`/staff/dashboard/trending?limit=${limit}`);
  },

  async getBusiestHour(): Promise<BusiestHour> {
    const response = await get<BusiestHour>('/staff/dashboard/busiest-hour');
    return response;
  },

  async getActivePatrons(): Promise<ActivePatronsData> {
    const response = await get<ActivePatronsData>('/staff/dashboard/active-patrons');
    return response;
  },
};
