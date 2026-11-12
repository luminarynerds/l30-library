/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef } from "react";
import toast from "react-hot-toast";
import api from "../api/api";
import { API_BASE } from '@/api/types';
import {
  Save, X as CloseIcon, Plus, Trash2, Eye, EyeOff,
  FileText, Video, HelpCircle, Beaker, FlaskConical,
  ChevronUp, ChevronDown, Check, X, AlertTriangle,
} from "lucide-react";
import { useTranslation } from '@/i18n'
import MediaUploadField from './training/MediaUploadField';
import { useAutoSave } from '../hooks/useAutoSave';
import AutoSaveIndicator from './AutoSaveIndicator';
import RichTextEditor, { type RichTextEditorHandle } from '@/components/editor/RichTextEditor';
import { MarkdownContent } from '@/components/learning/MarkdownContent';
import { toEditorHtml } from '@/lib/rich-text';
import type { AuthoringIssue } from '@/lib/authoring-checks';
import ConfirmDialog from '@/components/ConfirmDialog';

type LessonType = 'article' | 'video' | 'quiz' | 'sandbox' | 'lab';

interface QuizOption {
  text: string;
  is_correct: boolean;
}

interface QuizQuestion {
  id?: number;
  question_text: string;
  question_type: string;
  options: QuizOption[];
  explanation: string;
  sort_order: number;
  isNew?: boolean;
}

interface LessonData {
  id?: number;
  module_id: number;
  title: string;
  lesson_type: LessonType;
  content: Record<string, unknown>;
  estimated_minutes: number | null;
  sensory_notes: string;
  facilitator_notes: string;
  xp_reward: number;
  summary: string;
  visual_aid_url: string;
  audio_narration_url: string;
}

// Stable snapshot for autosave — includes quiz questions so a quiz edit
// triggers the same 2 s debounce as an article edit.
interface AutoSaveSnapshot {
  lesson: LessonData;
  quizQuestions: QuizQuestion[];
}

const LESSON_TYPE_CONFIG: Record<LessonType, { icon: React.ReactNode; label: string; description: string }> = {
  article: {
    icon: <FileText className="w-5 h-5" />,
    label: 'Article',
    description: 'Text-based lesson with markdown support',
  },
  video: {
    icon: <Video className="w-5 h-5" />,
    label: 'Video',
    description: 'Video content with transcript',
  },
  quiz: {
    icon: <HelpCircle className="w-5 h-5" />,
    label: 'Quiz',
    description: 'Multiple choice assessment',
  },
  sandbox: {
    icon: <Beaker className="w-5 h-5" />,
    label: 'Sandbox',
    description: 'Interactive practice environment',
  },
  lab: {
    icon: <FlaskConical className="w-5 h-5" />,
    label: 'Lab',
    description: 'Hands-on exercise with instructions',
  },
};

interface LessonEditorPanelProps {
  lessonId: number;
  onClose: () => void;
  onSaved?: (lessonId: number) => void;
  issues?: AuthoringIssue[];
  onDirtyChange?: (dirty: boolean) => void;
  courseId?: string;
}

export interface LessonEditorPanelHandle {
  forceSave: () => Promise<void>;
  cancelEdits: () => void;
}

