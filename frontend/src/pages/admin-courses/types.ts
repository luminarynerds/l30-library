/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type AccessTab = 'all' | 'patron' | 'staff' | 'admin';
export type DifficultyFilter = 'any' | 'beginner' | 'intermediate' | 'advanced';
export type SortKey =
  | 'updated_desc'
  | 'created_desc'
  | 'title_asc'
  | 'lessons_desc'
  | 'enrollees_desc'
  | 'modules_desc';
