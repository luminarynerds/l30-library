/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'
import { Scale, Search, Star, Loader2 } from 'lucide-react'
import { RubricCard } from '../components/rubrics/RubricCard';
import { rubricsApi } from '../components/rubrics/api';
import type { Rubric } from '../components/rubrics/types';
import { clean } from '@/lib/utils';
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

export default function RubricsPage() {
  const navigate = useNavigate();
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showFeaturedOnly, setShowFeaturedOnly] = useState(false);

  const loadCategories = async () => {
    try {
      const cats = await rubricsApi.getCategories();
      setCategories(cats);
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
    }
  };


  const loadRubrics = async () => {
    try {
      setLoading(true);
      const data = await rubricsApi.list(clean({
        ...(selectedCategory ? { category: selectedCategory } : {}),
        is_featured: showFeaturedOnly ? true : undefined,
        ...(search ? { search: search } : {}),
      }));
      setRubrics(data);
    } catch (_err) {
      setError(_err instanceof Error ? _err.message : 'Failed to load rubrics');
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadRubrics();
    loadCategories();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, showFeaturedOnly]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadRubrics();
  };

  const featuredRubrics = rubrics.filter((r) => r.is_featured);
  const otherRubrics = rubrics.filter((r) => !r.is_featured);

  return (
    <PageContainer width="wide" className="py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-earth-100 dark:bg-earth-800/40 rounded-lg">
            <Scale className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Assessment Rubrics
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Evaluate AI tools, projects, and systems using structured criteria
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 p-4 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
        <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={t('placeholder.rubrics.searchRubrics')}
                aria-label={t('aria.rubrics.searchRubrics')}
                className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent dark:bg-earth-700 dark:text-lsc-cream"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose focus:border-transparent dark:bg-earth-700 dark:text-lsc-cream"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => setShowFeaturedOnly(!showFeaturedOnly)}
              className={`px-4 py-2 rounded-lg border flex items-center gap-2 transition-colors ${
                showFeaturedOnly
                  ? 'bg-status-warning-100 border-status-warning-300 text-status-warning-700 dark:bg-status-warning-900/40 dark:border-status-warning-700 dark:text-status-warning-300'
                  : 'border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700'
              }`}
            >
              <Star className={`h-4 w-4 ${showFeaturedOnly ? 'fill-current' : ''}`} />
              Featured
            </button>

            <button
              type="submit"
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
            >
              Search
            </button>
          </div>
        </form>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <Loader2 className="h-12 w-12 motion-safe:animate-spin motion-reduce:animate-none text-earth-600 mx-auto mb-4" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading rubrics...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-center py-12">
          <p className="text-status-danger-500">{error}</p>
          <button
            onClick={loadRubrics}
            className="mt-4 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && rubrics.length === 0 && (
        <div className="text-center py-12">
          <Scale className="h-16 w-16 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            No rubrics found
          </h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {search || selectedCategory
              ? 'Try adjusting your filters'
              : 'Rubrics will appear here once they are published'}
          </p>
        </div>
      )}

      {/* Rubrics List */}
      {!loading && !error && rubrics.length > 0 && (
        <div className="space-y-8">
          {/* Featured Section */}
          {featuredRubrics.length > 0 && !showFeaturedOnly && (
            <section>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Star className="h-5 w-5 text-status-warning-500 fill-current" />
                Featured Rubrics
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {featuredRubrics.map((rubric) => (
                  <RubricCard
                    key={rubric.id}
                    rubric={rubric}
                    linkTo={`/rubrics/${rubric.id}`}
                    onAssess={() => navigate(`/rubrics/${rubric.id}/assess`)}
                  />
                ))}
              </div>
            </section>
          )}

          {/* All Rubrics */}
          <section>
            {featuredRubrics.length > 0 && otherRubrics.length > 0 && !showFeaturedOnly && (
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                All Rubrics
              </h2>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {(showFeaturedOnly ? featuredRubrics : otherRubrics).map((rubric) => (
                <RubricCard
                  key={rubric.id}
                  rubric={rubric}
                  linkTo={`/rubrics/${rubric.id}`}
                  onAssess={() => navigate(`/rubrics/${rubric.id}/assess`)}
                />
              ))}
            </div>
          </section>
        </div>
      )}
    </PageContainer>
  );
}
