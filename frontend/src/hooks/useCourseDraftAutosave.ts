/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useRef, useState, type MutableRefObject } from 'react';
import * as Sentry from '@/lib/sentry-lazy';
import api from '../api/api';
import { API_BASE } from '@/api/types';
import { type CourseSaveStatus } from '../components/training/CourseSaveStatusBar';
import { type CourseFormData } from '../components/training/training-types';

interface UseCourseDraftAutosaveParams {
  id: string | undefined;
  isEdit: boolean;
  loading: boolean;
  formData: CourseFormData;
  isRefetchingRef: MutableRefObject<boolean>;
}

export function useCourseDraftAutosave({
  id,
  isEdit,
  loading,
  formData,
  isRefetchingRef,
}: UseCourseDraftAutosaveParams) {
  const [autoSaveStatus, setAutoSaveStatus] = useState<CourseSaveStatus>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [autoSaveError, setAutoSaveError] = useState<string | undefined>(undefined);
  const [autoSavePaused, setAutoSavePaused] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitialLoadRef = useRef(true);
  const formDataRef = useRef(formData);
  // eslint-disable-next-line react-hooks/refs -- intentional sync ref update; see https://react.dev/reference/react/useRef#avoiding-recreating-the-ref-contents
  formDataRef.current = formData;
  const validationLockRef = useRef<CourseFormData | null>(null);

  const buildAutosavePayload = useCallback(() => {
    const fd = formDataRef.current;
    return {
      title: fd.title.trim(),
      description: fd.description.trim() || null,
      thumbnail_url: fd.thumbnail_url.trim() || null,
      access_level: fd.access_level,
      difficulty: fd.difficulty || null,
      estimated_minutes: fd.estimated_minutes ? parseInt(fd.estimated_minutes) : null,
      sensory_warning: fd.sensory_warning.trim() || null,
      quiz_passing_threshold: parseInt(fd.quiz_passing_threshold) || 70,
      prerequisite_course_ids: fd.prerequisite_course_ids,
      xp_reward: fd.xp_reward === '' ? 100 : parseInt(fd.xp_reward, 10),
      duration_days: fd.duration_days ? parseInt(fd.duration_days) : null,
    };
  }, []);

  const performSave = useCallback(async () => {
    if (!isEdit || !id) return;
    setAutoSaveStatus('saving');
    try {
      await api.put(`${API_BASE}/learning/courses/${id}`, buildAutosavePayload());
      setLastSavedAt(new Date());
      setAutoSaveStatus('saved');
      setAutoSaveError(undefined);
      Sentry.addBreadcrumb({
        category: 'authoring',
        message: 'course_autosave_succeeded',
        level: 'info',
        data: { courseId: id },
      });
    } catch (err: unknown) {
      const e = err as {
        status?: number;
        response?: { status?: number; data?: { detail?: string } };
        detail?: string;
        body?: { detail?: string };
        message?: string;
      };
      const statusCode = e?.status ?? e?.response?.status ?? 0;
      if (statusCode >= 400 && statusCode < 500) {
        const detail =
          e?.body?.detail ||
          e?.detail ||
          e?.response?.data?.detail ||
          e?.message ||
          'Validation error';
        validationLockRef.current = formDataRef.current;
        setAutoSaveError(detail);
        setAutoSaveStatus('validation-error');
        setAutoSavePaused(true);
        Sentry.addBreadcrumb({
          category: 'authoring',
          message: 'course_autosave_validation_error',
          level: 'warning',
          data: { courseId: id, status: statusCode },
        });
      } else {
        setAutoSaveStatus('failed-retry');
        Sentry.addBreadcrumb({
          category: 'authoring',
          message: 'course_autosave_failed',
          level: 'warning',
          data: { courseId: id, status: statusCode },
        });
      }
    }
  }, [id, isEdit, buildAutosavePayload]);

  useEffect(() => {
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      return;
    }
    if (!isEdit || loading) return;
    if (isRefetchingRef.current) return;

    if (validationLockRef.current) {
      if (validationLockRef.current === formData) return;
      validationLockRef.current = null;
      if (autoSavePaused) {
        setAutoSavePaused(false);
      }
    } else if (autoSavePaused) {
      return;
    }

    setAutoSaveStatus((prev) => (prev === 'saving' ? prev : 'writing'));

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      performSave();
    }, 2000);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [formData, isEdit, loading, autoSavePaused, performSave, isRefetchingRef]);

  const performSaveRef = useRef(performSave);
  // eslint-disable-next-line react-hooks/refs -- intentional sync ref update to avoid stale closure in the keydown listener
  performSaveRef.current = performSave;
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (debounceRef.current) clearTimeout(debounceRef.current);
        performSaveRef.current();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (autoSaveStatus === 'writing' || autoSaveStatus === 'saving') {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [autoSaveStatus]);

  const toggleAutoSavePause = useCallback(() => {
    setAutoSavePaused((p) => {
      if (p) {
        validationLockRef.current = null;
        if (autoSaveStatus === 'validation-error') setAutoSaveStatus('idle');
      }
      return !p;
    });
  }, [autoSaveStatus]);

  return {
    autoSaveStatus,
    lastSavedAt,
    autoSaveError,
    autoSavePaused,
    debounceRef,
    performSave,
    toggleAutoSavePause,
  };
}
