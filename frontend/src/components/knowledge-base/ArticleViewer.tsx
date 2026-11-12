/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useMemo, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Bookmark, Flag, ThumbsUp, ThumbsDown, History, AlertCircle, Clock, Volume2, Square } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../api/api';
import { useTranslation } from '@/i18n'
import { MarkdownContent } from '../learning/MarkdownContent'
import { useFocusAndAnnounce } from '@/hooks/useFocusAndAnnounce'

interface ArticleViewerProps {
  articleId: number;
  onBack: () => void;
}

interface Article {
  id: number;
  title: string;
  description: string;
  content: string;
  summary?: string;
  transcript?: string;
  content_type: string;
  category: string;
  subcategory: string;
  current_version: number;
  view_count: number;
  bookmark_count: number;
  helpful_count: number;
  unhelpful_count: number;
  created_at: string;
  updated_at: string;
  versions: Version[];
}

interface Version {
  id: number;
  version_number: number;
  title: string;
  change_notes: string;
  created_at: string;
}

// Average adult reading speed, used for the estimated reading-time aid.
const WORDS_PER_MINUTE = 200;

// Strip common markdown syntax so the speech-synthesis voice does not read out
// '#', '*', backticks, link/image brackets, etc. Intentionally lightweight.
function stripMarkdown(text: string): string {
  return text
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1') // images / links -> label text
    .replace(/`{1,3}([^`]*)`{1,3}/g, '$1') // inline / fenced code
    .replace(/^\s{0,3}#{1,6}\s+/gm, '') // ATX headings
    .replace(/^\s{0,3}>\s?/gm, '') // blockquotes
    .replace(/[*_~]{1,3}/g, '') // emphasis / strikethrough markers
    .replace(/^\s*[-*+]\s+/gm, '') // unordered list bullets
    .replace(/\|/g, ' ') // table pipes
    .replace(/\s+/g, ' ')
    .trim();
}

const speechSupported =
  typeof window !== 'undefined' && 'speechSynthesis' in window;

export default function ArticleViewer({ articleId, onBack }: ArticleViewerProps) {
  const { t } = useTranslation()
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showFlagForm, setShowFlagForm] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [flagReason, setFlagReason] = useState('');
  const [flagDescription, setFlagDescription] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  const { data: article, isLoading } = useQuery({
    queryKey: ['article', articleId],
    queryFn: async () => {
      return await api.get<Article>(`/staff-knowledge/articles/${articleId}`);
    },
  });

  // Move focus to the article heading and announce the view change to
  // screen readers once the article has loaded (shared drill-in primitive).
  useFocusAndAnnounce(
    headingRef,
    article ? `${t('components.knowledgeBase.articleViewer.openedArticle', 'Opened article')}: ${article.title}` : '',
    article?.id,
  );

  // Estimated reading time from the article body.
  const readingMinutes = useMemo(() => {
    const words = (article?.content ?? '').trim().split(/\s+/).filter(Boolean).length;
    return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
  }, [article?.content]);

  // Stop any in-progress speech when leaving the article.
  useEffect(() => {
    return () => {
      if (speechSupported) window.speechSynthesis.cancel();
    };
  }, []);

  const toggleSpeech = () => {
    if (!speechSupported || !article) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    const text = [article.title, article.summary, stripMarkdown(article.content)]
      .filter(Boolean)
      .join('. ');
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const bookmarkMutation = useMutation({
    mutationFn: async () => {
      if (isBookmarked) {
        await api.delete(`/staff-knowledge/bookmarks/${articleId}`);
      } else {
        await api.post('/staff-knowledge/bookmarks', { article_id: articleId });
      }
    },
    onSuccess: () => setIsBookmarked(!isBookmarked),
  });

  const flagMutation = useMutation({
    mutationFn: async () => {
      await api.post('/staff-knowledge/flags', {
        article_id: articleId,
        reason: flagReason,
        description: flagDescription,
      });
    },
    onSuccess: () => {
      setShowFlagForm(false);
      setFlagReason('');
      setFlagDescription('');
      toast.success(t('toast.knowledge-base.contentFlaggedForReview', 'Content flagged for review. Thank you!'));
    },
  });

  const helpfulMutation = useMutation({
    mutationFn: async (helpful: boolean) => {
      await api.post(`/staff-knowledge/articles/${articleId}/helpful?helpful=${helpful}`);
    },
  });

  const handleBack = () => {
    if (speechSupported) window.speechSynthesis.cancel();
    onBack();
  };

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
        <span className="sr-only">{t('components.knowledgeBase.articleViewer.loadingArticle', 'Loading article...')}</span>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4 text-status-danger-800 dark:text-status-danger-300">
        {t('components.knowledgeBase.articleViewer.articleNotFound', 'Article not found.')}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          type="button"
          onClick={handleBack}
          aria-label={t('components.knowledgeBase.articleViewer.backToArticles', 'Back to articles')}
          className="p-2 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
        >
          <ArrowLeft className="w-6 h-6 text-earth-600 dark:text-earth-400" aria-hidden="true" />
        </button>
        <h2 ref={headingRef} tabIndex={-1} className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream outline-none">{article.title}</h2>
      </div>

      {/* Metadata */}
      <div className="bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-4 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleViewer.category', 'Category')}</p>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{article.category}</p>
          </div>
          <div>
            <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleViewer.type', 'Type')}</p>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">{article.content_type.replace('_', ' ')}</p>
          </div>
          <div>
            <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleViewer.version', 'Version')}</p>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">v{article.current_version}</p>
          </div>
          <div>
            <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleViewer.lastUpdated', 'Last Updated')}</p>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
              {new Date(article.updated_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Reading aids: estimated time + Listen (TTS) */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <span className="inline-flex items-center gap-1.5 text-sm text-earth-600 dark:text-earth-400">
          <Clock className="w-4 h-4" aria-hidden="true" />
          {`${readingMinutes} ${t('components.knowledgeBase.articleViewer.minRead', 'min read')}`}
        </span>
        {speechSupported && (
          <button
            type="button"
            onClick={toggleSpeech}
            aria-pressed={isSpeaking}
            aria-label={
              isSpeaking
                ? t('components.knowledgeBase.articleViewer.stopReading', 'Stop reading aloud')
                : t('components.knowledgeBase.articleViewer.listen', 'Listen to this article')
            }
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
          >
            {isSpeaking ? (
              <Square className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Volume2 className="w-4 h-4" aria-hidden="true" />
            )}
            {isSpeaking
              ? t('components.knowledgeBase.articleViewer.stop', 'Stop')
              : t('components.knowledgeBase.articleViewer.listenShort', 'Listen')}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-8 mb-6">
        {/* Plain-language TL;DR summary (surfaced only when the backend provides it) */}
        {article.summary && (
          <div className="mb-6 rounded-lg border-l-4 border-lsc-rose bg-earth-50 dark:bg-earth-900 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-earth-600 dark:text-earth-400 mb-1">
              {t('components.knowledgeBase.articleViewer.summary', 'In short')}
            </p>
            <p className="text-lsc-dark dark:text-lsc-cream">{article.summary}</p>
          </div>
        )}
        {article.description && (
          <p className="text-earth-600 dark:text-earth-400 mb-6 text-lg">{article.description}</p>
        )}
        <MarkdownContent
          content={article.content}
          className="prose prose-sm max-w-none text-lsc-dark dark:text-lsc-cream dark:prose-invert"
        />
      </div>

      {/* Actions */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 mb-6">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('components.knowledgeBase.articleViewer.foundThisHelpful', 'Found this helpful?')}</h3>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => helpfulMutation.mutate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-status-success-50 dark:bg-status-success-900/20 hover:bg-status-success-100 border border-status-success-200 dark:border-status-success-800 rounded-lg text-status-success-700 dark:text-status-success-300 font-medium transition"
          >
            <ThumbsUp className="w-4 h-4" aria-hidden="true" />
            {`${t('components.knowledgeBase.articleViewer.yes', 'Yes')} (${article.helpful_count})`}
          </button>
          <button
            type="button"
            onClick={() => helpfulMutation.mutate(false)}
            className="flex items-center gap-2 px-4 py-2 bg-status-danger-50 dark:bg-status-danger-900/20 hover:bg-status-danger-100 border border-status-danger-200 dark:border-status-danger-800 rounded-lg text-status-danger-700 dark:text-status-danger-300 font-medium transition"
          >
            <ThumbsDown className="w-4 h-4" aria-hidden="true" />
            {`${t('components.knowledgeBase.articleViewer.no', 'No')} (${article.unhelpful_count})`}
          </button>
          <button
            type="button"
            onClick={() => bookmarkMutation.mutate()}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
              isBookmarked
                ? 'bg-status-warning-100 dark:bg-status-warning-900/30 hover:bg-status-warning-200 border border-status-warning-300 dark:border-status-warning-700 text-status-warning-700 dark:text-status-warning-300'
                : 'bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 border border-lsc-border dark:border-earth-700 text-earth-600 dark:text-earth-300'
            }`}
          >
            <Bookmark className="w-4 h-4" aria-hidden="true" />
            {isBookmarked
              ? t('components.knowledgeBase.articleViewer.bookmarked', 'Bookmarked')
              : t('components.knowledgeBase.articleViewer.bookmark', 'Bookmark')}
          </button>
          <button
            type="button"
            onClick={() => setShowFlagForm(!showFlagForm)}
            aria-expanded={showFlagForm}
            aria-controls="article-flag-form"
            className="flex items-center gap-2 px-4 py-2 bg-status-warning-50 dark:bg-status-warning-900/20 hover:bg-status-warning-100 border border-status-warning-200 dark:border-status-warning-800 rounded-lg text-status-warning-700 dark:text-status-warning-300 font-medium transition"
          >
            <Flag className="w-4 h-4" aria-hidden="true" />
            {t('components.knowledgeBase.articleViewer.flag', 'Flag')}
          </button>
        </div>
      </div>

      {/* Flag Form */}
      {showFlagForm && (
        <div id="article-flag-form" className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-6 mb-6">
          <div className="flex items-center gap-2 mb-4 text-status-warning-800 dark:text-status-warning-300">
            <AlertCircle className="w-5 h-5" aria-hidden="true" />
            <h4 className="font-serif font-semibold">{t('components.knowledgeBase.articleViewer.flagForReview', 'Flag for Review')}</h4>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                {t('components.knowledgeBase.articleViewer.reason', 'Reason')}
              </label>
              <select
                value={flagReason}
                onChange={e => setFlagReason(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500 dark:bg-earth-800 dark:text-earth-50"
              >
                <option value="">{t('components.knowledgeBase.articleViewer.selectAReason', 'Select a reason...')}</option>
                <option value="outdated">{t('components.knowledgeBase.articleViewer.reasonOutdated', 'Outdated Information')}</option>
                <option value="incorrect">{t('components.knowledgeBase.articleViewer.reasonIncorrect', 'Incorrect Information')}</option>
                <option value="unclear">{t('components.knowledgeBase.articleViewer.reasonUnclear', 'Unclear or Confusing')}</option>
                <option value="incomplete">{t('components.knowledgeBase.articleViewer.reasonIncomplete', 'Incomplete')}</option>
                <option value="other">{t('components.knowledgeBase.articleViewer.reasonOther', 'Other')}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-earth-600 dark:text-earth-400 mb-1">
                {t('components.knowledgeBase.articleViewer.description', 'Description')}
              </label>
              <textarea
                value={flagDescription}
                onChange={e => setFlagDescription(e.target.value)}
                placeholder={t('components.knowledgeBase.articleViewer.pleaseDescribeTheIssue')}
                rows={4}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-status-warning-500 dark:bg-earth-800 dark:text-earth-50"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => flagMutation.mutate()}
                disabled={!flagReason || !flagDescription || flagMutation.isPending}
                className="px-4 py-2 bg-status-warning-600 hover:bg-status-warning-700 disabled:bg-earth-400 text-white rounded-lg font-medium transition"
              >
                {t('components.knowledgeBase.articleViewer.submitFlag', 'Submit Flag')}
              </button>
              <button
                type="button"
                onClick={() => setShowFlagForm(false)}
                className="px-4 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition"
              >
                {t('components.knowledgeBase.articleViewer.cancel', 'Cancel')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Version History */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
        <button
          type="button"
          onClick={() => setShowVersionHistory(!showVersionHistory)}
          aria-expanded={showVersionHistory}
          aria-controls="article-version-history"
          className="flex items-center gap-2 font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose transition focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded"
        >
          <History className="w-5 h-5" aria-hidden="true" />
          {t('components.knowledgeBase.articleViewer.versionHistory', 'Version History')}
        </button>

        {showVersionHistory && article.versions && (
          <div id="article-version-history" className="mt-4 space-y-3">
            {article.versions.map(version => (
              <div key={version.id} className="border-l-4 border-lsc-border dark:border-earth-600 pl-4 py-2">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream">v{version.version_number}</span>
                  <span className="text-sm text-earth-600 dark:text-earth-400">
                    {new Date(version.created_at).toLocaleDateString()}
                  </span>
                </div>
                {version.change_notes && (
                  <p className="text-sm text-earth-600 dark:text-earth-400">{version.change_notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
