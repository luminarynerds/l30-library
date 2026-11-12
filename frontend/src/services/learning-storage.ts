/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import api from '../api/api';
import { API_BASE } from '@/api/types'
import type { RecentlyViewedCourse, LastLesson } from '../types/learning';

// Recently viewed courses and last lesson tracking
// Uses localStorage as offline cache; will sync to backend when
// POST ${API_BASE}/learning/courses/{id}/view and GET ${API_BASE}/learning/my-recent-courses
// endpoints are available.
export const RECENTLY_VIEWED_KEY = 'lsc_recently_viewed_courses';
export const LAST_LESSON_KEY = 'lsc_last_lesson';

export const getRecentlyViewedFromStorage = (): RecentlyViewedCourse[] => {
  try {
    const stored = localStorage.getItem(RECENTLY_VIEWED_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
    return [];
  }
};

export const getRecentlyViewed = async (isAuthenticated = false): Promise<RecentlyViewedCourse[]> => {
  // Anonymous visitors: skip the authed API call (would 401 and noise Sentry).
  if (!isAuthenticated) {
    return getRecentlyViewedFromStorage();
  }
  try {
    return await api.get<RecentlyViewedCourse[]>(`${API_BASE}/learning/my-recent-courses`);
  } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
  }
  return getRecentlyViewedFromStorage();
};

export const addToRecentlyViewed = async (course: { id: number; title: string }) => {
  // Always update localStorage for offline access
  const recent = getRecentlyViewedFromStorage().filter(c => c.id !== course.id);
  recent.unshift({ id: course.id, title: course.title, viewedAt: new Date().toISOString() });
  localStorage.setItem(RECENTLY_VIEWED_KEY, JSON.stringify(recent.slice(0, 5)));
  try { await api.post(`${API_BASE}/learning/courses/${course.id}/view`); } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
  }
};

// Last lesson tracking for quick resume
export const getLastLesson = async (): Promise<LastLesson | null> => {
  try {
    const stored = localStorage.getItem(LAST_LESSON_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
    return null;
  }
};

export const setLastLesson = async (lesson: LastLesson) => {
  localStorage.setItem(LAST_LESSON_KEY, JSON.stringify(lesson));
  try {
    await api.put(`${API_BASE}/learning/lessons/${lesson.lessonId}/position`, { position: lesson.position || 0 });
  } catch (err) {
    Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
  }
};
