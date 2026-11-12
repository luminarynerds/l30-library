/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ThumbsUp, MessageSquare, X, Send, Search } from 'lucide-react';
import api from '../../api/api';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';
import { useTranslation} from '@/i18n'

interface Question {
  id: number;
  question: string;
  category: string;
  tags: string;
  asked_by_id: number;
  is_answered: boolean;
  is_closed: boolean;
  answer: string | null;
  answered_by_id: number | null;
  answer_upvotes: number;
  created_at: string;
  answered_at: string | null;
}

export default function StaffQA() {
  const { t } = useTranslation()
  const [showNewQuestion, setShowNewQuestion] = useState(false);
  const [newQuestion, setNewQuestion] = useState('');
  const [newCategory, setNewCategory] = useState('General');
  const [filterAnswered, setFilterAnswered] = useState(false);
  const [answeringId, setAnsweringId] = useState<number | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const newQuestionRef = useRef<HTMLTextAreaElement>(null);
  const answerRef = useRef<HTMLTextAreaElement>(null);

  // Move focus into the reveal so keyboard/SR users land on the form, not stay
  // on a now-expanded toggle with no visible focus change.
  useEffect(() => {
    if (showNewQuestion) newQuestionRef.current?.focus();
  }, [showNewQuestion]);
  useEffect(() => {
    if (answeringId !== null) answerRef.current?.focus();
  }, [answeringId]);

  const isStaff = user?.role === 'staff' || user?.role === 'admin' || user?.role === 'super_admin';

  const { data: questions, isLoading } = useQuery({
    queryKey: ['staff-qa', filterAnswered],
    queryFn: async () => {
      return await api.get<Question[]>('/staff-knowledge/qa', {
        params: { answered_only: filterAnswered },
      });
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      await api.post('/staff-knowledge/qa', {
        question: newQuestion,
        category: newCategory,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-qa'] });
      setNewQuestion('');
      setNewCategory('General');
      setShowNewQuestion(false);
      toast.success(t('toast.knowledge-base.questionPostedSuccessfully'));
    },
    onError: () => {
      toast.error(t('components.knowledgeBase.staffQA.failedToPostQuestion'));
    },
  });

  const answerMutation = useMutation({
    mutationFn: async ({ qaId, answer }: { qaId: number; answer: string }) => {
      await api.post(`/staff-knowledge/qa/${qaId}/answer`, { answer });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-qa'] });
      setAnsweringId(null);
      setAnswerText('');
      toast.success(t('toast.knowledge-base.answerSubmitted'));
    },
    onError: () => {
      toast.error(t('components.knowledgeBase.staffQA.failedToSubmitAnswer'));
    },
  });

  const upvoteMutation = useMutation({
    mutationFn: async (qaId: number) => {
      await api.post(`/staff-knowledge/qa/${qaId}/upvote`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-qa'] });
    },
  });

  const categories = [
    'General',
    'Circulation',
    'Patron Services',
    'Cataloging',
    'Technology',
    'Staff Management',
    'Policies & Procedures',
    'Safety & Security',
    'Facilities',
    'Reference',
  ];

  const filteredQuestions = questions?.filter(q => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      q.question.toLowerCase().includes(query) ||
      q.category.toLowerCase().includes(query) ||
      (q.answer && q.answer.toLowerCase().includes(query))
    );
  });

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
        <span className="sr-only">{t('common.loading', 'Loading...')}</span>
      </div>
    );
  }

  return (
    <div>
      {/* Controls */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <button
          onClick={() => setShowNewQuestion(!showNewQuestion)}
          aria-expanded={showNewQuestion}
          aria-controls="staff-qa-new-question-form"
          className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition flex items-center gap-2"
        >
          <MessageSquare className="w-4 h-4" />
          {t('components.knowledgeBase.staffQA.askAQuestion', 'Ask a Question')}
        </button>

        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-earth-600" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={t('components.knowledgeBase.staffQA.searchQuestionsAndAnswers')}
            aria-label={t('aria.knowledge-base.searchQuestions')}
            className="w-full pl-9 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setFilterAnswered(false)}
            aria-pressed={!filterAnswered}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition ${
              !filterAnswered
                ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light border border-lsc-border dark:border-earth-700'
                : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 border border-lsc-border dark:border-earth-700'
            }`}
          >
            {t('components.knowledgeBase.staffQA.filterAll', 'All')}
          </button>
          <button
            onClick={() => setFilterAnswered(true)}
            aria-pressed={filterAnswered}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition ${
              filterAnswered
                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 border border-status-success-200 dark:border-status-success-800'
                : 'bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 border border-lsc-border dark:border-earth-700'
            }`}
          >
            {t('components.knowledgeBase.staffQA.filterAnswered', 'Answered')}
          </button>
        </div>
      </div>

      {/* New Question Form */}
      {showNewQuestion && (
        <div id="staff-qa-new-question-form" className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('components.knowledgeBase.staffQA.askAQuestion', 'Ask a Question')}</h3>
            <button
              onClick={() => setShowNewQuestion(false)}
              aria-label={t('components.knowledgeBase.staffQA.closeForm', 'Close form')}
              className="text-earth-600 dark:text-earth-400 hover:text-earth-800 dark:hover:text-earth-300"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label htmlFor="staff-qa-category" className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                {t('components.knowledgeBase.staffQA.category', 'Category')}
              </label>
              <select
                id="staff-qa-category"
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="staff-qa-question" className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                {t('components.knowledgeBase.staffQA.question', 'Question')}
              </label>
              <textarea
                id="staff-qa-question"
                ref={newQuestionRef}
                value={newQuestion}
                onChange={e => setNewQuestion(e.target.value)}
                placeholder={t('components.knowledgeBase.staffQA.whatDoYouNeedHelp')}
                rows={4}
                aria-describedby="staff-qa-question-help"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              />
              <p id="staff-qa-question-help" className="mt-1 text-xs text-earth-600 dark:text-earth-400">
                {t('components.knowledgeBase.staffQA.minLengthHelp', 'Please enter at least 10 characters before posting.')}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => createMutation.mutate()}
                disabled={!newQuestion.trim() || newQuestion.trim().length < 10 || createMutation.isPending}
                className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg font-medium transition"
              >
                {t('components.knowledgeBase.staffQA.postQuestion', 'Post Question')}
              </button>
              <button
                onClick={() => setShowNewQuestion(false)}
                className="px-4 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 text-earth-600 dark:text-earth-400 rounded-lg font-medium transition"
              >
                {t('components.knowledgeBase.staffQA.cancel', 'Cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Questions List */}
      <div className="space-y-4">
        {!filteredQuestions || filteredQuestions.length === 0 ? (
          <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
            <MessageSquare className="w-12 h-12 text-earth-600 dark:text-earth-400 mx-auto mb-3" />
            <p className="text-earth-600 dark:text-earth-400">
              {searchQuery
                ? t('components.knowledgeBase.staffQA.noQuestionsMatchingSearch', 'No questions matching your search.')
                : filterAnswered
                  ? t('components.knowledgeBase.staffQA.noAnsweredQuestionsYet', 'No answered questions yet.')
                  : t('components.knowledgeBase.staffQA.noQuestionsYet', 'No questions yet. Be the first to ask!')}
            </p>
          </div>
        ) : (
          filteredQuestions.map(q => (
            <div
              key={q.id}
              className={`border rounded-lg p-6 ${
                q.is_answered
                  ? 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800'
                  : 'bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700'
              }`}
            >
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {q.question}
                  </h4>
                  {q.is_answered && (
                    <span className="px-3 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 text-xs font-medium rounded-full flex-shrink-0 ml-2">
                      {t('components.knowledgeBase.staffQA.answered', 'Answered')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-sm text-earth-600 dark:text-earth-400">
                  <span className="bg-earth-100 dark:bg-earth-700 px-2 py-1 rounded">
                    {q.category}
                  </span>
                  <span>
                    {new Date(q.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {q.is_answered && q.answer && (
                <div className="bg-lsc-white dark:bg-earth-800 border border-status-success-200 dark:border-status-success-800 rounded-lg p-4 mb-4">
                  <h5 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('components.knowledgeBase.staffQA.answerLabel', 'Answer:')}</h5>
                  <p className="text-earth-600 dark:text-earth-400 mb-3 whitespace-pre-wrap">{q.answer}</p>
                  {q.answered_at && (
                    <p className="text-xs text-earth-600 dark:text-earth-400 mb-3">
                      {`${t('components.knowledgeBase.staffQA.answeredOn', 'Answered on')} ${new Date(q.answered_at).toLocaleDateString()}`}
                    </p>
                  )}
                  <button
                    onClick={() => upvoteMutation.mutate(q.id)}
                    className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light hover:opacity-80 font-medium text-sm"
                  >
                    <ThumbsUp className="w-4 h-4" />
                    {`${t('components.knowledgeBase.staffQA.helpful', 'Helpful')} (${q.answer_upvotes})`}
                  </button>
                </div>
              )}

              {/* Answer form for unanswered questions (staff only) */}
              {!q.is_answered && isStaff && answeringId === q.id && (
                <div id={`staff-qa-answer-form-${q.id}`} className="bg-status-success-50 dark:bg-status-success-900/10 border border-status-success-200 dark:border-status-success-800 rounded-lg p-4 mb-4">
                  <h5 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
                    <Send className="w-4 h-4 text-status-success-600" />
                    {t('components.knowledgeBase.staffQA.writeYourAnswer', 'Write Your Answer')}
                  </h5>
                  <textarea
                    ref={answerRef}
                    value={answerText}
                    onChange={e => setAnswerText(e.target.value)}
                    placeholder={t('components.knowledgeBase.staffQA.shareYourKnowledgeWithYour')}
                    rows={4}
                    aria-describedby={`staff-qa-answer-help-${q.id}`}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-status-success-500 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream mb-1"
                  />
                  <p id={`staff-qa-answer-help-${q.id}`} className="mb-3 text-xs text-earth-600 dark:text-earth-400">
                    {t('components.knowledgeBase.staffQA.minLengthHelp', 'Please enter at least 10 characters before posting.')}
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => answerMutation.mutate({ qaId: q.id, answer: answerText })}
                      disabled={!answerText.trim() || answerText.trim().length < 10 || answerMutation.isPending}
                      className="px-4 py-2 bg-status-success-600 hover:bg-status-success-700 disabled:bg-earth-400 text-white rounded-lg font-medium transition flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      {t('components.knowledgeBase.staffQA.submitAnswer', 'Submit Answer')}
                    </button>
                    <button
                      onClick={() => { setAnsweringId(null); setAnswerText(''); }}
                      className="px-4 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 text-earth-600 dark:text-earth-400 rounded-lg font-medium transition"
                    >
                      {t('components.knowledgeBase.staffQA.cancel', 'Cancel')}
                    </button>
                  </div>
                </div>
              )}

              {!q.is_answered && isStaff && answeringId !== q.id && (
                <button
                  onClick={() => { setAnsweringId(q.id); setAnswerText(''); }}
                  className="w-full py-3 bg-status-success-50 dark:bg-status-success-900/20 hover:bg-status-success-100 dark:hover:bg-status-success-900/30 border border-status-success-200 dark:border-status-success-800 rounded-lg text-status-success-700 dark:text-status-success-300 font-medium text-sm transition flex items-center justify-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  {t('components.knowledgeBase.staffQA.answerThisQuestion', 'Answer This Question')}
                </button>
              )}

              {!q.is_answered && !isStaff && (
                <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 text-center text-earth-800 dark:text-lsc-rose-light">
                  <p className="text-sm font-medium">{t('components.knowledgeBase.staffQA.awaitingAnswerFromAColleague')}</p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
