/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Training Configuration API Service
 *
 * Provides functions for fetching dynamic training configuration options
 * used by staff forms and components. Includes rating scales and lesson types.
 */

import { fetchApi } from '@/api/fetchApi';

export interface RatingScaleOption {
  key: string;
  label: string;
  description?: string;
}

export interface LessonTypeOption {
  key: string;
  label: string;
  description?: string;
}

export async function getRatingScales(token?: string): Promise<RatingScaleOption[]> {
  try {
    const response = await fetchApi(
      '/staff/training/config/rating-scales',
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

export async function getLessonTypes(token?: string): Promise<LessonTypeOption[]> {
  try {
    const response = await fetchApi(
      '/staff/training/config/lesson-types',
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
