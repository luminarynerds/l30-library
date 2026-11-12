/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { API_BASE } from '@/api/types';
import { Save, ArrowLeft, Loader2, BookOpen, History, ArrowRight, Eye, AlertTriangle, X as CloseIcon } from 'lucide-react';
import {
  getCourseStageHistory,
  createStubLesson,
  duplicateLesson,
  updateModule,
  type CourseStageTransitionRow,
} from '@/api/domains/learning/courses-api';
import api from '../api/api';
import ConfirmDialog from '../components/ConfirmDialog';
import { useTranslation } from '@/i18n'
import { AdminShell } from '@/components/shells'
import { AvailableCourse, Module, CourseFormData } from '../components/training/training-types'
import CourseDetailsSection from '../components/training/CourseDetailsSection'
import PrerequisitesSection from '../components/training/PrerequisitesSection'
import CourseOutlineRail from '../components/training/CourseOutlineRail'
import { groupIssuesByTarget, getDismissedIssueKeys, type AuthoringIssue, type IssueScope } from '@/lib/authoring-checks'
import CourseSaveStatusBar from '../components/training/CourseSaveStatusBar'
import { useCourseDraftAutosave } from '@/hooks/useCourseDraftAutosave'
import WhatsMissingPanel from '@/components/training/WhatsMissingPanel'
import LessonTemplatePicker from '@/components/training/LessonTemplatePicker'
import { type LessonTemplate } from '@/lib/lesson-templates'
import LessonEditorPanel, { type LessonEditorPanelHandle } from '@/components/LessonEditorPanel'

