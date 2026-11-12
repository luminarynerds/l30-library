/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * QuizPlayer - Interactive quiz experience
 * Displays questions one at a time with progress, supports multiple choice and true/false
 * Shows feedback and final score with pass/fail status
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { fetchApi } from '@/api/fetchApi';
import {
  ChevronLeft, ChevronRight, CheckCircle, XCircle,
  Trophy, RefreshCw, ArrowLeft, Clock, Award
} from "lucide-react";
import clsx from "clsx";
import { t } from '@/i18n'

interface QuizOption {
  text: string;
}

interface QuizQuestion {
  id: number;
  question_text: string;
  question_type: string;
  options: QuizOption[];
  sort_order: number;
}

interface QuizFeedback {
  question_id: number;
  correct: boolean;
  correct_option_index: number | null;
  explanation: string | null;
  selected_option_index: number;
}

interface QuizResult {
  attempt_id: number;
  score: number;
  total_questions: number;
  percentage: number;
  passed: boolean;
  feedback: QuizFeedback[];
  xp_earned: number;
}

interface QuizAttempt {
  id: number;
  score: number;
  passed: boolean;
  started_at: string;
  completed_at: string | null;
  total_questions: number;
  percentage: number;
}

interface QuizPlayerProps {
  lessonId: number;
  lessonTitle: string;
  onBack: () => void;
  onComplete?: () => void;
}

type QuizPhase = "loading" | "ready" | "in_progress" | "review" | "complete";

