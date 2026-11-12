/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface BoardReport {
  id: number;
  title: string;
  description?: string;
  report_period_start: string;
  report_period_end: string;
  status: string;
  frequency: string;
  format_generated: string;
  file_powerpoint?: boolean;
  file_pdf?: boolean;
  email_sent: boolean;
  email_sent_at?: string;
  created_at: string;
  generated_at?: string;
  stats_snapshot?: ReportStats;
  key_metrics?: Record<string, unknown>;
  narrative_prompts?: NarrativePrompts;
  executive_summary?: string;
}

export interface ReportStats {
  period: { start_date: string; end_date: string };
  circulation: {
    total_checkouts: number;
    completed_checkouts: number;
    active_checkouts: number;
    avg_checkout_duration_days: number;
  };
  financial: {
    total_revenue: number;
    revenue_by_type: Record<string, { total: number; count: number }>;
    outstanding_fines_count: number;
    outstanding_balance: number;
    daily_collection_count: number;
    payment_methods?: Record<string, unknown>;
    monthly_breakdown?: Array<{ month: string; amount: number }>;
  };
  patrons: {
    new_patrons: number;
    active_patrons: number;
    patrons_with_fines: number;
  };
  collection: {
    total_items: number;
    total_titles: number;
    checked_out_items: number;
    available_items: number;
    availability_rate: number;
  };
  holds: {
    new_holds: number;
    active_holds: number;
  };
  website?: WebsiteMetrics | null;
  comparison?: {
    period: { start_date: string; end_date: string };
    circulation: {
      total_checkouts: number;
      completed_checkouts: number;
      active_checkouts: number;
      avg_checkout_duration_days: number;
    };
    financial: {
      total_revenue: number;
      outstanding_fines_count: number;
      outstanding_balance: number;
    };
    patrons: {
      new_patrons: number;
      active_patrons: number;
      patrons_with_fines: number;
    };
    website?: WebsiteMetrics | null;
  };
  trends?: {
    checkout_change_percent?: number;
    revenue_change_percent?: number;
    patron_engagement_change_percent?: number;
  };
  narrative_prompts?: NarrativePrompts;
}

export interface WebsiteMetrics {
  pageviews: number;
  visitors: number;
  visits: number;
  bounces: number;
  top_pages: Array<{ path: string | null; views: number }>;
  top_referrers: Array<{ referrer: string | null; views: number }>;
  top_countries: Array<{ country: string | null; visits: number }>;
}

export interface NarrativePrompts {
  circulation: string[];
  financial: string[];
  patrons: string[];
  general: string[];
}

export const CHART_COLORS = ["#1F4E79", "#E89B44", "#2E7D32", "#C41E3A", "#5C4F3D", "#1565C0"];