export default function AdminCourseFormPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const isEdit = Boolean(id && id !== 'new');

  // ---- Lesson selection (master/detail) -----------------------------------
  const selectedLessonId = searchParams.get('lesson');
  const lessonPanelRef = useRef<HTMLHeadingElement>(null);
  const lessonEditorRef = useRef<LessonEditorPanelHandle | null>(null);
  const courseSettingsPanelRef = useRef<HTMLHeadingElement>(null);
  const didSelectRef = useRef(false);

  const selectLesson = useCallback((lessonId: number) => {
    didSelectRef.current = true;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('lesson', String(lessonId));
      return next;
    });
  }, [setSearchParams]);

  const clearLesson = useCallback(() => {
    didSelectRef.current = true;
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('lesson');
      return next;
    });
  }, [setSearchParams]);

  // Dirty-guard for lesson switches
  const lessonIsDirtyRef = useRef(false)
  const [pendingLessonSwitch, setPendingLessonSwitch] = useState<{
    lessonId: number
    lessonTitle: string
  } | null>(null)

  // Move focus into the detail panel on selection (a11y).
  // Only fires when the user explicitly selected/cleared a lesson — not on initial mount.
  useEffect(() => {
    if (!didSelectRef.current) return;
    didSelectRef.current = false;
    if (selectedLessonId) {
      lessonPanelRef.current?.focus();
    } else {
      courseSettingsPanelRef.current?.focus();
    }
  }, [selectedLessonId]);
  // -------------------------------------------------------------------------

  const [formData, setFormData] = useState<CourseFormData>({
    title: '',
    description: '',
    thumbnail_url: '',
    access_level: 'patron',
    difficulty: 'beginner',
    estimated_minutes: '',
    sensory_warning: '',
    quiz_passing_threshold: '70',
    prerequisite_course_ids: [],
    xp_reward: '100',
    duration_days: '',
  });

  const [modules, setModules] = useState<Module[]>([]);

  const handleSelectLesson = useCallback(
    (lessonId: number) => {
      if (lessonIsDirtyRef.current && selectedLessonId && Number(selectedLessonId) !== lessonId) {
        let title = 'this lesson'
        for (const m of modules) {
          const l = m.lessons.find((lesson) => lesson.id === Number(selectedLessonId))
          if (l) { title = l.title || 'Untitled lesson'; break }
        }
        setPendingLessonSwitch({ lessonId, lessonTitle: title })
        return
      }
      selectLesson(lessonId)
    },
    [selectedLessonId, modules, selectLesson],
  )
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [availableCourses, setAvailableCourses] = useState<AvailableCourse[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);

  const [deleteModuleConfirm, setDeleteModuleConfirm] = useState<{ index: number; title: string } | null>(null);
  const [deleteLessonConfirm, setDeleteLessonConfirm] = useState<{
    moduleIndex: number;
    lessonIndex: number;
    title: string;
  } | null>(null);

  // E2: template picker (module id = picker open; null = closed)
  const [templatePickerModuleId, setTemplatePickerModuleId] = useState<number | null>(null)
  const [pendingTemplateModuleId, setPendingTemplateModuleId] = useState<number | null>(null)

  // W2-A: stub-lesson creation error (inline, not toast) so the admin sees the
  // failure in the modules section instead of the "+ Add lesson" click feeling
  // like a silent no-op.
  const [stubError, setStubError] = useState<string | null>(null);

  // ---- Checklist badge (Task 3) ------------------------------------------
  const [checklistOpen, setChecklistOpen] = useState(false);
  const checklistBtnRef = useRef<HTMLButtonElement>(null);
  const checklistDrawerRef = useRef<HTMLDivElement>(null);

  // Move focus into drawer on open; return focus on Esc close.
  useEffect(() => {
    if (checklistOpen && checklistDrawerRef.current) {
      // Focus the first focusable element in the drawer
      const first = checklistDrawerRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      first?.focus();
    }
  }, [checklistOpen]);

  useEffect(() => {
    if (!checklistOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setChecklistOpen(false);
        checklistBtnRef.current?.focus();
        return;
      }
      if (e.key === 'Tab' && checklistDrawerRef.current) {
        const focusable = Array.from(
          checklistDrawerRef.current.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ).filter((el) => !el.hasAttribute('disabled'));
        if (focusable.length === 0) { e.preventDefault(); return; }
        const first = focusable[0]!;
        const last = focusable[focusable.length - 1]!;
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [checklistOpen]);

  // ---- Autosave (W1-A) ---------------------------------------------------
  const isRefetchingRef = useRef(false);
  const {
    autoSaveStatus,
    lastSavedAt,
    autoSaveError,
    autoSavePaused,
    debounceRef,
    performSave,
    toggleAutoSavePause,
  } = useCourseDraftAutosave({ id, isEdit, loading, formData, isRefetchingRef });
  // ------------------------------------------------------------------------

  const fetchCourse = useCallback(async () => {
    isRefetchingRef.current = true;
    try {
      setLoading(true);
      const data = await api.get(`${API_BASE}/learning/courses/${id}`);
      setFormData({
        title: data.title || '',
        description: data.description || '',
        thumbnail_url: data.thumbnail_url || '',
        access_level: data.access_level || 'patron',
        difficulty: data.difficulty || 'beginner',
        estimated_minutes: data.estimated_minutes?.toString() || '',
        sensory_warning: data.sensory_warning || '',
        quiz_passing_threshold: data.quiz_passing_threshold?.toString() || '70',
        prerequisite_course_ids: data.prerequisite_course_ids || [],
        xp_reward: data.xp_reward?.toString() || '100',
        duration_days: data.duration_days?.toString() || '',
      });

      if (data.modules && Array.isArray(data.modules)) {
        setModules(
          data.modules.map((m: { id?: number; title: string; description?: string; sort_order: number; lessons?: Array<{ id?: number; title: string; lesson_type: string; content?: Record<string, unknown>; estimated_minutes?: number; sensory_notes?: string; sort_order: number }> }) => ({
            id: m.id,
            title: m.title,
            description: m.description || '',
            sort_order: m.sort_order,
            isExpanded: false,
            lessons: (m.lessons || []).map((l: { id?: number; title: string; lesson_type: string; content?: Record<string, unknown>; estimated_minutes?: number; sensory_notes?: string; sort_order: number }) => ({
              id: l.id,
              title: l.title,
              lesson_type: l.lesson_type,
              content: l.content || {},
              ...(l.estimated_minutes && { estimated_minutes: l.estimated_minutes }),
              ...(l.sensory_notes && { sensory_notes: l.sensory_notes }),
              sort_order: l.sort_order,
            })),
          }))
        );
      }
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(err instanceof Error ? err.message : t('toast.adminCourseForm.failedToLoadCourse'));
      navigate('/staff/admin/courses');
    } finally {
      setLoading(false);
      isRefetchingRef.current = false;
    }
  }, [id, navigate, t]);

  useEffect(() => {
    if (isEdit) {
      fetchCourse();
    }
  }, [isEdit, fetchCourse]);

  const fetchAvailableCourses = useCallback(async () => {
    try {
      setLoadingCourses(true);
      const data = await api.get(`${API_BASE}/learning/courses`);
      const courses = (data.items || data || [])
        .filter((c: { id: number; title: string; difficulty?: string }) => !id || c.id !== parseInt(id))
        .map((c: { id: number; title: string; difficulty?: string }) => ({
          id: c.id,
          title: c.title,
          difficulty: c.difficulty || 'beginner',
        }));
      setAvailableCourses(courses);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    } finally {
      setLoadingCourses(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAvailableCourses();
  }, [fetchAvailableCourses]);


  const togglePrerequisite = (courseId: number) => {
    setFormData((prev) => {
      const current = prev.prerequisite_course_ids;
      if (current.includes(courseId)) {
        return { ...prev, prerequisite_course_ids: current.filter((id) => id !== courseId) };
      } else {
        return { ...prev, prerequisite_course_ids: [...current, courseId] };
      }
    });
  };

  const updateField = (field: keyof CourseFormData, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    } else if (formData.title.length > 200) {
      newErrors.title = 'Title must be 200 characters or less';
    }

    if (formData.estimated_minutes && isNaN(parseInt(formData.estimated_minutes))) {
      newErrors.estimated_minutes = 'Must be a valid number';
    }

    const threshold = parseInt(formData.quiz_passing_threshold);
    if (isNaN(threshold) || threshold < 0 || threshold > 100) {
      newErrors.quiz_passing_threshold = 'Must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      const firstErrorField = Object.keys(errors)[0];
      if (firstErrorField) {
        const element = document.getElementById(firstErrorField);
        element?.focus();
      }
      return;
    }

    setSaving(true);

    try {
      const payload = {
        title: formData.title.trim(),
        description: formData.description.trim() || null,
        thumbnail_url: formData.thumbnail_url.trim() || null,
        access_level: formData.access_level,
        difficulty: formData.difficulty || null,
        estimated_minutes: formData.estimated_minutes ? parseInt(formData.estimated_minutes) : null,
        sensory_warning: formData.sensory_warning.trim() || null,
        quiz_passing_threshold: parseInt(formData.quiz_passing_threshold) || 70,
        prerequisite_course_ids: formData.prerequisite_course_ids,
        xp_reward: formData.xp_reward === '' ? 100 : parseInt(formData.xp_reward, 10),
        duration_days: formData.duration_days ? parseInt(formData.duration_days) : null,
      };

      if (isEdit) {
        await api.put(`${API_BASE}/learning/courses/${id}`, payload);
        toast.success(t('toast.adminCourseForm.courseUpdatedSuccessfully'));
      } else {
        await api.post(`${API_BASE}/learning/courses`, payload);
        toast.success(t('toast.adminCourseForm.courseCreatedSuccessfully'));
      }

      navigate('/staff/admin/courses');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminCourseForm.failedToSaveCourse'));
    } finally {
      setSaving(false);
    }
  };

  const addModule = () => {
    const newModule: Module = {
      title: '',
      description: '',
      sort_order: modules.length,
      lessons: [],
      isExpanded: true,
      isNew: true,
    };
    setModules([...modules, newModule]);
  };

  const deleteModule = (index: number) => {
    setModules((prev) => {
      const updated = [...prev];
      const module = updated[index];
      if (module) {
        if (module.id) {
          updated[index] = { ...module, isDeleted: true };
        } else {
          updated.splice(index, 1);
        }
      }
      return updated;
    });
    setDeleteModuleConfirm(null);
  };

  const moveModule = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= modules.length) return;

    setModules((prev) => {
      const updated = [...prev];
      const moduleA = updated[index];
      const moduleB = updated[newIndex];
      if (moduleA && moduleB) {
        [updated[index], updated[newIndex]] = [moduleB, moduleA];
        updated.forEach((m, i) => {
          m.sort_order = i;
        });
      }
      return updated;
    });
  };

  const moveLesson = (moduleIndex: number, lessonIndex: number, direction: 'up' | 'down') => {
    setModules((prev) => {
      const updated = [...prev];
      const module = updated[moduleIndex];
      if (!module) return updated;

      const lessons = [...module.lessons];
      const step = direction === 'up' ? -1 : 1;
      let target = lessonIndex + step;
      while (target >= 0 && target < lessons.length && lessons[target]?.isDeleted) {
        target += step;
      }
      if (target < 0 || target >= lessons.length) return updated;

      const a = lessons[lessonIndex];
      const b = lessons[target];
      if (!a || !b) return updated;
      [lessons[lessonIndex], lessons[target]] = [b, a];
      lessons.forEach((l, i) => {
        l.sort_order = i;
      });
      updated[moduleIndex] = { ...module, lessons };
      return updated;
    });
  };

  // Open a lesson inline in the detail panel. For existing lessons, select by
  // id. For new lessons, create a stub first then select the stub's id.
  const handleUpdateModuleTitle = useCallback(
    async (actualModuleIndex: number, title: string) => {
      const mod = modules[actualModuleIndex]
      if (!mod?.id) {
        setModules((prev) => {
          const updated = [...prev]
          const m = updated[actualModuleIndex]
          if (m) updated[actualModuleIndex] = { ...m, title }
          return updated
        })
        return
      }
      try {
        await updateModule(mod.id, { title })
        setModules((prev) => {
          const updated = [...prev]
          const m = updated[actualModuleIndex]
          if (m) updated[actualModuleIndex] = { ...m, title }
          return updated
        })
      } catch (err) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        toast.error('Could not save module title. Try again.')
      }
    },
    [modules],
  )

  const handleDuplicateLesson = useCallback(
    async (moduleIndex: number, lessonIndex: number) => {
      const lesson = modules[moduleIndex]?.lessons[lessonIndex]
      if (!lesson?.id) return
      setStubError(null)
      try {
        const copy = await duplicateLesson(lesson.id)
        await fetchCourse()
        selectLesson(copy.id)
      } catch (err) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
        setStubError('Could not duplicate lesson. Check your connection and try again.')
      }
    },
    [modules, fetchCourse, selectLesson],
  )

  const handleOpenLesson = useCallback(
    async (moduleIndex: number, lessonIndex?: number | null) => {
      const module = modules[moduleIndex];
      if (!module) return;
      setStubError(null);

      if (lessonIndex !== undefined && lessonIndex !== null) {
        const lesson = module.lessons[lessonIndex];
        if (lesson?.id) {
          selectLesson(lesson.id);
          return;
        }
      }

      // No lessonIndex (or lesson lacks a server-side id) -> show template picker first.
      if (!module.id) {
        setStubError('Save the course first to add lessons to a new module.');
        return;
      }
      setPendingTemplateModuleId(module.id)
      setTemplatePickerModuleId(module.id)
    },
    [modules, selectLesson],
  );

  const deleteLesson = (moduleIndex: number, lessonIndex: number) => {
    setModules((prev) => {
      const updated = [...prev];
      const module = updated[moduleIndex];
      if (!module) return updated;

      const moduleLessons = [...module.lessons];
      const lesson = moduleLessons[lessonIndex];

      if (lesson) {
        if (lesson.id) {
          moduleLessons[lessonIndex] = { ...lesson, isDeleted: true };
        } else {
          moduleLessons.splice(lessonIndex, 1);
        }
      }

      updated[moduleIndex] = { ...module, lessons: moduleLessons };
      return updated;
    });
    setDeleteLessonConfirm(null);
  };

  // ---- Grouped issues for checklist signals (Task 3) ---------------------
  const authoringModules = useMemo(
    () =>
      modules
        .filter((m) => !m.isDeleted)
        .map((m) => ({
          id: m.id,
          title: m.title,
          sort_order: m.sort_order,
          lessons: m.lessons
            .filter((l) => !l.isDeleted)
            .map((l) => ({
              id: l.id,
              title: l.title,
              lesson_type: l.lesson_type,
              content: l.content,
              sort_order: l.sort_order,
            })),
        })),
    [modules],
  )

  const authoringCourse = useMemo(
    () => ({
      title: formData.title,
      thumbnail_url: formData.thumbnail_url,
      access_level: formData.access_level,
      difficulty: formData.difficulty,
    }),
    [formData.title, formData.thumbnail_url, formData.access_level, formData.difficulty],
  )

  const groupedIssues = useMemo(() => {
    if (!isEdit) return { course: [] as AuthoringIssue[], byLesson: {} as Record<number, AuthoringIssue[]> }
    const dismissed = getDismissedIssueKeys(id ?? '')
    const raw = groupIssuesByTarget(authoringCourse, authoringModules)
    return {
      course: raw.course.filter((i) => !dismissed.has(i.code)),
      byLesson: Object.fromEntries(
        Object.entries(raw.byLesson).map(([k, v]) => [k, v.filter((i) => !dismissed.has(i.code))]),
      ) as Record<number, AuthoringIssue[]>,
    }
  }, [isEdit, id, authoringCourse, authoringModules])

  const issuesByLessonCount = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(groupedIssues.byLesson).map(([k, v]) => [Number(k), v.length]),
      ) as Record<number, number>,
    [groupedIssues.byLesson],
  )

  const totalOpenIssues = useMemo(
    () =>
      groupedIssues.course.length +
      Object.values(groupedIssues.byLesson).reduce((s, v) => s + v.length, 0),
    [groupedIssues],
  )

  const selectedLessonIssues = useMemo(
    () =>
      selectedLessonId
        ? (groupedIssues.byLesson[Number(selectedLessonId)] ?? [])
        : [],
    [selectedLessonId, groupedIssues.byLesson],
  )
  // -------------------------------------------------------------------------

  return (
    <AdminShell
      title={isEdit ? 'Edit Course' : 'Create Course'}
      subtitle={isEdit
        ? 'Update course details, modules, and lessons.'
        : 'Fill in the details below to create a new course.'}
      icon={<BookOpen className="w-7 h-7 text-lsc-rose" />}
      actions={
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => navigate('/staff/admin/courses')}
            className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg p-2 transition-colors"
            aria-label={t('admin.adminCourseForm.goBackToCoursesList')}
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back to Courses
          </button>
          {isEdit && id && (
            <a
              href={`/learn/course/${id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg p-2 transition-colors"
            >
              <Eye className="w-4 h-4" aria-hidden="true" />
              {t('admin.adminCourseForm.viewAsPatron', 'View as patron')}
              <span className="sr-only">{t('admin.adminCourseForm.viewAsPatronNewTab', '(opens in a new tab)')}</span>
            </a>
          )}
          {isEdit && totalOpenIssues > 0 && (
            <button
              ref={checklistBtnRef}
              type="button"
              onClick={() => {
                const wasOpen = checklistOpen;
                setChecklistOpen((o) => !o);
                if (!wasOpen) {
                  // Focus will move into drawer (handled by useEffect below)
                } else {
                  // Focus returns to trigger on close
                  checklistBtnRef.current?.focus();
                }
              }}
              className="
                inline-flex items-center gap-1.5 text-sm
                text-status-warning-700 dark:text-status-warning-300
                hover:bg-status-warning-100 dark:hover:bg-status-warning-900/30
                rounded-lg px-2 py-1.5 transition-colors
                focus:outline-none focus:ring-2 focus:ring-lsc-rose
              "
              aria-expanded={checklistOpen}
              aria-controls="checklist-drawer"
            >
              <AlertTriangle className="w-4 h-4" aria-hidden="true" />
              {totalOpenIssues} to finish
            </button>
          )}
          {isEdit && (
            <CourseSaveStatusBar
              status={autoSaveStatus}
              lastSavedAt={lastSavedAt}
              errorMessage={autoSaveError}
              onManualSave={() => {
                if (debounceRef.current) clearTimeout(debounceRef.current);
                void performSave();
              }}
              paused={autoSavePaused}
              onTogglePause={toggleAutoSavePause}
            />
          )}
        </div>
      }
      loading={loading}
      maxWidth="max-w-6xl"
    >
      {/* Two-zone master/detail layout: left = course outline, right = detail pane (course settings XOR lesson) */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* ── Left zone: course outline rail ── */}
        <div className="lg:w-72 shrink-0">
          <CourseOutlineRail
            courseTitle={formData.title || 'Untitled course'}
            modules={modules}
            selectedLessonId={selectedLessonId ? Number(selectedLessonId) : null}
            onSelectCourse={clearLesson}
            onSelectLesson={handleSelectLesson}
            onAddModule={addModule}
            onAddLesson={(moduleId) => {
              const moduleIndex = modules.findIndex((m) => m.id === moduleId)
              if (moduleIndex >= 0) void handleOpenLesson(moduleIndex)
            }}
            onMoveModule={moveModule}
            onMoveLesson={moveLesson}
            onDeleteModule={(i) => setDeleteModuleConfirm({ index: i, title: modules[i]?.title ?? '' })}
            onDeleteLesson={(mi, li) => {
              const lesson = modules[mi]?.lessons[li]
              setDeleteLessonConfirm({ moduleIndex: mi, lessonIndex: li, title: lesson?.title ?? '' })
            }}
            issuesByLesson={issuesByLessonCount}
            onDuplicateLesson={handleDuplicateLesson}
            onUpdateModuleTitle={handleUpdateModuleTitle}
            pendingSwitch={
              pendingLessonSwitch
                ? {
                    lessonTitle: pendingLessonSwitch.lessonTitle,
                    onSave: async () => {
                      await lessonEditorRef.current?.forceSave()
                      lessonIsDirtyRef.current = false
                      setPendingLessonSwitch(null)
                      selectLesson(pendingLessonSwitch.lessonId)
                    },
                    onDiscard: () => {
                      lessonEditorRef.current?.cancelEdits()
                      lessonIsDirtyRef.current = false
                      setPendingLessonSwitch(null)
                      selectLesson(pendingLessonSwitch.lessonId)
                    },
                  }
                : null
            }
          />

          {stubError && (
            <div role="alert" className="mt-2 mb-4 text-sm text-status-danger-600 dark:text-status-danger-400">
              {stubError}
            </div>
          )}
        </div>

        {/* ── Right zone: detail pane — course settings XOR lesson editor, never both ── */}
        <div className="flex-1 min-w-0">
          {selectedLessonId ? (
            <aside
              aria-label="Lesson editor"
              className="border-lsc-border dark:border-earth-700"
            >
              <h2
                ref={lessonPanelRef}
                tabIndex={-1}
                className="sr-only"
              >
                Lesson editor
              </h2>
              {/* Back to outline link — visible only on narrow screens */}
              <a
                href="#course-outline-body"
                onClick={(e) => { e.preventDefault(); document.getElementById('course-outline-body')?.querySelector('button')?.focus(); }}
                className="
                  lg:hidden inline-flex items-center gap-1 mb-3
                  text-xs text-lsc-rose hover:underline
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded
                "
              >
                ← Back to outline
              </a>
              <LessonEditorPanel
                ref={lessonEditorRef}
                lessonId={Number(selectedLessonId)}
                onClose={clearLesson}
                onSaved={() => { void fetchCourse(); }}
                issues={selectedLessonIssues}
                onDirtyChange={(dirty) => { lessonIsDirtyRef.current = dirty }}
                courseId={id && id !== 'new' ? id : undefined}
              />
            </aside>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <h2
                ref={courseSettingsPanelRef}
                tabIndex={-1}
                className="sr-only"
              >
                Course settings
              </h2>
              {/* Back to outline link — visible only on narrow screens */}
              <a
                href="#course-outline-body"
                onClick={(e) => { e.preventDefault(); document.getElementById('course-outline-body')?.querySelector('button')?.focus(); }}
                className="
                  lg:hidden inline-flex items-center gap-1 mb-3
                  text-xs text-lsc-rose hover:underline
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded
                "
              >
                ← Back to outline
              </a>
              <CourseDetailsSection
                formData={formData}
                errors={errors}
                onUpdate={updateField}
                courseId={id && id !== 'new' ? id : undefined}
                issues={groupedIssues.course}
              />

              <PrerequisitesSection
                formData={formData}
                availableCourses={availableCourses}
                loadingCourses={loadingCourses}
                isEdit={isEdit}
                onToggle={togglePrerequisite}
                onClearAll={() => updateField('prerequisite_course_ids', [])}
              />

              {isEdit && id && <StageHistoryPanel courseId={parseInt(id, 10)} t={t} />}

              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  type="submit"
                  disabled={saving}
                  className="
                    flex-1 bg-lsc-rose text-white
                    px-6 py-4 rounded-xl font-semibold
                    hover:bg-lsc-rose/90 motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center justify-center gap-2
                    focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
                    dark:focus:ring-offset-earth-800
                    min-h-[52px]
                  "
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="w-5 h-5" aria-hidden="true" />
                      {isEdit ? 'Save Changes' : 'Create Course'}
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/staff/admin/courses')}
                  disabled={saving}
                  className="
                    px-6 py-4 rounded-xl font-semibold
                    border border-lsc-border dark:border-earth-700
                    text-lsc-dark dark:text-lsc-cream
                    hover:bg-lsc-cream dark:hover:bg-earth-700
                    motion-safe:transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed
                    focus:outline-none focus:ring-2 focus:ring-lsc-rose
                    min-h-[52px]
                  "
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!deleteModuleConfirm}
        title="Delete Module?"
        message={`Are you sure you want to delete "${deleteModuleConfirm?.title}"? All lessons in this module will also be deleted.`}
        confirmText="Delete Module"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => {
          if (deleteModuleConfirm) deleteModule(deleteModuleConfirm.index);
        }}
        onCancel={() => setDeleteModuleConfirm(null)}
      />

      <ConfirmDialog
        isOpen={!!deleteLessonConfirm}
        title="Delete Lesson?"
        message={`Are you sure you want to delete "${deleteLessonConfirm?.title}"?`}
        confirmText="Delete Lesson"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => {
          if (deleteLessonConfirm) {
            deleteLesson(deleteLessonConfirm.moduleIndex, deleteLessonConfirm.lessonIndex);
          }
        }}
        onCancel={() => setDeleteLessonConfirm(null)}
      />
      {/* ── Checklist drawer (header badge → WhatsMissingPanel) ── */}
      {isEdit && id && checklistOpen && (
        <div
          ref={checklistDrawerRef}
          id="checklist-drawer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="checklist-drawer-heading"
          className="
            fixed inset-y-0 right-0 z-50 w-80 max-w-full
            bg-lsc-white dark:bg-earth-800
            border-l border-lsc-border dark:border-earth-700
            shadow-lg flex flex-col
          "
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h2 id="checklist-drawer-heading" className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
              Quality checklist
            </h2>
            <button
              type="button"
              onClick={() => {
                setChecklistOpen(false);
                checklistBtnRef.current?.focus();
              }}
              aria-label="Close checklist"
              className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <CloseIcon className="w-4 h-4 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <WhatsMissingPanel
              courseId={id}
              course={authoringCourse}
              modules={authoringModules}
              onNavigate={(scope: IssueScope) => {
                if (scope.kind === 'lesson' && scope.lessonId !== undefined) {
                  setChecklistOpen(false)
                  checklistBtnRef.current?.focus()
                  selectLesson(scope.lessonId)
                }
              }}
            />
          </div>
        </div>
      )}
      {/* ── E2: Lesson template picker ── */}
      {templatePickerModuleId !== null && (
        <LessonTemplatePicker
          onSelect={async (tpl: LessonTemplate) => {
            const moduleId = pendingTemplateModuleId
            setTemplatePickerModuleId(null)
            setPendingTemplateModuleId(null)
            if (!moduleId) return
            try {
              const stub = await createStubLesson(moduleId)
              if (tpl.id !== 'blank') {
                const { updateLesson } = await import('@/api/domains/learning/courses-api')
                await updateLesson(stub.id, {
                  lesson_type: tpl.lessonType,
                  content: tpl.defaultContent,
                })
              }
              await fetchCourse()
              selectLesson(stub.id)
            } catch (err) {
              Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
              setStubError('Could not create lesson. Check your connection and try again.')
            }
          }}
          onCancel={() => {
            setTemplatePickerModuleId(null)
            setPendingTemplateModuleId(null)
          }}
        />
      )}
    </AdminShell>
  );
}

type TFn = (key: string, paramsOrFallback?: Record<string, unknown> | string) => string;

const STAGE_HISTORY_KEY: Record<string, string> = {
  draft: 'admin.adminCourses.stage_draft',
  published: 'admin.adminCourses.stage_published',
  archived: 'admin.adminCourses.stage_archived',
};

// Stage-transition audit panel: one GET on mount, reverse-chronological,
// no fetch loop. Failure is non-fatal.
function StageHistoryPanel({ courseId, t }: { courseId: number; t: TFn }) {
  const [rows, setRows] = useState<CourseStageTransitionRow[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCourseStageHistory(courseId)
      .then((data) => {
        if (!cancelled) setRows(Array.isArray(data) ? data : []);
      })
      .catch((err: unknown) => {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const stageName = (s: string | null): string =>
    s && STAGE_HISTORY_KEY[s] ? t(STAGE_HISTORY_KEY[s] as string) : '—';

  return (
    <section
      aria-labelledby="stage-history-heading"
      className="
        bg-lsc-white dark:bg-earth-800
        border border-lsc-border dark:border-earth-700
        rounded-xl p-4 sm:p-6 mb-6
      "
    >
      <h2
        id="stage-history-heading"
        className="flex items-center gap-2 font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4"
      >
        <History className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        {t('admin.adminCourses.stageHistoryTitle')}
      </h2>

      {error ? (
        <p className="text-sm text-status-danger-600 dark:text-status-danger-400">
          {t('admin.adminCourses.stageHistoryError')}
        </p>
      ) : rows === null ? (
        <p
          className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
          role="status"
          aria-live="polite"
        >
          <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
          {t('admin.adminCourses.stageHistoryLoading')}
        </p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('admin.adminCourses.stageHistoryEmpty')}
        </p>
      ) : (
        <ol className="space-y-3">
          {rows.map((row) => (
            <li
              key={row.id}
              className="flex flex-col gap-1 border-l-2 border-lsc-border dark:border-earth-600 pl-3"
            >
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                <span>{stageName(row.from_stage)}</span>
                <ArrowRight className="w-3.5 h-3.5 text-lsc-dark/50 dark:text-lsc-cream/50" aria-hidden="true" />
                <span>{stageName(row.to_stage)}</span>
              </span>
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                {t('admin.adminCourses.stageHistoryMeta', {
                  actor: row.actor?.display_name ?? t('admin.adminCourses.stageHistoryUnknownActor'),
                  when: new Date(row.created_at).toLocaleString(),
                })}
              </span>
              {row.note && (
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                  {row.note}
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