// eslint-disable-next-line complexity
export function QuizPlayer({ lessonId, lessonTitle, onBack, onComplete }: QuizPlayerProps) {
  const [phase, setPhase] = useState<QuizPhase>("loading");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<number, number>>(new Map());
  const [result, setResult] = useState<QuizResult | null>(null);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [previousAttempts, setPreviousAttempts] = useState<QuizAttempt[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Ref to capture current answers for submit to prevent race conditions
  const answersRef = useRef<Map<number, number>>(new Map());

  // Load previous attempts on mount
  const loadPreviousAttempts = useCallback(async () => {
    try {
      const attempts = await fetchApi(`/learning/lessons/${lessonId}/quiz/attempts`) as QuizAttempt[];
      setPreviousAttempts(attempts);
      setPhase("ready");
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
      setPhase("ready");
    }
  }, [lessonId]);

  useEffect(() => {
    loadPreviousAttempts();
  }, [loadPreviousAttempts]);

  const startQuiz = useCallback(async () => {
    setError(null);
    setPhase("loading");
    try {
      const data = await fetchApi(`/learning/lessons/${lessonId}/quiz/start`, { method: "POST" }) as {
        attempt_id: number;
        questions: QuizQuestion[];
        total_questions: number;
        passing_score: number;
      };

      setQuestions(data.questions);
      setCurrentIndex(0);
      setAnswers(new Map());
      setResult(null);
      setPhase("in_progress");
    } catch (_err) {
      const message = (_err as { message?: string })?.message;
      setError(message || "Failed to start quiz");
      setPhase("ready");
    }
  }, [lessonId]);

  const selectAnswer = (questionId: number, optionIndex: number) => {
    setAnswers((prev) => {
      const next = new Map(prev);
      next.set(questionId, optionIndex);
      // Keep ref in sync with state
      answersRef.current = next;
      return next;
    });
  };

  const submitQuiz = useCallback(async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);

    // Capture current answers from ref to prevent race conditions
    const currentAnswers = new Map(answersRef.current);
    const answerPayload = Array.from(currentAnswers.entries()).map(([question_id, selected_option_index]) => ({
      question_id,
      selected_option_index,
    }));

    try {
      const data = await fetchApi(`/learning/lessons/${lessonId}/quiz/submit`, {
        method: "POST",
        body: JSON.stringify({ answers: answerPayload }),
      }) as QuizResult;

      setResult(data);
      setReviewIndex(0);
      setPhase("complete");

      if (data.passed && onComplete) {
        onComplete();
      }
    } catch (_err) {
      const message = (_err as { message?: string })?.message;
      setError(message || "Failed to submit quiz");
    } finally {
      setIsSubmitting(false);
    }
  }, [lessonId, isSubmitting, onComplete]);

  const currentQuestion = questions[currentIndex];
  const isAnswered = currentQuestion && answers.has(currentQuestion.id);
  const allAnswered = questions.length > 0 && answers.size === questions.length;
  const progress = questions.length > 0 ? ((currentIndex + 1) / questions.length) * 100 : 0;

  // Loading state
  if (phase === "loading") {
    return (
      <div className="min-h-[400px] flex items-center justify-center" role="status" aria-live="polite" aria-label={t('aria.training.loadingQuiz')}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-earth-500 border-t-transparent rounded-full motion-safe:animate-spin" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading quiz...</p>
        </div>
      </div>
    );
  }

  // Ready to start state
  if (phase === "ready") {
    const bestAttempt = previousAttempts.find((a) => a.passed) || previousAttempts[0];

    return (
      <div className="max-w-2xl mx-auto">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose mb-6"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          Back to lesson
        </button>

        <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-8 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-lsc-cream dark:bg-lsc-dark/30 rounded-full mb-4">
              <Award aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Quiz: {lessonTitle}
            </h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Test your understanding of this lesson. Score 70% or higher to pass.
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl">
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300">{error}</p>
            </div>
          )}

          {bestAttempt && (
            <div className="mb-8 p-4 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
              <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                Previous Attempts ({previousAttempts.length})
              </h3>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {bestAttempt.passed ? (
                    <CheckCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  ) : (
                    <XCircle aria-hidden="true" className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/70">
                      Best: {bestAttempt.percentage}%
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {bestAttempt.score}/{bestAttempt.total_questions} correct
                    </p>
                  </div>
                </div>
                <span
                  className={clsx(
                    "px-3 py-1 rounded-full text-xs font-medium",
                    bestAttempt.passed
                      ? "bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-rose dark:text-lsc-cream/70"
                      : "bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light"
                  )}
                >
                  {bestAttempt.passed ? "Passed" : "Not passed"}
                </span>
              </div>
            </div>
          )}

          <button
            onClick={startQuiz}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
          >
            {previousAttempts.length > 0 ? (
              <>
                <RefreshCw aria-hidden="true" className="w-5 h-5" />
                Try Again
              </>
            ) : (
              <>
                <Clock aria-hidden="true" className="w-5 h-5" />
                Start Quiz
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // In progress state - question view
  if (phase === "in_progress" && currentQuestion) {
    const isTrueFalse = currentQuestion.question_type === "true_false" ||
                        (currentQuestion.options.length === 2 &&
                         currentQuestion.options.some(o => o.text.toLowerCase() === "true") &&
                         currentQuestion.options.some(o => o.text.toLowerCase() === "false"));

    return (
      <div className="max-w-2xl mx-auto">
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Question {currentIndex + 1} of {questions.length}
            </span>
            <span className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
              {Math.round(progress)}% complete
            </span>
          </div>
          <div className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
            <div
              className="h-full bg-lsc-rose transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Question card */}
        <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-8 shadow-sm border border-lsc-border dark:border-earth-700">
          <h2 className="text-xl font-medium text-lsc-dark dark:text-lsc-cream mb-6">
            {currentQuestion.question_text}
          </h2>

          {/* Options */}
          <div className={clsx(
            "space-y-3",
            isTrueFalse && "grid grid-cols-1 sm:grid-cols-2 gap-4 space-y-0"
          )}>
            {currentQuestion.options.map((option, idx) => {
              const isSelected = answers.get(currentQuestion.id) === idx;
              return (
                <button
                  key={idx}
                  onClick={() => selectAnswer(currentQuestion.id, idx)}
                  className={clsx(
                    "w-full p-4 rounded-xl text-left transition-all border-2",
                    isSelected
                      ? "border-earth-500 bg-lsc-cream dark:bg-lsc-dark/20"
                      : "border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown hover:border-lsc-border dark:hover:border-earth-600",
                    isTrueFalse && "text-center"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={clsx(
                        "flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center",
                        isSelected
                          ? "border-earth-500 bg-lsc-rose"
                          : "border-lsc-border dark:border-earth-700"
                      )}
                    >
                      {isSelected && (
                        <span className="w-2 h-2 bg-lsc-white dark:bg-earth-800 rounded-full" />
                      )}
                    </span>
                    <span
                      className={clsx(
                        "text-base",
                        isSelected
                          ? "text-lsc-rose dark:text-lsc-rose-light font-medium"
                          : "text-lsc-dark dark:text-lsc-cream/70"
                      )}
                    >
                      {option.text}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            disabled={currentIndex === 0}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-xl transition-colors",
              currentIndex === 0
                ? "text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed"
                : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose"
            )}
          >
            <ChevronLeft aria-hidden="true" className="w-5 h-5" />
            Previous
          </button>

          {currentIndex < questions.length - 1 ? (
            <button
              onClick={() => setCurrentIndex((i) => Math.min(questions.length - 1, i + 1))}
              disabled={!isAnswered}
              className={clsx(
                "flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium transition-colors",
                isAnswered
                  ? "bg-lsc-rose hover:bg-lsc-rose/90 text-white"
                  : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed"
              )}
            >
              Next
              <ChevronRight aria-hidden="true" className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={submitQuiz}
              disabled={!allAnswered || isSubmitting}
              className={clsx(
                "flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium transition-colors",
                allAnswered && !isSubmitting
                  ? "bg-lsc-rose hover:bg-lsc-rose/90 text-white"
                  : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed"
              )}
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full motion-safe:animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <CheckCircle aria-hidden="true" className="w-5 h-5" />
                  Submit Quiz
                </>
              )}
            </button>
          )}
        </div>

        {/* Question dots */}
        <div className="flex justify-center gap-2 mt-6">
          {questions.map((q, idx) => (
            <button
              key={q.id}
              onClick={() => setCurrentIndex(idx)}
              className={clsx(
                "w-3 h-3 rounded-full transition-all",
                idx === currentIndex
                  ? "bg-lsc-rose scale-125"
                  : answers.has(q.id)
                  ? "bg-lsc-rose"
                  : "bg-lsc-border dark:bg-lsc-brown"
              )}
              aria-label={`Go to question ${idx + 1}`}
            />
          ))}
        </div>
      </div>
    );
  }

  // Complete state - results
  if (phase === "complete" && result) {
    const currentFeedback = result.feedback[reviewIndex];
    const currentQ = questions.find((q) => q.id === currentFeedback?.question_id);

    return (
      <div className="max-w-2xl mx-auto">
        {/* Score card */}
        <div
          className={clsx(
            "rounded-xl p-8 text-center mb-8 border-2",
            result.passed
              ? "bg-lsc-cream dark:bg-lsc-brown/20 border-lsc-border dark:border-earth-700"
              : "bg-lsc-cream dark:bg-lsc-dark/20 border-lsc-border dark:border-earth-700"
          )}
        >
          <div
            className={clsx(
              "inline-flex items-center justify-center w-20 h-20 rounded-full mb-4",
              result.passed
                ? "bg-lsc-cream dark:bg-lsc-dark/50"
                : "bg-lsc-cream dark:bg-lsc-dark/50"
            )}
          >
            {result.passed ? (
              <Trophy aria-hidden="true" className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" />
            ) : (
              <RefreshCw aria-hidden="true" className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" />
            )}
          </div>

          <h2
            className={clsx(
              "text-3xl font-serif font-bold mb-2",
              result.passed
                ? "text-lsc-rose dark:text-lsc-cream/70"
                : "text-lsc-rose dark:text-lsc-rose-light"
            )}
          >
            {result.passed ? "Congratulations!" : "Keep Learning!"}
          </h2>

          <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            You scored{" "}
            <span className="font-bold">{result.percentage}%</span> ({result.score}/
            {result.total_questions} correct)
          </p>

          {result.passed && result.xp_earned > 0 && (
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-dark/30 rounded-full">
              <Award aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              <span className="font-medium text-lsc-rose dark:text-lsc-rose-light">
                +{result.xp_earned} XP earned!
              </span>
            </div>
          )}

          {!result.passed && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              You need 70% to pass. Review the answers below and try again.
            </p>
          )}
        </div>

        {/* Review section */}
        <div className="bg-lsc-cream dark:bg-earth-800 rounded-xl p-8 shadow-sm border border-lsc-border dark:border-earth-700">
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-6">
            Review Answers
          </h3>

          {currentQ && currentFeedback && (
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                {currentFeedback.correct ? (
                  <CheckCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                ) : (
                  <XCircle aria-hidden="true" className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" />
                )}
                <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Question {reviewIndex + 1} of {result.feedback.length}
                </span>
              </div>

              <p className="text-lg text-lsc-dark dark:text-lsc-cream mb-4">
                {currentQ.question_text}
              </p>

              <div className="space-y-2">
                {currentQ.options.map((opt, idx) => {
                  const isSelected = currentFeedback.selected_option_index === idx;
                  const isCorrect = currentFeedback.correct_option_index === idx;

                  return (
                    <div
                      key={idx}
                      className={clsx(
                        "p-3 rounded-xl border-2",
                        isCorrect
                          ? "border-lsc-rose bg-lsc-cream dark:bg-lsc-brown/20"
                          : isSelected && !isCorrect
                          ? "border-status-danger-400 bg-status-danger-50 dark:bg-status-danger-900/20"
                          : "border-lsc-border dark:border-earth-700"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={clsx(
                            "text-sm",
                            isCorrect
                              ? "text-lsc-rose dark:text-lsc-rose-light font-medium"
                              : isSelected && !isCorrect
                              ? "text-status-danger-700 dark:text-status-danger-300"
                              : "text-lsc-dark/70 dark:text-lsc-cream/70"
                          )}
                        >
                          {opt.text}
                        </span>
                        {isCorrect && (
                          <span className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">
                            Correct
                          </span>
                        )}
                        {isSelected && !isCorrect && (
                          <span className="text-xs font-medium text-status-danger-600 dark:text-status-danger-400">
                            Your answer
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {currentFeedback.explanation && (
                <div className="mt-4 p-4 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    <span className="font-medium">Explanation:</span>{" "}
                    {currentFeedback.explanation}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Review navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => setReviewIndex((i) => Math.max(0, i - 1))}
              disabled={reviewIndex === 0}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-xl transition-colors",
                reviewIndex === 0
                  ? "text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
              )}
            >
              <ChevronLeft aria-hidden="true" className="w-5 h-5" />
              Previous
            </button>

            <div className="flex gap-1">
              {result.feedback.map((f, idx) => (
                <button
                  key={f.question_id}
                  onClick={() => setReviewIndex(idx)}
                  className={clsx(
                    "w-8 h-8 rounded-xl text-sm font-medium transition-all",
                    idx === reviewIndex
                      ? "bg-lsc-rose text-white"
                      : f.correct
                      ? "bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-rose dark:text-lsc-rose-light"
                      : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300"
                  )}
                >
                  {idx + 1}
                </button>
              ))}
            </div>

            <button
              onClick={() => setReviewIndex((i) => Math.min(result.feedback.length - 1, i + 1))}
              disabled={reviewIndex === result.feedback.length - 1}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-xl transition-colors",
                reviewIndex === result.feedback.length - 1
                  ? "text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed"
                  : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
              )}
            >
              Next
              <ChevronRight aria-hidden="true" className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-center gap-4 mt-8">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-6 py-2.5 border-2 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/70 rounded-xl hover:border-lsc-rose hover:text-lsc-rose transition-colors"
          >
            <ArrowLeft aria-hidden="true" className="w-5 h-5" />
            Back to Lesson
          </button>
          {!result.passed && (
            <button
              onClick={startQuiz}
              className="flex items-center gap-2 px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
            >
              <RefreshCw aria-hidden="true" className="w-5 h-5" />
              Try Again
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}

export default QuizPlayer;
