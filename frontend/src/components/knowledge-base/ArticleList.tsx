/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Eye, ThumbsUp, Bookmark } from 'lucide-react'
import api from '../../api/api';
import ArticleViewer from './ArticleViewer';
import { useTranslation } from '@/i18n'
import { useFocusAndAnnounce } from '@/hooks/useFocusAndAnnounce'
import toast from 'react-hot-toast'

interface Article {
  id: number;
  title: string;
  description: string;
  content_type: string;
  category: string;
  view_count: number;
  bookmark_count: number;
  helpful_count: number;
  created_at: string;
  updated_at?: string;
  last_verified_at?: string | null;
}

interface ArticleListProps {
  searchQuery: string;
}

const STALE_AFTER_MS = 365 * 24 * 60 * 60 * 1000;
function isStale(a: { last_verified_at?: string | null; updated_at?: string }): boolean {
  const ref = a.last_verified_at ?? a.updated_at;
  if (!ref) return false;
  return Date.now() - new Date(ref).getTime() > STALE_AFTER_MS;
}

export default function ArticleList({ searchQuery }: ArticleListProps) {
  const { t } = useTranslation()
  const [selectedArticle, setSelectedArticle] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const hasInteracted = useRef(false);
  const [announcement, setAnnouncement] = useState('');
  // Tracks whether the user has drilled into an article, so returning to the
  // list moves focus + announces (drill-out) without stealing focus on mount.
  // State (not a ref) so the drill-out gate can be read safely during render.
  const [hasOpenedArticle, setHasOpenedArticle] = useState(false);
  const listHeadingRef = useRef<HTMLHeadingElement>(null);

  const { data: articles, isLoading, error } = useQuery<Article[]>({
    queryKey: ['articles', searchQuery, selectedCategory, selectedType],
    queryFn: async () => {
      if (searchQuery.trim()) {
        const response = await api.get<{ results: Article[] }>('/staff-knowledge/articles/search', {
          params: { q: searchQuery },
        });
        return response.results;
      } else {
        return await api.get<Article[]>('/staff-knowledge/articles', {
          params: {
            category: selectedCategory || undefined,
            content_type: selectedType || undefined,
          },
        });
      }
    },
  });

  // Track when user initiates a search or filter change
  useEffect(() => {
    if (searchQuery || selectedCategory || selectedType) {
      hasInteracted.current = true;
    }
  }, [searchQuery, selectedCategory, selectedType]);

  // Announce results to screen readers after data loads (only for user-initiated actions)
  useEffect(() => {
    if (!hasInteracted.current || isLoading) return;
    if (!articles) return;

    if (articles.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- screen reader announcement requires setState from effect
      setAnnouncement(
        searchQuery
          ? `${t('components.knowledgeBase.articleList.noArticlesFound', 'No articles found')} ${t('components.knowledgeBase.articleList.for', 'for')} "${searchQuery}"`
          : t('components.knowledgeBase.articleList.noArticlesFound', 'No articles found')
      );
    } else {
      const noun = articles.length === 1
        ? t('components.knowledgeBase.articleList.article', 'article')
        : t('components.knowledgeBase.articleList.articles', 'articles');
      setAnnouncement(`${articles.length} ${noun} ${t('components.knowledgeBase.articleList.found', 'found')}`);
    }
  }, [articles, isLoading, searchQuery, t]);

  const categories = [
    'Circulation',
    'Patron Services',
    'Cataloging',
    'Reference',
    'Technology',
    'Staff Management',
    'Safety & Security',
    'Facilities',
  ];

  const contentTypes = [
    { value: 'policy', label: 'Policies' },
    { value: 'procedure', label: 'Procedures' },
    { value: 'how_to', label: 'How-To Guides' },
    { value: 'faq', label: 'FAQs' },
  ];

  // Drill-out: when returning from the viewer to the list, move focus to the
  // list heading and announce. Gated on hasOpenedArticle so it never fires on
  // the initial mount or on filter/search changes.
  useFocusAndAnnounce(
    listHeadingRef,
    t('components.knowledgeBase.articleList.backToArticleList', 'Back to article list'),
    selectedArticle,
    selectedArticle === null && hasOpenedArticle,
  );

  const openArticle = (id: number) => {
    setHasOpenedArticle(true);
    setSelectedArticle(id);
  };

  if (selectedArticle) {
    return (
      <ArticleViewer
        articleId={selectedArticle}
        onBack={() => setSelectedArticle(null)}
      />
    );
  }

  return (
    <>
    <div aria-live="polite" aria-atomic="true" className="sr-only">
      {announcement}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Sidebar Filters */}
      <div className="lg:col-span-1">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 sticky top-20">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('components.knowledgeBase.articleList.filters', 'Filters')}</h2>

          {/* Category Filter */}
          <div className="mb-6">
            <label className="text-sm font-medium text-earth-600 dark:text-earth-400 block mb-2">
              {t('components.knowledgeBase.articleList.category', 'Category')}
            </label>
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              aria-label={t('components.knowledgeBase.articleList.filterByCategory', 'Filter by category')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
            >
              <option value="">{t('components.knowledgeBase.articleList.allCategories', 'All Categories')}</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          {/* Content Type Filter */}
          <div className="mb-6">
            <label className="text-sm font-medium text-earth-600 dark:text-earth-400 block mb-2">
              {t('components.knowledgeBase.articleList.contentType', 'Content Type')}
            </label>
            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value)}
              aria-label={t('components.knowledgeBase.articleList.filterByType', 'Filter by type')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
            >
              <option value="">{t('components.knowledgeBase.articleList.allTypes', 'All Types')}</option>
              {contentTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Articles */}
      <div className="lg:col-span-3">
        {/* Focus target for drill-out from the article viewer (visually hidden). */}
        <h2 ref={listHeadingRef} tabIndex={-1} className="sr-only">
          {t('components.knowledgeBase.articleList.articleListHeading', 'Articles')}
        </h2>
        {isLoading && (
          <div className="text-center py-12" role="status">
            <div className="inline-block motion-safe:animate-spin rounded-full h-8 w-8 border-b-2 border-lsc-rose"></div>
            <p className="mt-4 text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleList.loadingArticles', 'Loading articles...')}</p>
          </div>
        )}

        {error && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4 text-status-danger-800 dark:text-status-danger-300">
            {t('components.knowledgeBase.articleList.errorLoadingArticles', 'Error loading articles. Please try again.')}
          </div>
        )}

        {articles && articles.length === 0 && (
          <div className="text-center py-12 bg-earth-50 dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700">
            <p className="text-earth-600 dark:text-earth-400">{t('components.knowledgeBase.articleList.noArticlesFoundTryAdjusting')}</p>
          </div>
        )}

        <div className="space-y-4">
          {articles?.map((article: Article) => (
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
                    {isStale(article) && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/40 dark:text-status-warning-200">
                        {t('components.knowledgeBase.articleList.needsReview', 'Needs review')}
                      </span>
                    )}
                  </div>
                  <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                    <button
                      type="button"
                      onClick={() => openArticle(article.id)}
                      aria-label={`${t('components.knowledgeBase.articleList.openArticle', 'Open article')}: ${article.title}`}
                      className="block w-full text-left truncate hover:text-lsc-rose cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose dark:focus-visible:ring-lsc-rose-light rounded"
                      title={article.title}
                    >
                      {article.title}
                    </button>
                  </h2>
                  {article.description && (
                    <p className="text-earth-600 dark:text-earth-400 text-sm line-clamp-2" title={article.description}>
                      {article.description}
                    </p>
                  )}
                </div>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-6 mt-4 pt-4 border-t border-earth-100 dark:border-earth-700 text-sm text-earth-600 dark:text-earth-400">
                <div className="flex items-center gap-1">
                  <Eye className="w-4 h-4" aria-hidden="true" />
                  {`${article.view_count} ${t('components.knowledgeBase.articleList.views', 'views')}`}
                </div>
                <div className="flex items-center gap-1">
                  <ThumbsUp className="w-4 h-4" aria-hidden="true" />
                  {`${article.helpful_count} ${t('components.knowledgeBase.articleList.helpful', 'helpful')}`}
                </div>
                <div className="flex items-center gap-1">
                  <Bookmark className="w-4 h-4" aria-hidden="true" />
                  {`${article.bookmark_count} ${t('components.knowledgeBase.articleList.bookmarks', 'bookmarks')}`}
                </div>
              </div>
              <div className="mt-3 flex items-center justify-end">
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await api.post("/staff-knowledge/flags", {
                        article_id: article.id,
                        reason: "outdated",
                        description: t("components.knowledgeBase.articleList.outdatedReason", "Flagged as outdated from the article list."),
                      })
                      toast.success(t("components.knowledgeBase.articleList.flaggedSuccess", "Article flagged for review"))
                    } catch {
                      toast.error(t("components.knowledgeBase.articleList.flaggedError", "Failed to flag article"))
                    }
                  }}
                  className="text-xs text-earth-600 dark:text-earth-400 hover:text-lsc-rose dark:hover:text-lsc-rose-light underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded"
                >
                  {t("components.knowledgeBase.articleList.flagOutdated", "Flag as outdated")}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
    </>
  );
}
