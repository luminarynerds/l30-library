/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Lesson Viewer - The main lesson experience
 * Includes format picker, ND controls, progress tracking, and Focus Mode tabs
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { MarkdownContent } from "../learning/MarkdownContent";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, CheckCircle, Clock,
  Volume2, Focus, Timer, ChevronDown, ChevronUp,
  Eye, BookOpen, Headphones, Coffee, X
} from "lucide-react";
import clsx from "clsx";
import { FormatPicker, type ContentFormat } from "./FormatPicker";
import { TextToSpeech, FocusMode, PomodoroTimer, MicroTasks } from "./neurodivergent";
import { usePreferences } from "../../contexts/PreferencesContext";
import { t } from '@/i18n'

// Security: Strict DOMPurify config to limit XSS attack surface

interface LessonData {
  id: number;
  title: string;
  estimated_minutes: number | null;
  content: {
    body?: string;
    summary?: string;
    sections?: Array<{ title: string; content: string }>;
    video_url?: string;
    audio_url?: string;
    audio_narration_url?: string;
    preferred_break_interval?: number;
  };
  variants?: Array<{
    type: ContentFormat;
    content: Record<string, unknown>;
  }>;
}

interface LessonViewerProps {
  lesson: LessonData;
  courseId: number;
  courseTitle: string;
  isCompleted: boolean;
  onComplete: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  hasNext: boolean;
  hasPrev: boolean;
}

type FocusModeTab = "quick-scan" | "deep-dive" | "listen";

