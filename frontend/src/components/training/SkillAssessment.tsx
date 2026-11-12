/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react';
import { Plus, Trash2, GripVertical, Eye, Save, Loader2, ClipboardList } from 'lucide-react';
import type { SkillAssessmentQuestion } from './types';
import { skillsApi } from './api';
import { Modal } from '../ui/Modal';
import ConfirmDialog from '../ConfirmDialog';
import { useTranslation} from '@/i18n'

interface Props {
  isOpen: boolean;
  skillId: string | null;
  skillName: string | null;
  onClose: () => void;
  onSuccess: () => void;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

export const SkillAssessment: React.FC<Props> = ({
  isOpen,
  skillId,
  skillName,
  onClose,
  onSuccess,
  onShowToast,
}) => {
  const { t } = useTranslation()
  const [questions, setQuestions] = useState<SkillAssessmentQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  const [newQuestion, setNewQuestion] = useState<SkillAssessmentQuestion>({
    question: '',
    correct_answer: '',
    explanation: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showPreview, setShowPreview] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [deleteQuestionConfirm, setDeleteQuestionConfirm] = useState<{ index: number; question: string } | null>(null);

  const loadQuestions = React.useCallback(async () => {
    try {
      setInitialLoading(true);
      const data = await skillsApi.getQuestions(skillId!);
      setQuestions(data);
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to load questions';
      setErrors({ submit: errorMessage });
      onShowToast?.(errorMessage, 'error');
    } finally {
      setInitialLoading(false);
    }
  }, [skillId, onShowToast]);

  useEffect(() => {
    if (isOpen && skillId) {
      loadQuestions();
    }
  }, [isOpen, skillId, loadQuestions]);

  const validateQuestion = () => {
    const newErrors: Record<string, string> = {};

    if (!newQuestion.question.trim()) {
      newErrors.question = 'Question text is required';
    }

    if (!newQuestion.correct_answer.trim()) {
      newErrors.correct_answer = 'Correct answer is required';
    }

    if (!newQuestion.explanation.trim()) {
      newErrors.explanation = 'Explanation is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleAddQuestion = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateQuestion() || !skillId) {
      return;
    }

    try {
      setLoading(true);

      const savedQuestion = await skillsApi.addQuestion(skillId, {
        question: newQuestion.question.trim(),
        correct_answer: newQuestion.correct_answer.trim(),
        explanation: newQuestion.explanation.trim(),
      });

      setQuestions((prev) => [...prev, savedQuestion]);
      setNewQuestion({
        question: '',
        correct_answer: '',
        explanation: '',
      });
      setErrors({});
      onShowToast?.('Question added successfully', 'success');
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to add question';
      setErrors({ submit: errorMessage });
      onShowToast?.(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteQuestion = async (index: number) => {
    if (!skillId) {
      return;
    }

    try {
      const question = questions[index];
      if (question && question.id) {
        await skillsApi.deleteQuestion(skillId, question.id);
      }
      setQuestions((prev) => prev.filter((_, i) => i !== index));
      setDeleteQuestionConfirm(null);
      onShowToast?.('Question deleted', 'success');
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to delete question';
      onShowToast?.(errorMessage, 'error');
    }
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (targetIndex: number) => {
    if (draggedIndex === null || draggedIndex === targetIndex || !skillId) {
      return;
    }

    try {
      const newQuestions = [...questions];
      const removed = newQuestions.splice(draggedIndex, 1);
      if (removed.length === 0 || !removed[0]) {
        return;
      }
      newQuestions.splice(targetIndex, 0, removed[0]);

      setQuestions(newQuestions);

      const orderMap = newQuestions.reduce(
        (acc, q, i) => {
          if (q.id) {
            acc[q.id] = i;
          }
          return acc;
        },
        {} as Record<string, number>,
      );

      await skillsApi.reorderQuestions(skillId, orderMap);
      onShowToast?.('Questions reordered', 'success');
    } catch (_err) {
      const errorMessage = _err instanceof Error ? _err.message : 'Failed to reorder questions';
      onShowToast?.(errorMessage, 'error');
      loadQuestions();
    } finally {
      setDraggedIndex(null);
    }
  };

  if (!isOpen || !skillId) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Assessment Builder"
      size="2xl"
    >
      {/* Subtitle */}
      <div className="mb-6 pb-4 border-b border-lsc-border dark:border-earth-700">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{skillName}</p>
      </div>

      {/* Error message */}
      {errors.submit && (
        <div className="mb-6 rounded-xl border border-status-danger-300 bg-status-danger-50 p-4 text-status-danger-700 dark:border-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-200">
          {errors.submit}
        </div>
      )}

      {/* Preview Toggle */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setShowPreview(false)}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 font-medium transition-colors ${
            !showPreview
              ? 'bg-lsc-rose text-white dark:bg-lsc-rose-light'
              : 'border border-lsc-border text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:text-lsc-cream/80 dark:hover:bg-lsc-brown'
          }`}
        >
          <Plus aria-hidden="true" className="w-5 h-5" />
          Add Questions
        </button>
        <button
          onClick={() => setShowPreview(true)}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 font-medium transition-colors ${
            showPreview
              ? 'bg-lsc-rose text-white dark:bg-lsc-rose-light'
              : 'border border-lsc-border text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:text-lsc-cream/80 dark:hover:bg-lsc-brown'
          }`}
        >
          <Eye aria-hidden="true" className="w-5 h-5" />
          Preview
        </button>
      </div>

      {/* Add Question Form */}
      {!showPreview && (
        <form onSubmit={handleAddQuestion} className="mb-8 space-y-4 rounded-xl bg-lsc-cream dark:bg-lsc-brown/50 p-6">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Add New Question</h3>

          {/* Question */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
              Question *
            </label>
            <textarea
              value={newQuestion.question}
              onChange={(e) =>
                setNewQuestion((prev) => ({ ...prev, question: e.target.value }))
              }
              placeholder={t('placeholder.training.enterTheQuestion')}
              rows={3}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
            {errors.question && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.question}</p>
            )}
          </div>

          {/* Correct Answer */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
              Correct Answer *
            </label>
            <input
              type="text"
              value={newQuestion.correct_answer}
              onChange={(e) =>
                setNewQuestion((prev) => ({ ...prev, correct_answer: e.target.value }))
              }
              placeholder={t('components.training.skillAssessment.enterTheCorrectAnswer')}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
            {errors.correct_answer && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.correct_answer}</p>
            )}
          </div>

          {/* Explanation */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
              Explanation *
            </label>
            <textarea
              value={newQuestion.explanation}
              onChange={(e) =>
                setNewQuestion((prev) => ({ ...prev, explanation: e.target.value }))
              }
              placeholder={t('components.training.skillAssessment.explainWhyThisIsThe')}
              rows={3}
              className="mt-2 w-full rounded-xl border border-lsc-border bg-lsc-white px-4 py-2.5 text-lsc-dark placeholder-earth-500 dark:placeholder-earth-500 dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-status-warning-400"
            />
            {errors.explanation && (
              <p className="mt-1 text-sm text-status-danger-600 dark:text-status-danger-400">{errors.explanation}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-lsc-rose px-4 py-2.5 font-medium text-white hover:bg-lsc-rose disabled:opacity-50 dark:bg-sage-700 dark:hover:bg-lsc-rose transition-colors"
          >
            {loading ? 'Adding...' : 'Add Question'}
          </button>
        </form>
      )}

      {/* Questions List */}
      {initialLoading && !showPreview && (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
        </div>
      )}

      {!initialLoading && questions.length === 0 && !showPreview && (
        <div className="rounded-xl border-2 border-dashed border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50 p-12 text-center">
          <ClipboardList aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.training.skillAssessment.noQuestionsYetAddYour')}</p>
        </div>
      )}

      {!showPreview && questions.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Questions ({questions.length})
          </h3>
          {questions.map((question, index) => (
            <div
              key={index}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(index)}
              className={`rounded-xl border-2 p-4 ${
                draggedIndex === index
                  ? 'border-earth-500 bg-lsc-cream dark:bg-lsc-dark/20'
                  : 'border-lsc-border dark:border-earth-700'
              } cursor-move bg-lsc-white dark:bg-earth-800 transition`}
            >
              <div className="flex gap-4">
                <GripVertical aria-hidden="true" className="w-5 h-5 flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <div className="flex-1">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{question.question}</p>
                  <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="font-medium">Answer:</span> {question.correct_answer}
                  </p>
                </div>
                <button
                  onClick={() => setDeleteQuestionConfirm({ index, question: question.question })}
                  className="rounded-xl p-2 text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:text-status-danger-400 dark:hover:bg-lsc-brown transition-colors"
                  aria-label={t('aria.training.deleteQuestion')}
                >
                  <Trash2 className="w-5 h-5" aria-hidden="true" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Preview Mode */}
      {showPreview && (
        <div className="space-y-6">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Assessment Preview ({questions.length} questions)
          </h3>

          {questions.length === 0 && (
            <div className="rounded-xl border-2 border-dashed border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50 p-12 text-center">
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                No questions added yet. Add questions to create the assessment.
              </p>
            </div>
          )}

          {questions.map((question, index) => (
            <div key={index} className="space-y-2 rounded-xl border border-lsc-border bg-lsc-cream dark:border-earth-700 dark:bg-lsc-brown/50 p-6">
              <div className="flex items-start justify-between">
                <div className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  Question {index + 1} of {questions.length}
                </div>
                <span className="rounded-full bg-lsc-cream dark:bg-lsc-brown/30 px-3 py-1 text-xs font-medium text-lsc-rose dark:text-lsc-cream/70">
                  Short Answer
                </span>
              </div>

              <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{question.question}</p>

              <div className="my-4 rounded-xl border border-lsc-border bg-lsc-white p-4 dark:border-earth-700 dark:bg-earth-800">
                <input
                  type="text"
                  placeholder={t('components.training.skillAssessment.staffResponseWouldGoHere')}
                  className="w-full border-0 bg-transparent text-lsc-dark/70 placeholder-earth-500 dark:placeholder-earth-500 dark:text-lsc-cream/70"
                  disabled
                />
              </div>

              <details className="mt-4">
                <summary className="cursor-pointer font-medium text-lsc-rose hover:text-lsc-rose dark:text-lsc-rose-light dark:hover:text-brand-300">
                  Show Answer & Explanation
                </summary>
                <div className="mt-3 space-y-3 rounded-xl bg-lsc-white dark:bg-earth-800 p-4">
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">Correct Answer:</p>
                    <p className="text-lsc-dark dark:text-lsc-cream">{question.correct_answer}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">Explanation:</p>
                    <p className="text-lsc-dark dark:text-lsc-cream">{question.explanation}</p>
                  </div>
                </div>
              </details>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-8 flex gap-3 pt-6 border-t border-lsc-border dark:border-earth-700">
        <button
          onClick={onClose}
          className="flex-1 rounded-xl border border-lsc-border px-4 py-2.5 font-medium text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:text-lsc-cream/80 dark:hover:bg-lsc-brown transition-colors"
        >
          Close
        </button>
        <button
          onClick={() => {
            onSuccess();
            onClose();
          }}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-lsc-rose px-4 py-2.5 font-medium text-white hover:bg-lsc-rose dark:bg-lsc-rose-light dark:hover:bg-lsc-rose transition-colors"
        >
          <Save aria-hidden="true" className="w-5 h-5" />
          Done
        </button>
      </div>

      <ConfirmDialog
        isOpen={!!deleteQuestionConfirm}
        title="Delete Question?"
        message={`Are you sure you want to delete this question? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteQuestionConfirm) handleDeleteQuestion(deleteQuestionConfirm.index) }}
        onCancel={() => setDeleteQuestionConfirm(null)}
      />
    </Modal>
  );
};
