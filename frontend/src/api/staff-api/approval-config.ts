/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Approval Configuration API Service
 *
 * Provides functions for fetching dynamic approval status configuration
 * options used by patron-related forms and components.
 */

import { fetchApi } from '@/api/fetchApi';

export interface ApprovalStatusOption {
  key: string;
  label: string;
  description?: string;
}

export async function getApprovalStatuses(token?: string): Promise<ApprovalStatusOption[]> {
  try {
    const response = await fetchApi(
      '/staff/patrons/config/approval-statuses',
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
