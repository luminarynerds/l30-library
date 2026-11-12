/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Onboarding Configuration API Service
 *
 * Provides functions for fetching dynamic onboarding configuration options
 * used by onboarding forms and components. Includes follow-up period options.
 */

import { fetchApi } from '@/api/fetchApi';

export interface FollowUpPeriodOption {
  key: string;
  label: string;
  days_offset: number;
}

export async function getFollowUpPeriods(token?: string): Promise<FollowUpPeriodOption[]> {
  try {
    const response = await fetchApi(
      '/onboarding/config/follow-up-periods',
      {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }
    );
    return response || [];
  } catch (error) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)));
    return [];
  }
}