export function LessonViewer({
  lesson,
  courseId,
  courseTitle,
  isCompleted,
  onComplete,
  onNext,
  onPrev,
  hasNext,
  hasPrev,
}: LessonViewerProps) {
  const { preferences } = usePreferences();
  const [activeFormat, setActiveFormat] = useState<ContentFormat>("default");
  const [showControls, setShowControls] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [pomodoroEnabled, setPomodoroEnabled] = useState(false);
  const [tasks, setTasks] = useState<Array<{ id: string; label: string; completed: boolean }>>([]);

  // Focus Mode Tab state
  const [activeFocusTab, setActiveFocusTab] = useState<FocusModeTab>("deep-dive");

  // Break reminder state
  const [showBreakReminder, setShowBreakReminder] = useState(false);
  const [breakTimerActive, setBreakTimerActive] = useState(true);

  // Build format options from variants
  const formatOptions = [
    { type: "default" as ContentFormat, available: true },
    ...(lesson.variants?.map(v => ({ type: v.type, available: true })) || []),
  ];

  // Generate micro-tasks from content sections
  useEffect(() => {
    if (lesson.content.sections) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- tasks are seeded from props then independently mutated by handleTaskComplete; useMemo would lose completion state
      setTasks(lesson.content.sections.map((s, i) => ({
        id: `section-${i}`,
        label: s.title,
        completed: false,
      })));
    }
  }, [lesson.id, lesson.content.sections]);

  // Break reminder timer
  useEffect(() => {
    const breakInterval = lesson.content.preferred_break_interval;
    if (!breakInterval || !breakTimerActive) return;

    const timeoutMs = breakInterval * 60 * 1000;
    const timer = setTimeout(() => {
      setShowBreakReminder(true);
    }, timeoutMs);

    return () => clearTimeout(timer);
  }, [lesson.id, lesson.content.preferred_break_interval, breakTimerActive]);

  const breakResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismissBreakReminder = useCallback(() => {
    setShowBreakReminder(false);
    setBreakTimerActive(false);
    // Clear any existing timeout
    if (breakResetTimeoutRef.current) {
      clearTimeout(breakResetTimeoutRef.current);
    }
    breakResetTimeoutRef.current = setTimeout(() => setBreakTimerActive(true), 100);
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (breakResetTimeoutRef.current) {
        clearTimeout(breakResetTimeoutRef.current);
      }
    };
  }, []);

  const handleTaskComplete = (taskId: string) => {
    setTasks(prev => prev.map(t =>
      t.id === taskId ? { ...t, completed: true } : t
    ));
  };

  // Get content for current format
  const getContent = () => {
    if (activeFormat === "default") {
      return lesson.content;
    }
    const variant = lesson.variants?.find(v => v.type === activeFormat);
    return variant?.content || lesson.content;
  };

  const content = getContent();
  const textContent = typeof content === "string"
    ? content
    : (typeof (content as Record<string, unknown>)?.body === "string" ? (content as Record<string, unknown>).body : "") as string;

  // Extract first paragraph for Quick Scan
  const getQuickScanContent = () => {
    if (lesson.content.summary) {
      return lesson.content.summary;
    }

    const body = lesson.content.body || "";
    const firstParagraph = body.match(/<p[^>]*>(.*?)<\/p>/i)?.[0] ||
                           body.split("</p>")[0] + "</p>" ||
                           body.substring(0, 500);
    return firstParagraph;
  };

  const hasAudioNarration = !!lesson.content.audio_narration_url;

  const renderFocusModeTabs = () => (
    <div className="mb-6">
      <div className="flex items-center gap-1 p-1 bg-lsc-cream dark:bg-earth-800 rounded-xl" role="tablist" aria-label={t('aria.training.focusModeOptions')}>
        <button
          role="tab"
          id="focus-tab-quick-scan"
          aria-selected={activeFocusTab === "quick-scan"}
          aria-controls="focus-panel-content"
          tabIndex={activeFocusTab === "quick-scan" ? 0 : -1}
          onClick={() => setActiveFocusTab("quick-scan")}
          className={clsx(
            "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all",
            activeFocusTab === "quick-scan"
              ? "bg-lsc-cream dark:bg-lsc-brown text-lsc-rose dark:text-lsc-rose-light shadow-sm"
              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-dark/70"
          )}
        >
          <Eye aria-hidden="true" className="w-4 h-4" />
          Quick Scan
        </button>

        <button
          role="tab"
          id="focus-tab-deep-dive"
          aria-selected={activeFocusTab === "deep-dive"}
          aria-controls="focus-panel-content"
          tabIndex={activeFocusTab === "deep-dive" ? 0 : -1}
          onClick={() => setActiveFocusTab("deep-dive")}
          className={clsx(
            "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all",
            activeFocusTab === "deep-dive"
              ? "bg-lsc-cream dark:bg-lsc-brown text-lsc-rose dark:text-lsc-rose-light shadow-sm"
              : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-dark/70"
          )}
        >
          <BookOpen aria-hidden="true" className="w-4 h-4" />
          Deep Dive
        </button>

        {hasAudioNarration && (
          <button
            role="tab"
            id="focus-tab-listen"
            aria-selected={activeFocusTab === "listen"}
            aria-controls="focus-panel-content"
            tabIndex={activeFocusTab === "listen" ? 0 : -1}
            onClick={() => setActiveFocusTab("listen")}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all",
              activeFocusTab === "listen"
                ? "bg-lsc-cream dark:bg-lsc-brown text-lsc-rose dark:text-lsc-rose-light shadow-sm"
                : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-dark/70"
            )}
          >
            <Headphones aria-hidden="true" className="w-4 h-4" />
            Listen
          </button>
        )}
      </div>

      <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        {activeFocusTab === "quick-scan" && "Get the key points at a glance"}
        {activeFocusTab === "deep-dive" && "Read the full lesson content"}
        {activeFocusTab === "listen" && "Listen to the audio narration"}
      </p>
    </div>
  );

  const renderBreakReminder = () => (
    <div
      className="fixed bottom-6 right-6 max-w-sm bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg p-4 z-50"
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-full flex items-center justify-center">
          <Coffee aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            Time for a break?
          </h4>
          <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            You have been learning for {lesson.content.preferred_break_interval} minutes.
            A short break can help you retain information better.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={dismissBreakReminder}
              className="px-3 py-1.5 text-xs font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl transition-colors"
            >
              Take 5 min break
            </button>
            <button
              onClick={dismissBreakReminder}
              className="px-3 py-1.5 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-earth-100 transition-colors"
            >
              Continue learning
            </button>
          </div>
        </div>
        <button
          onClick={dismissBreakReminder}
          className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:hover:text-lsc-cream"
          aria-label={t('aria.training.dismissReminder')}
        >
          <X aria-hidden="true" className="w-4 h-4" />
        </button>
      </div>
    </div>
  );

  // Note: Content comes from trusted backend database, same pattern as existing code
  const renderTabContent = () => {
    switch (activeFocusTab) {
      case "quick-scan":
        return (
          <div className="prose prose-earth dark:prose-invert max-w-prose mx-auto mb-8">
            <div className="p-6 bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-800/50 rounded-xl">
              <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-rose-light mt-0 mb-3 flex items-center gap-2">
                <Eye aria-hidden="true" className="w-5 h-5" />
                Key Takeaways
              </h3>
              <MarkdownContent content={getQuickScanContent()} className="text-lsc-dark dark:text-earth-300" />
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 text-center">
              Ready to learn more? Switch to <button onClick={() => setActiveFocusTab("deep-dive")} className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium">Deep Dive</button> for the full content.
            </p>
          </div>
        );

      case "listen":
        return (
          <div className="prose prose-earth dark:prose-invert max-w-prose mx-auto mb-8">
            <div className="p-6 bg-lsc-cream dark:bg-lsc-brown/20 border border-lsc-border dark:border-lsc-dark/50 rounded-xl">
              <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream/70 mt-0 mb-4 flex items-center gap-2">
                <Headphones aria-hidden="true" className="w-5 h-5" />
                Audio Narration
              </h3>
              <audio
                src={lesson.content.audio_narration_url}
                controls
                className="w-full"
                aria-label={`Audio narration for ${lesson.title}`}
              >
                Your browser does not support the audio element.
              </audio>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 mb-0">
                Listen while you follow along, or close your eyes and absorb the information.
              </p>
            </div>
          </div>
        );

      case "deep-dive":
      default: {
        const contentAsRecord = content as Record<string, unknown>;
        return (
          <div className="prose prose-earth dark:prose-invert max-w-prose mx-auto mb-8">
            {typeof contentAsRecord.body === "string" && (
              <MarkdownContent content={contentAsRecord.body as string} />
            )}

            {Array.isArray(contentAsRecord.sections) && contentAsRecord.sections.map((section: unknown, i: number) => {
              const sec = section as Record<string, unknown>;
              return (
                <section key={i} className="mb-8">
                  <h2>{String(sec.title)}</h2>
                  <MarkdownContent content={String(sec.content)} />
                </section>
              );
            })}

            {typeof contentAsRecord.video_url === "string" && activeFormat === "video" && (
              <div className="aspect-video rounded-xl overflow-hidden bg-black">
                <video
                  src={contentAsRecord.video_url}
                  controls
                  className="w-full h-full"
                />
              </div>
            )}

            {typeof contentAsRecord.audio_url === "string" && activeFormat === "audio" && (
              <audio
                src={contentAsRecord.audio_url}
                controls
                className="w-full"
              />
            )}
          </div>
        );
      }
    }
  };

  const lessonBody = (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to={`/learn/course/${courseId}`}
          className="inline-flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose mb-4"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          Back to {courseTitle}
        </Link>

        <h1 className="text-2xl md:text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {lesson.title}
        </h1>

        <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {lesson.estimated_minutes && (
            <span className="flex items-center gap-1">
              <Clock aria-hidden="true" className="w-4 h-4" />
              {lesson.estimated_minutes} min
            </span>
          )}
          {isCompleted && (
            <span className="flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light">
              <CheckCircle aria-hidden="true" className="w-4 h-4" />
              Completed
            </span>
          )}
        </div>
      </div>

      {/* Focus Mode Tabs */}
      {renderFocusModeTabs()}

      {/* Format Picker */}
      {formatOptions.length > 1 && activeFocusTab === "deep-dive" && (
        <div className="mb-6">
          <FormatPicker
            formats={formatOptions}
            activeFormat={activeFormat}
            onSelect={setActiveFormat}
            preferredFormat={preferences.preferred_content_variant as ContentFormat}
          />
        </div>
      )}

      {/* ND Controls Toggle */}
      <button
        onClick={() => setShowControls(!showControls)}
        className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose mb-4"
      >
        {showControls ? <ChevronUp aria-hidden="true" className="w-4 h-4" /> : <ChevronDown aria-hidden="true" className="w-4 h-4" />}
        Learning tools
      </button>

      {showControls && (
        <div className="bg-lsc-cream dark:bg-earth-800/50 rounded-xl p-4 mb-6 space-y-4">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => setTtsEnabled(!ttsEnabled)}
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
                ttsEnabled
                  ? "bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light"
                  : "bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70"
              )}
            >
              <Volume2 className="w-4 h-4" />
              Read Aloud
            </button>

            <button
              onClick={() => setFocusMode(!focusMode)}
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
                focusMode
                  ? "bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light"
                  : "bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70"
              )}
            >
              <Focus aria-hidden="true" className="w-4 h-4" />
              Focus Mode
            </button>

            <button
              onClick={() => setPomodoroEnabled(!pomodoroEnabled)}
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors",
                pomodoroEnabled
                  ? "bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light"
                  : "bg-lsc-white dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70"
              )}
            >
              <Timer aria-hidden="true" className="w-4 h-4" />
              Pomodoro
            </button>
          </div>

          {ttsEnabled && (
            <TextToSpeech text={textContent} enabled={ttsEnabled} onToggle={setTtsEnabled} />
          )}

          {tasks.length > 0 && (
            <MicroTasks tasks={tasks} onTaskComplete={handleTaskComplete} />
          )}
        </div>
      )}

      {/* Main Content - Tab Based */}
      {renderTabContent()}

      {/* Footer Navigation */}
      <div className="flex items-center justify-between pt-6 border-t border-lsc-border dark:border-earth-700">
        <div>
          {hasPrev && (
            <button
              onClick={onPrev}
              className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose"
            >
              <ArrowLeft aria-hidden="true" className="w-4 h-4" />
              Previous
            </button>
          )}
        </div>

        <div className="flex items-center gap-4">
          {!isCompleted && (
            <button
              onClick={onComplete}
              className="flex items-center gap-2 px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
            >
              <CheckCircle aria-hidden="true" className="w-5 h-5" />
              Mark Complete
            </button>
          )}

          {hasNext && (
            <button
              onClick={onNext}
              className="flex items-center gap-2 px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
            >
              Next Lesson
              <ArrowRight aria-hidden="true" className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Pomodoro Timer */}
      <PomodoroTimer enabled={pomodoroEnabled} />

      {/* Break Reminder */}
      {showBreakReminder && renderBreakReminder()}
    </div>
  );

  if (focusMode) {
    return (
      <FocusMode enabled={focusMode} onToggle={setFocusMode}>
        {lessonBody}
      </FocusMode>
    );
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      {lessonBody}
    </div>
  );
}
