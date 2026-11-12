/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { API_BASE } from '@/api/types';
import api from '../../api/api';

// Lesson bookmark helpers
// Uses localStorage as offline cache; will sync to backend when
// POST/DELETE ${API_BASE}/learning/lessons/{id}/bookmark and
// GET ${API_BASE}/learning/my-bookmarks endpoints are available.
const BOOKMARKS_KEY = 'lsc_lesson_bookmarks';

export const getBookmarksFromStorage = (): number[] => {
  try {
    const stored = localStorage.getItem(BOOKMARKS_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch (err) {
    Sentry.captureException(err);
    return [];
  }
};

export const getBookmarks = async (): Promise<number[]> => {
  try {
    return await api.get<number[]>(`${API_BASE}/learning/my-bookmarks`);
  } catch (err) {
    Sentry.captureException(err);
  }
  return getBookmarksFromStorage();
};

export const toggleBookmark = async (lessonId: number): Promise<boolean> => {
  const bookmarks = getBookmarksFromStorage();
  const index = bookmarks.indexOf(lessonId);
  if (index > -1) {
    bookmarks.splice(index, 1);
  } else {
    bookmarks.push(lessonId);
  }
  localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(bookmarks));
  try {
    if (index === -1) {
      await api.post(`${API_BASE}/learning/lessons/${lessonId}/bookmark`);
    } else {
      await api.delete(`${API_BASE}/learning/lessons/${lessonId}/bookmark`);
    }
  } catch (err) {
    Sentry.captureException(err);
  }
  return index === -1; // returns true if added, false if removed
};
