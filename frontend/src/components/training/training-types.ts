/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface AvailableCourse {
  id: number;
  title: string;
  difficulty: string;
}

export interface Lesson {
  id?: number;
  title: string;
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab';
  content: Record<string, unknown>;
  estimated_minutes?: number;
  sensory_notes?: string;
  sort_order: number;
  isNew?: boolean;
  isDeleted?: boolean;
  is_published?: boolean;
}

export interface Module {
  id?: number;
  title: string;
  description?: string;
  sort_order: number;
  lessons: Lesson[];
  isExpanded?: boolean;
  isNew?: boolean;
  isDeleted?: boolean;
}

export interface CourseFormData {
  title: string;
  description: string;
  thumbnail_url: string;
  access_level: 'patron' | 'staff' | 'admin';
  difficulty: string;
  estimated_minutes: string;
  sensory_warning: string;
  quiz_passing_threshold: string;
  prerequisite_course_ids: number[];
  xp_reward: string;
  duration_days: string;
}
