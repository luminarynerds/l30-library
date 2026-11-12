/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface EnrolledCourse {
  course: { id: number; title: string; description: string; estimated_minutes: number | null; difficulty?: string; };
  enrollment: { id: number; enrolled_at: string; completed_at: string | null; };
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
}

export interface RecentlyViewedCourse {
  id: number;
  title: string;
  viewedAt: string;
}

export interface RecommendedCourse {
  id: number;
  title: string;
  description: string;
  difficulty?: string;
  estimated_minutes: number | null;
  reason: string;
}

export interface LearningPath {
  id: number;
  title: string;
  description: string | null;
  total_courses: number;
  progress?: number;
  is_enrolled?: boolean;
}

export interface LastLesson {
  lessonId: number;
  lessonTitle: string;
  courseId: number;
  courseTitle: string;
  viewedAt: string;
  position?: number;
}
