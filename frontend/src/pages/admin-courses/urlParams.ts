/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { CourseLifecycleStage } from '@/api/domains/learning/courses-api';
import type { AccessTab, DifficultyFilter, SortKey } from './types';

export const ALL_STAGES: CourseLifecycleStage[] = [
  'draft',
  'published',
  'archived',
];

export const ACCESS_TABS: AccessTab[] = ['all', 'patron', 'staff', 'admin'];

export function defaultTabForRole(role: string | undefined): AccessTab {
  if (role === 'super_admin' || role === 'director') return 'all';
  if (role === 'admin' || role === 'legal') return 'admin';
  if (role === 'staff' || role === 'teacher') return 'staff';
  return 'patron';
}

export function parseAccessTab(raw: string | null, fallback: AccessTab): AccessTab {
  if (raw === 'all' || raw === 'patron' || raw === 'staff' || raw === 'admin') return raw;
  return fallback;
}

// Stage filter is a set (multi-select chips). Default = all stages.
// Old `?status=published|draft` links map forward to the new `?stage=`
// param so existing bookmarks / deep links keep working.
// Legacy in_review/needs_revision values are silently treated as 'draft'.
export function isStage(v: string): v is CourseLifecycleStage {
  return (ALL_STAGES as string[]).includes(v);
}

export function parseStageSet(
  stageRaw: string | null,
  statusRaw: string | null,
): Set<CourseLifecycleStage> {
  if (stageRaw) {
    const picked = stageRaw
      .split(',')
      .map((s) => s.trim())
      .filter(isStage) as CourseLifecycleStage[];
    if (picked.length > 0) return new Set(picked);
  }
  // Backward-compat shim for legacy ?status= links.
  if (statusRaw === 'published') return new Set<CourseLifecycleStage>(['published']);
  if (statusRaw === 'draft') return new Set<CourseLifecycleStage>(['draft']);
  return new Set(ALL_STAGES);
}

export function parseDifficulty(raw: string | null): DifficultyFilter {
  if (raw === 'beginner' || raw === 'intermediate' || raw === 'advanced') return raw;
  return 'any';
}

export function parseSort(raw: string | null): SortKey {
  if (
    raw === 'updated_desc' ||
    raw === 'created_desc' ||
    raw === 'title_asc' ||
    raw === 'lessons_desc' ||
    raw === 'enrollees_desc' ||
    raw === 'modules_desc'
  ) {
    return raw;
  }
  return 'updated_desc';
}