const LessonEditorPanel = forwardRef<LessonEditorPanelHandle, LessonEditorPanelProps>(
  function LessonEditorPanel({ lessonId, onClose, onSaved, issues, onDirtyChange, courseId }, ref) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  const [pendingLessonType, setPendingLessonType] = useState<LessonType | null>(null);
  const rteRef = useRef<RichTextEditorHandle>(null);
  const labRteRef = useRef<RichTextEditorHandle>(null);

  const [lesson, setLesson] = useState<LessonData>({
    module_id: 0,
    title: "",
    lesson_type: "article",
    content: { body: "" },
    estimated_minutes: 10,
    sensory_notes: "",
    facilitator_notes: "",
    xp_reward: 10,
    summary: "",
    visual_aid_url: "",
    audio_narration_url: "",
  });

  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);

  useEffect(() => {
    let cancelled = false;
    // Clear stale quiz data immediately so a previous lesson's questions
    // don't remain visible while the new fetch is in flight.
    setQuizQuestions([]);
    discardedRef.current = false;

    (async () => {
      try {
        setLoading(true);
        const response = await api.get(`/learning/lessons/${lessonId}`);
        // If lessonId changed (or panel unmounted) while awaiting, discard result.
        if (cancelled) return;
        const data = response.data || response;

        const isArticle = (data.lesson_type as LessonType) === 'article';
        const isLabOrSandbox = (data.lesson_type as LessonType) === 'lab' || (data.lesson_type as LessonType) === 'sandbox';
        const rawBody = (data.content?.body as string) || "";
        const needsHtmlConversion = isArticle || isLabOrSandbox;
        const loadedContent = needsHtmlConversion
          ? { ...(data.content || {}), body: toEditorHtml(rawBody) }
          : (data.content || { body: "" });

        setLesson({
          id: data.id,
          module_id: data.module_id,
          title: data.title,
          lesson_type: data.lesson_type,
          content: loadedContent,
          estimated_minutes: data.estimated_minutes,
          sensory_notes: data.sensory_notes || "",
          facilitator_notes: data.facilitator_notes || "",
          xp_reward: data.xp_reward || 10,
          summary: data.summary || "",
          visual_aid_url: data.visual_aid_url || "",
          audio_narration_url: data.audio_narration_url || "",
        });

        if (isArticle) {
          rteRef.current?.setContent(toEditorHtml(rawBody));
        } else if (isLabOrSandbox) {
          labRteRef.current?.setContent(toEditorHtml(rawBody));
        }

        if (data.quiz_questions) {
          setQuizQuestions(data.quiz_questions.map((q: QuizQuestion) => ({
            ...q,
            options: q.options || [],
            explanation: q.explanation || "",
          })));
        }
      } catch (_err) {
        if (cancelled) return;
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
        toast.error(t('admin.adminLessonEditor.failedToLoadLesson'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [lessonId, t]);

  // Unified autosave: article fields + quiz questions on the same 2s debounce.
  // Guard: no autosave until title is non-blank.
  const autoSaveSnapshot: AutoSaveSnapshot = { lesson, quizQuestions };

  // Persist a snapshot to an EXPLICIT lesson id. Taking the target id as an
  // argument (instead of closing over the panel's current lessonId) is what
  // makes the switch-flush safe: when navigating away we must write the
  // OUTGOING lesson, never the one being navigated to. See the flush effect.
  const putLessonSnapshot = useCallback(async (targetLessonId: number, snapshot: AutoSaveSnapshot) => {
    const { lesson: data, quizQuestions: questions } = snapshot;
    const payload = {
      title: data.title,
      lesson_type: data.lesson_type,
      content: data.content,
      estimated_minutes: data.estimated_minutes,
      sensory_notes: data.sensory_notes || null,
      facilitator_notes: data.facilitator_notes || null,
      xp_reward: data.xp_reward,
      summary: data.summary || null,
      visual_aid_url: data.visual_aid_url || null,
      audio_narration_url: data.audio_narration_url || null,
    };
    await api.put(`/learning/lessons/${targetLessonId}`, payload);

    // Quiz questions: save alongside lesson fields in the same autosave pass.
    if (data.lesson_type === 'quiz') {
      await saveQuizQuestionsFor(targetLessonId, questions);
    }
  }, []);

  const autoSavePanel = useCallback(
    (snapshot: AutoSaveSnapshot) => putLessonSnapshot(lessonId, snapshot),
    [lessonId, putLessonSnapshot],
  );

  const autoSaveEnabled = !loading && !saving && !!lesson.title.trim();

  const {
    status: autoSaveStatus,
    lastSaved: autoSaveLastSaved,
    error: autoSaveError,
  } = useAutoSave<AutoSaveSnapshot>({
    data: autoSaveSnapshot,
    onSave: autoSavePanel,
    delay: 2000,
    enabled: autoSaveEnabled,
  });

  // Flush genuinely-unsaved edits to the lesson being navigated AWAY from.
  //
  // Refs float forward to the latest render, but on a lesson switch this
  // cleanup runs BEFORE the incoming lesson's fetch resolves, so snapshotRef
  // still holds the OUTGOING lesson's data -- and we PUT it to the captured
  // outgoing id. Previously this flushed the floating forceSave, which wrote
  // the outgoing content to the INCOMING lesson id and corrupted siblings just
  // by clicking through the outline (data-loss incident 2026-06-19). The dirty
  // check (snapshot vs the loaded baseline) keeps a no-edit click from
  // rewriting an untouched lesson at all.
  const snapshotRef = useRef(autoSaveSnapshot);
  snapshotRef.current = autoSaveSnapshot;
  const autoSaveEnabledRef = useRef(autoSaveEnabled);
  autoSaveEnabledRef.current = autoSaveEnabled;
  const baselineRef = useRef<string>('');
  const discardedRef = useRef(false);
  useEffect(() => {
    // Re-baseline only when a different lesson finishes loading, not on edits.
    if (!loading) {
      baselineRef.current = JSON.stringify(autoSaveSnapshot);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, lessonId]);
  const onDirtyChangeRef = useRef(onDirtyChange)
  onDirtyChangeRef.current = onDirtyChange
  useEffect(() => {
    const isDirty = autoSaveEnabled && JSON.stringify(autoSaveSnapshot) !== baselineRef.current
    onDirtyChangeRef.current?.(isDirty)

  }, [autoSaveEnabled, autoSaveSnapshot])

  useImperativeHandle(ref, () => ({
    forceSave: async () => {
      if (!autoSaveEnabledRef.current) return;
      discardedRef.current = false;
      await putLessonSnapshot(lessonId, snapshotRef.current);
      baselineRef.current = JSON.stringify(snapshotRef.current);
    },
    cancelEdits: () => {
      if (!baselineRef.current) return;
      discardedRef.current = true;
      try {
        const baseline = JSON.parse(baselineRef.current) as AutoSaveSnapshot;
        setLesson(baseline.lesson);
        setQuizQuestions(baseline.quizQuestions);
      } catch {
        // baseline corrupt - no-op; unmount flush will still be skipped via discardedRef
      }
    },
  }), [lessonId, putLessonSnapshot]);

  useEffect(() => {
    const outgoingLessonId = lessonId;
    return () => {
      if (discardedRef.current) return; // Discard was chosen; don't flush
      if (!autoSaveEnabledRef.current) return;
      const snapshot = snapshotRef.current;
      if (JSON.stringify(snapshot) === baselineRef.current) return;
      void putLessonSnapshot(outgoingLessonId, snapshot);
    };
  }, [lessonId, putLessonSnapshot]);

  const saveQuizQuestionsFor = async (id: number, questions: QuizQuestion[]) => {
    for (let i = 0; i < questions.length; i++) {
      const question = questions[i]!;
      const payload = {
        question_text: question.question_text,
        question_type: question.question_type || "multiple_choice",
        options: question.options,
        explanation: question.explanation || null,
        sort_order: i,
      };
      try {
        if (question.isNew || !question.id) {
          // Fix 1: capture the create response and write the server-assigned id
          // back into state so the next autosave debounce PUTs (updates) instead
          // of re-POSTing and creating a duplicate.
          const created = await api.post(`/learning/admin/lessons/${id}/quiz-questions`, payload);
          const createdData = created.data || created;
          // Fix 1 (cont.) + Fix 2: After this setState, autoSaveSnapshot changes
          // (isNew->false, id set). This triggers exactly one more autosave debounce
          // which will PUT (update). It stabilizes there -- no infinite loop.
          setQuizQuestions(prev => prev.map(q =>
            q === question ? { ...question, id: createdData.id, isNew: false } : q
          ));
        } else {
          await api.put(`/learning/admin/lessons/${id}/quiz-questions/${question.id}`, payload);
        }
      } catch (_err) {
        Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      }
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const payload = {
        title: lesson.title,
        lesson_type: lesson.lesson_type,
        content: lesson.content,
        estimated_minutes: lesson.estimated_minutes,
        sensory_notes: lesson.sensory_notes || null,
        facilitator_notes: lesson.facilitator_notes || null,
        xp_reward: lesson.xp_reward,
        summary: lesson.summary || null,
        visual_aid_url: lesson.visual_aid_url || null,
        audio_narration_url: lesson.audio_narration_url || null,
      };

      await api.put(`/learning/lessons/${lessonId}`, payload);

      if (lesson.lesson_type === 'quiz') {
        await saveQuizQuestionsFor(lessonId, quizQuestions);
      }

      toast.success(t('toast.adminLessonEditor.lessonSaved'));
      onSaved?.(lessonId);
      onClose();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(error.response?.data?.detail || t('toast.adminLessonEditor.failedToSaveLesson'));
    } finally {
      setSaving(false);
    }
  };

  const updateContent = (field: string, value: string) => {
    setLesson(prev => ({
      ...prev,
      content: { ...prev.content, [field]: value },
    }));
  };

  const addQuizQuestion = () => {
    setQuizQuestions(prev => [...prev, {
      question_text: "",
      question_type: "multiple_choice",
      options: [
        { text: "", is_correct: true },
        { text: "", is_correct: false },
        { text: "", is_correct: false },
        { text: "", is_correct: false },
      ],
      explanation: "",
      sort_order: prev.length,
      isNew: true,
    }]);
  };

  const removeQuizQuestion = async (index: number) => {
    const question = quizQuestions[index]!;
    if (question.id && !question.isNew) {
      try {
        await api.delete(`/learning/admin/lessons/${lessonId}/quiz-questions/${question.id}`);
      } catch (_err) {
        toast.error(t('admin.adminLessonEditor.failedToDeleteQuestion'));
        return;
      }
    }
    setQuizQuestions(prev => prev.filter((_, i) => i !== index));
  };

  const updateQuestion = (index: number, field: string, value: unknown) => {
    setQuizQuestions(prev => prev.map((q, i) =>
      i === index ? { ...q, [field]: value } : q
    ));
  };

  const updateOption = (questionIndex: number, optionIndex: number, field: string, value: unknown) => {
    setQuizQuestions(prev => prev.map((q, qi) =>
      qi === questionIndex ? {
        ...q,
        options: q.options.map((o, oi) =>
          oi === optionIndex ? { ...o, [field]: value } : o
        ),
      } : q
    ));
  };

  const setCorrectOption = (questionIndex: number, optionIndex: number) => {
    setQuizQuestions(prev => prev.map((q, qi) =>
      qi === questionIndex ? {
        ...q,
        options: q.options.map((o, oi) => ({
          ...o,
          is_correct: oi === optionIndex,
        })),
      } : q
    ));
  };

  const addOption = (questionIndex: number) => {
    setQuizQuestions(prev => prev.map((q, i) =>
      i === questionIndex ? {
        ...q,
        options: [...q.options, { text: "", is_correct: false }],
      } : q
    ));
  };

  const removeOption = (questionIndex: number, optionIndex: number) => {
    setQuizQuestions(prev => prev.map((q, i) =>
      i === questionIndex ? {
        ...q,
        options: q.options.filter((_, oi) => oi !== optionIndex),
      } : q
    ));
  };

  const moveQuizQuestion = (index: number, direction: 'up' | 'down') => {
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= quizQuestions.length) return;
    setQuizQuestions((prev) => {
      const updated = [...prev];
      const a = updated[index];
      const b = updated[newIndex];
      if (!a || !b) return prev;
      [updated[index], updated[newIndex]] = [b, a];
      updated.forEach((q, i) => { q.sort_order = i; });
      return updated;
    });
  };

  if (loading) {
    return <div className="p-8 text-lsc-dark/70 dark:text-lsc-cream/70">Loading lesson...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Panel header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream">
            Edit Lesson
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {LESSON_TYPE_CONFIG[lesson.lesson_type].description}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <AutoSaveIndicator
            status={autoSaveStatus}
            lastSaved={autoSaveLastSaved}
            error={autoSaveError}
            disabled={!autoSaveEnabled}
          />
          <button
            type="button"
            onClick={() => setPreviewMode(!previewMode)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              previewMode
                ? 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
            }`}
          >
            {previewMode ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {previewMode ? 'Edit' : 'Preview'}
          </button>
          {courseId && lesson.id && (
            <a
              href={`/learn/course/${courseId}/lesson/${lesson.id}?preview=true`}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t('lessonEditor.previewAsPatronAriaLabel', 'Preview this lesson as a patron (opens in a new tab)')}
              className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600"
            >
              <Eye className="w-4 h-4" aria-hidden="true" />
              {t('lessonEditor.previewAsPatron', 'Preview as patron')}
              <span className="sr-only">{t('lessonEditor.opensInNewTab', '(opens in a new tab)')}</span>
            </a>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close lesson editor"
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            <CloseIcon className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>
      </div>

      {issues && issues.length > 0 && (
        <ul
          className="space-y-1.5"
          aria-label="Items to finish for this lesson"
        >
          {issues.map((issue) => (
            <li
              key={issue.code}
              className="flex items-start gap-2 text-sm text-status-warning-800 dark:text-status-warning-200"
            >
              <AlertTriangle
                className="w-4 h-4 shrink-0 mt-0.5 text-status-warning-600 dark:text-status-warning-400"
                aria-hidden="true"
              />
              <span>{issue.message}</span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Basic Info */}
        <div className="bg-lsc-white dark:bg-earth-800 shadow-md rounded-lg p-6 border border-lsc-border dark:border-earth-700 space-y-4">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Lesson Details
          </h3>

          <div>
            <label htmlFor="panel-lesson-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Title *
            </label>
            <input
              id="panel-lesson-title"
              type="text"
              required
              value={lesson.title}
              onChange={(e) => setLesson({ ...lesson, title: e.target.value })}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label htmlFor="panel-lesson-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Type
              </label>
              <select
                id="panel-lesson-type"
                value={lesson.lesson_type}
                onChange={(e) => setPendingLessonType(e.target.value as LessonType)}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              >
                {Object.entries(LESSON_TYPE_CONFIG).map(([value, config]) => (
                  <option key={value} value={value}>{config.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="panel-lesson-duration" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Duration (min)
              </label>
              <input
                id="panel-lesson-duration"
                type="number"
                min="1"
                value={lesson.estimated_minutes || ''}
                onChange={(e) => setLesson({ ...lesson, estimated_minutes: parseInt(e.target.value) || null })}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="panel-lesson-xp-reward" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                XP Reward
              </label>
              <input
                id="panel-lesson-xp-reward"
                type="number"
                min="0"
                value={lesson.xp_reward}
                onChange={(e) => setLesson({ ...lesson, xp_reward: parseInt(e.target.value) || 0 })}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>

            <div>
              <label htmlFor="panel-lesson-sensory-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Sensory Notes
              </label>
              <input
                id="panel-lesson-sensory-notes"
                type="text"
                value={lesson.sensory_notes}
                onChange={(e) => setLesson({ ...lesson, sensory_notes: e.target.value })}
                placeholder={t('placeholder.adminLessonEditor.egLoudAudio')}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
          </div>

          {/* Facilitator Notes -- rendered exactly once */}
          <div>
            <label htmlFor="panel-lesson-facilitator-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Facilitator Notes <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">(staff-only, not visible to patrons)</span>
            </label>
            <textarea
              id="panel-lesson-facilitator-notes"
              value={lesson.facilitator_notes}
              onChange={(e) => setLesson({ ...lesson, facilitator_notes: e.target.value })}
              placeholder="Setup checklist, pacing notes, scripts for difficult moments..."
              rows={4}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
        </div>

        {/* Content Editor based on lesson type */}
        <div className="bg-lsc-white dark:bg-earth-800 shadow-md rounded-lg p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            {LESSON_TYPE_CONFIG[lesson.lesson_type].icon}
            Content
          </h3>

          {/* Article Content */}
          {lesson.lesson_type === 'article' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Content
                </label>
                {previewMode ? (
                  <MarkdownContent
                    content={(lesson.content.body as string) || ''}
                    className="prose dark:prose-invert max-w-none p-4 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream/30 dark:bg-earth-700/30 min-h-[300px]"
                  />
                ) : (
                  <RichTextEditor
                    ref={rteRef}
                    defaultValue={(lesson.content.body as string) || ''}
                    onChange={(html) => updateContent('body', html)}
                    ariaLabel={t('admin.adminLessonEditor.lessonContent', 'Lesson content')}
                  />
                )}
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                Use the formatting toolbar to style the lesson. Switch to Preview to see exactly how patrons will read it.
              </p>
            </div>
          )}

          {/* Video Content */}
          {lesson.lesson_type === 'video' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Video URL
                </label>
                <input
                  type="url"
                  value={(lesson.content.video_url as string) || ''}
                  onChange={(e) => updateContent('video_url', e.target.value)}
                  placeholder={t('placeholder.adminLessonEditor.httpsyoutubecomwatchvOrHttpsvimeocom')}
                  className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Transcript
                </label>
                <textarea
                  rows={10}
                  value={(lesson.content.transcript as string) || ''}
                  onChange={(e) => updateContent('transcript', e.target.value)}
                  placeholder={t('admin.adminLessonEditor.videoTranscriptForAccessibility')}
                  className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
            </div>
          )}

          {/* Quiz Content */}
          {lesson.lesson_type === 'quiz' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {quizQuestions.length} question{quizQuestions.length !== 1 ? 's' : ''}
                </p>
                <button
                  type="button"
                  onClick={addQuizQuestion}
                  className="text-sm text-lsc-rose hover:underline flex items-center gap-1"
                >
                  <Plus className="w-4 h-4" />
                  Add Question
                </button>
              </div>

              {quizQuestions.length === 0 ? (
                <div className="text-center py-8 bg-lsc-cream/30 dark:bg-earth-700/30 rounded-lg">
                  <HelpCircle className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-2" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No questions yet</p>
                  <button
                    type="button"
                    onClick={addQuizQuestion}
                    className="mt-2 text-lsc-rose hover:underline"
                  >
                    Add your first question
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {quizQuestions.map((question, qIndex) => (
                    <div
                      key={question.id ?? `new-${qIndex}`}
                      className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream/20 dark:bg-earth-700/20"
                    >
                      <div className="flex items-start gap-3 mb-4">
                        <div className="flex flex-col gap-0.5 mt-1">
                          <button
                            type="button"
                            onClick={() => moveQuizQuestion(qIndex, 'up')}
                            disabled={qIndex === 0}
                            aria-label="Move question up"
                            className="p-0.5 rounded text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronUp className="w-4 h-4" aria-hidden="true" />
                          </button>
                          <button
                            type="button"
                            onClick={() => moveQuizQuestion(qIndex, 'down')}
                            disabled={qIndex === quizQuestions.length - 1}
                            aria-label="Move question down"
                            className="p-0.5 rounded text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronDown className="w-4 h-4" aria-hidden="true" />
                          </button>
                        </div>
                        <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
                          Q{qIndex + 1}
                        </span>
                        <div className="flex-1">
                          <textarea
                            rows={2}
                            value={question.question_text}
                            onChange={(e) => updateQuestion(qIndex, 'question_text', e.target.value)}
                            placeholder={t('placeholder.adminLessonEditor.enterYourQuestion')}
                            className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeQuizQuestion(qIndex)}
                          className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Options */}
                      <div className="ml-10 space-y-2">
                        <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                          Answer Options (click to mark correct)
                        </p>
                        {question.options.map((option, oIndex) => (
                          <div key={oIndex} className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => setCorrectOption(qIndex, oIndex)}
                              aria-label={option.is_correct ? "Marked correct" : "Mark as correct"}
                              className={`p-1 rounded-full transition-colors ${
                                option.is_correct
                                  ? 'bg-status-success-500 text-white'
                                  : 'bg-lsc-cream dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-status-success-200 dark:hover:bg-status-success-900/30'
                              }`}
                            >
                              {option.is_correct ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                            </button>
                            <input
                              type="text"
                              value={option.text}
                              onChange={(e) => updateOption(qIndex, oIndex, 'text', e.target.value)}
                              placeholder={`Option ${oIndex + 1}`}
                              className="flex-1 border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-1.5 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                            />
                            {question.options.length > 2 && (
                              <button
                                type="button"
                                onClick={() => removeOption(qIndex, oIndex)}
                                aria-label={`Remove option ${oIndex + 1}`}
                                className="p-1 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded transition-colors"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        ))}
                        {question.options.length < 6 && (
                          <button
                            type="button"
                            onClick={() => addOption(qIndex)}
                            className="text-xs text-lsc-rose hover:underline ml-8"
                          >
                            + Add option
                          </button>
                        )}
                      </div>

                      {/* Explanation */}
                      <div className="ml-10 mt-4">
                        <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                          Explanation (shown after answering)
                        </label>
                        <input
                          type="text"
                          value={question.explanation}
                          onChange={(e) => updateQuestion(qIndex, 'explanation', e.target.value)}
                          placeholder={t('admin.adminLessonEditor.explainWhyThisAnswerIs')}
                          className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-3 py-1.5 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent text-sm"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Sandbox/Lab Content -- WYSIWYG editor; edits content.body, which LabBody renders */}
          {(lesson.lesson_type === 'sandbox' || lesson.lesson_type === 'lab') && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Content <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">(shown to patrons)</span>
                </label>
                {previewMode ? (
                  <MarkdownContent
                    content={(lesson.content.body as string) || ''}
                    className="prose dark:prose-invert max-w-none p-4 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream/30 dark:bg-earth-700/30 min-h-[300px]"
                  />
                ) : (
                  <RichTextEditor
                    ref={labRteRef}
                    defaultValue={(lesson.content.body as string) || ''}
                    onChange={(html) => updateContent('body', html)}
                    ariaLabel="Lab content"
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Accessibility Options */}
        <div className="bg-lsc-white dark:bg-earth-800 shadow-md rounded-lg p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Accessibility
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Summary (for quick scan mode)
              </label>
              <textarea
                rows={3}
                value={lesson.summary}
                onChange={(e) => setLesson({ ...lesson, summary: e.target.value })}
                placeholder={t('admin.adminLessonEditor.briefSummaryOfThisLesson')}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <div className="space-y-4">
              <MediaUploadField
                label="Visual Aid"
                value={lesson.visual_aid_url}
                onChange={(url) => setLesson({ ...lesson, visual_aid_url: url })}
                getUploadUrl={() => `${API_BASE}/learning/lessons/${lessonId}/media?media_type=visual_aid`}
                accept="image/png,image/jpeg,image/gif,image/webp"
                helpText="PNG, JPEG, GIF, WebP up to 10MB"
              />
              <MediaUploadField
                label="Audio Narration"
                value={lesson.audio_narration_url}
                onChange={(url) => setLesson({ ...lesson, audio_narration_url: url })}
                getUploadUrl={() => `${API_BASE}/learning/lessons/${lessonId}/media?media_type=audio`}
                accept="audio/mpeg,audio/wav,audio/ogg"
                helpText="MP3, WAV, Ogg up to 50MB"
              />
            </div>
          </div>
        </div>

        {/* Save / Cancel */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-3 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 bg-lsc-rose text-white px-6 py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
          >
            <Save className="w-5 h-5" />
            {saving ? "Saving..." : "Save Lesson"}
          </button>
        </div>

        {/* Demand-collection link for per-lesson alternate-format authoring. */}
        <div className="mt-8 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-t border-lsc-border dark:border-earth-700 pt-4">
          <a
            href="/staff/admin/alternate-formats-request"
            className="underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
          >
            Alternate formats (audio / visual / text) -- request when you would use this
          </a>
        </div>
      </form>

      <ConfirmDialog
        isOpen={pendingLessonType !== null}
        title={t('admin.adminLessonEditor.changeLessonTypeTitle')}
        message={t('admin.adminLessonEditor.changeLessonTypeMessage')}
        confirmText={t('admin.adminLessonEditor.changeLessonTypeConfirm')}
        confirmVariant="warning"
        onConfirm={() => {
          if (pendingLessonType) {
            setLesson((prev) => ({ ...prev, lesson_type: pendingLessonType }));
          }
          setPendingLessonType(null);
        }}
        onCancel={() => setPendingLessonType(null)}
      />
    </div>
  );
});

export default LessonEditorPanel;
