/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Eye, ThumbsUp, Trash2 } from 'lucide-react';
import api from '../../api/api';
import ArticleViewer from './ArticleViewer';
import toast from 'react-hot-toast';
import { useTranslation} from '@/i18n'
import { useFocusAndAnnounce } from '@/hooks/useFocusAndAnnounce'

interface Article {
  id: number;
  title: string;
  description: string;
  content_type: string;
  category: string;
  view_count: number;
  helpful_count: number;
  created_at: string;
}

export default function BookmarkedArticles() {
  const { t } = useTranslation()
  const [selectedArticle, setSelectedArticle] = useState<number | null>(null);
  const queryClient = useQueryClient();
  // Drill-out focus management (see ArticleList for the same pattern).
  const [hasOpenedArticle, setHasOpenedArticle] = useState(false);
  const listHeadingRef = useRef<HTMLHeadingElement>(null);

  useFocusAndAnnounce(
    listHeadingRef,
    t('components.knowledgeBase.bookmarkedArticles.backToBookmarks', 'Back to bookmarks'),
    selectedArticle,
    selectedArticle === null && hasOpenedArticle,
  );

  const openArticle = (id: number) => {
    setHasOpenedArticle(true);
    setSelectedArticle(id);
  };

  const { data: articles, isLoading } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: async () => {
      return await api.get<Article[]>('/staff-knowledge/bookmarks');
    },
  });

  const removeBookmarkMutation = useMutation({
    mutationFn: async (articleId: number) => {
      await api.delete(`/staff-knowledge/bookmarks/${articleId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookmarks'] });
      toast.success(t('toast.knowledge-base.bookmarkRemovedSuccessfully'));
    },
    onError: (error: Error) => {
      toast.error(error?.message || t('toast.knowledge-base.failedToRemoveBookmark'));
    },
  });

  if (selectedArticle) {
    return (
      <ArticleViewer
        articleId={selectedArticle}
        onBack={() => setSelectedArticle(null)}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-12" role="status">
        <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
        <span className="sr-only">{t('components.knowledgeBase.bookmarkedArticles.loading', 'Loading bookmarks...')}</span>
      </div>
    );
  }

  if (!articles || articles.length === 0) {
    return (
      <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
        <p className="text-earth-600 dark:text-earth-400 mb-4">{t('components.knowledgeBase.bookmarkedArticles.noBookmarkedArticlesYet')}</p>
        <p className="text-sm text-earth-600 dark:text-earth-400">
          {t('components.knowledgeBase.bookmarkedArticles.emptyHint', 'Visit the Articles section and click the bookmark icon on any article to save it here.')}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 ref={listHeadingRef} tabIndex={-1} className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6 outline-none">
        {`${t('components.knowledgeBase.bookmarkedArticles.heading', 'Bookmarked Articles')} (${articles.length})`}
      </h2>

      {articles.map(article => (
        <div
          key={article.id}
          className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-5 hover:shadow-lg transition"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2 py-1 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light text-xs font-medium rounded">
                  {article.content_type.replace('_', ' ')}
                </span>
                <span className="px-2 py-1 bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100 text-xs font-medium rounded">
                  {article.category}
                </span>
              </div>
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                <button
                  type="button"
                  onClick={() => openArticle(article.id)}
                  aria-label={`${t('components.knowledgeBase.bookmarkedArticles.openArticle', 'Open article')}: ${article.title}`}
                  className="block w-full text-left truncate hover:text-lsc-rose cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-lsc-rose-light rounded"
                  title={article.title}
                >
                  {article.title}
                </button>
              </h3>
              {article.description && (
                <p className="text-earth-600 dark:text-earth-400 text-sm line-clamp-2" title={article.description}>
                  {article.description}
                </p>
              )}
            </div>

            <button
              type="button"
              onClick={() => removeBookmarkMutation.mutate(article.id)}
              disabled={removeBookmarkMutation.isPending}
              className="flex-shrink-0 p-2 text-earth-600 dark:text-earth-400 hover:text-status-danger-600 hover:bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
              aria-label={t('components.knowledgeBase.bookmarkedArticles.removeBookmark', 'Remove bookmark')}
            >
              <Trash2 className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-earth-100 dark:border-earth-700 text-sm text-earth-600 dark:text-earth-400">
            <div className="flex items-center gap-1">
              <Eye className="w-4 h-4" aria-hidden="true" />
              {`${article.view_count} ${t('components.knowledgeBase.bookmarkedArticles.views', 'views')}`}
            </div>
            <div className="flex items-center gap-1">
              <ThumbsUp className="w-4 h-4" aria-hidden="true" />
              {`${article.helpful_count} ${t('components.knowledgeBase.bookmarkedArticles.helpful', 'helpful')}`}
            </div>
            <div className="text-xs text-earth-600 dark:text-earth-400 ml-auto">
              {`${t('components.knowledgeBase.bookmarkedArticles.addedOn', 'Added on')} ${new Date(article.created_at).toLocaleDateString()}`}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
