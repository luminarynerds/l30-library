/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Clock, Search, GraduationCap, Filter, X, Zap, BarChart3, Video, FileText, HelpCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { CourseThumbnail } from '../components/training';
import { ExternalResourcesSection } from '../components/training';
import { API_BASE } from '@/api/types'
import { t } from '@/i18n'
import { useDebounce } from '@/hooks/useDebounce'
import { getAccessToken } from '@/utils/tokenStore'

interface Course {
  id: number;
  title: string;
  thumbnail_url?: string | null;
  description: string;
  access_level: 'patron' | 'staff' | 'admin';
  estimated_minutes: number | null;
  module_count: number;
  lesson_count: number;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  primary_content_type?: 'article' | 'video' | 'quiz' | 'mixed';
}

type DifficultyFilter = 'all' | 'beginner' | 'intermediate' | 'advanced';
type TimeFilter = 'all' | 'short' | 'medium' | 'long';
type ContentTypeFilter = 'all' | 'article' | 'video' | 'quiz' | 'mixed';

const DIFFICULTY_OPTIONS: { value: DifficultyFilter; labelKey: string; label: string; icon: typeof Zap }[] = [
  { value: 'all', labelKey: 'learnCatalog.difficultyAll', label: 'All Levels', icon: BarChart3 },
  { value: 'beginner', labelKey: 'learnCatalog.difficultyBeginner', label: 'Beginner', icon: Zap },
  { value: 'intermediate', labelKey: 'learnCatalog.difficultyIntermediate', label: 'Intermediate', icon: BarChart3 },
  { value: 'advanced', labelKey: 'learnCatalog.difficultyAdvanced', label: 'Advanced', icon: BarChart3 },
];

const TIME_OPTIONS: { value: TimeFilter; labelKey: string; label: string; range: string }[] = [
  { value: 'all', labelKey: 'learnCatalog.timeAny', label: 'Any Duration', range: '' },
  { value: 'short', labelKey: 'learnCatalog.timeShort', label: 'Quick (< 30 min)', range: '< 30 min' },
  { value: 'medium', labelKey: 'learnCatalog.timeMedium', label: 'Medium (30-60 min)', range: '30-60 min' },
  { value: 'long', labelKey: 'learnCatalog.timeLong', label: 'In-depth (60+ min)', range: '60+ min' },
];

const CONTENT_TYPE_OPTIONS: { value: ContentTypeFilter; labelKey: string; label: string; icon: typeof Video }[] = [
  { value: 'all', labelKey: 'learnCatalog.contentTypeAll', label: 'All Types', icon: BookOpen },
  { value: 'video', labelKey: 'learnCatalog.contentTypeVideo', label: 'Video-focused', icon: Video },
  { value: 'article', labelKey: 'learnCatalog.contentTypeArticle', label: 'Reading-focused', icon: FileText },
  { value: 'quiz', labelKey: 'learnCatalog.contentTypeQuiz', label: 'Quiz-based', icon: HelpCircle },
];

const PAGE_SIZE = 50;

export default function LearnCatalogPage() {
  const { isAuthenticated } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyFilter>('all');
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('all');
  const [contentTypeFilter, setContentTypeFilter] = useState<ContentTypeFilter>('all');
  const [offset, setOffset] = useState(0);

  const [_error, setError] = useState<string | null>(null);

  // Debounce the search input so we don't hammer the API on every keystroke.
  const debouncedSearch = useDebounce(searchTerm, 300);

  // Whenever a filter or search changes, snap back to page 1. Otherwise a user
  // who scrolled to page 3 of "all courses" then types a search would see
  // "page 3 of 4 filtered results" with an unexpectedly thin page 1.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset pagination to page 1 when filters/search change
    setOffset(0);
  }, [debouncedSearch, difficultyFilter, timeFilter, contentTypeFilter]);

  // Fetch on filter/page change. Server applies filters + pagination; we just
  // map UI state -> query params and read X-Total-Count for pagination math.
  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag for the async course fetch below
    setLoading(true);

    const params = new URLSearchParams();
    if (debouncedSearch.trim()) params.set('search', debouncedSearch.trim());
    if (difficultyFilter !== 'all') params.set('difficulty', difficultyFilter);
    if (contentTypeFilter !== 'all') params.set('content_type', contentTypeFilter);
    if (timeFilter === 'short') {
      params.set('duration_max', '30');
    } else if (timeFilter === 'medium') {
      params.set('duration_min', '30');
      params.set('duration_max', '60');
    } else if (timeFilter === 'long') {
      params.set('duration_min', '60');
    }
    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(offset));

    const token = getAccessToken();
    // eslint-disable-next-line no-restricted-syntax -- raw fetch required to read X-Total-Count header; fetchApi/api.get strip headers
    fetch(`${API_BASE}/learning/courses?${params.toString()}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`Failed to load courses: ${res.status}`);
        const total = Number.parseInt(res.headers.get('X-Total-Count') ?? '0', 10);
        const data: Course[] = await res.json();
        setCourses(data);
        setTotalCount(Number.isFinite(total) ? total : data.length);
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setError('Unable to load courses. Please try again later.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [debouncedSearch, difficultyFilter, timeFilter, contentTypeFilter, offset]);

  const activeFilterCount = [difficultyFilter !== 'all', timeFilter !== 'all', contentTypeFilter !== 'all'].filter(Boolean).length;

  const clearFilters = () => {
    setDifficultyFilter('all');
    setTimeFilter('all');
    setContentTypeFilter('all');
  };

  const filteredCourses = courses;
  const pageStart = totalCount === 0 ? 0 : offset + 1;
  const pageEnd = Math.min(offset + filteredCourses.length, totalCount);
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < totalCount;

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('learnCatalog.heading', 'Course Catalog')}</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learnCatalog.subheading', 'Explore our neurodivergent-friendly courses with flexible pacing and multiple formats.')}</p>
        </div>

        {/* Registration prompt for unauthenticated users */}
        {!isAuthenticated && (
          <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 border border-lsc-rose/30 rounded-xl p-4 mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <GraduationCap aria-hidden="true" className="w-8 h-8 text-lsc-rose flex-shrink-0" />
              <p className="text-lsc-dark dark:text-lsc-cream">
                <span className="font-medium">{t('learn.readyToStartLearning')}</span>{' '}
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learnCatalog.registerForFreeToEnroll', 'Register to enroll in courses and track your progress.')}</span>
              </p>
            </div>
            <Link
              to="/account"
              className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-5 py-2 rounded-xl font-medium whitespace-nowrap"
            >
              {t('learnCatalog.signUpFree', 'Sign Up')}
            </Link>
          </div>
        )}

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md p-4 mb-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input type="text" placeholder={t('placeholder.learnCatalog.searchCourses')} aria-label={t('aria.learnCatalog.searchCourses')} value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-colors ${
                showFilters || activeFilterCount > 0
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
              }`}
              aria-expanded={showFilters}
              aria-label={activeFilterCount > 0
                ? `${t('learnCatalog.filtersAriaLabel', 'Filters')} (${activeFilterCount} ${t('learnCatalog.activeSuffix', 'active')})`
                : t('learnCatalog.filtersAriaLabel', 'Filters')}
            >
              <Filter className="w-5 h-5" />
              <span className="hidden sm:inline">{t('learnCatalog.filters', 'Filters')}</span>
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-lsc-white dark:bg-earth-800 text-lsc-rose rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md p-5 mb-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{t('learnCatalog.filterCourses', 'Filter Courses')}</h3>
              {activeFilterCount > 0 && (
                <button
                  onClick={clearFilters}
                  className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:text-lsc-rose/80"
                >
                  <X className="w-4 h-4" />
                  {t('learnCatalog.clearAll', 'Clear all')}
                </button>
              )}
            </div>

            <div className="grid sm:grid-cols-3 gap-6">
              {/* Difficulty Filter */}
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  {t('learnCatalog.difficultyLevel', 'Difficulty Level')}
                </label>
                <div className="space-y-2">
                  {DIFFICULTY_OPTIONS.map(option => (
                    <button
                      key={option.value}
                      onClick={() => setDifficultyFilter(option.value)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                        difficultyFilter === option.value
                          ? 'bg-lsc-rose text-white'
                          : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
                      }`}
                    >
                      <option.icon className="w-4 h-4" />
                      {t(option.labelKey, option.label)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time Filter */}
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  {t('learnCatalog.duration', 'Duration')}
                </label>
                <div className="space-y-2">
                  {TIME_OPTIONS.map(option => (
                    <button
                      key={option.value}
                      onClick={() => setTimeFilter(option.value)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                        timeFilter === option.value
                          ? 'bg-lsc-rose text-white'
                          : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
                      }`}
                    >
                      <Clock className="w-4 h-4" />
                      {t(option.labelKey, option.label)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Content Type Filter */}
              <div>
                <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                  {t('learnCatalog.contentType', 'Content Type')}
                </label>
                <div className="space-y-2">
                  {CONTENT_TYPE_OPTIONS.map(option => (
                    <button
                      key={option.value}
                      onClick={() => setContentTypeFilter(option.value)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                        contentTypeFilter === option.value
                          ? 'bg-lsc-rose text-white'
                          : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
                      }`}
                    >
                      <option.icon className="w-4 h-4" />
                      {t(option.labelKey, option.label)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Active Filters Summary */}
        {activeFilterCount > 0 && !showFilters && (
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('learnCatalog.activeFilters', 'Active filters:')}</span>
            {difficultyFilter !== 'all' && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm">
                {(() => { const o = DIFFICULTY_OPTIONS.find(o => o.value === difficultyFilter); return o ? t(o.labelKey, o.label) : null; })()}
                <button onClick={() => setDifficultyFilter('all')} aria-label={t('aria.learnCatalog.removeDifficultyFilter')}><X className="w-3 h-3" /></button>
              </span>
            )}
            {timeFilter !== 'all' && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm">
                {(() => { const o = TIME_OPTIONS.find(o => o.value === timeFilter); return o ? t(o.labelKey, o.label) : null; })()}
                <button onClick={() => setTimeFilter('all')} aria-label={t('aria.learnCatalog.removeTimeFilter')}><X className="w-3 h-3" /></button>
              </span>
            )}
            {contentTypeFilter !== 'all' && (
              <span className="inline-flex items-center gap-1 px-3 py-1 bg-lsc-rose/10 text-lsc-rose rounded-full text-sm">
                {(() => { const o = CONTENT_TYPE_OPTIONS.find(o => o.value === contentTypeFilter); return o ? t(o.labelKey, o.label) : null; })()}
                <button onClick={() => setContentTypeFilter('all')} aria-label={t('aria.learnCatalog.removeContentTypeFilter')}><X className="w-3 h-3" /></button>
              </span>
            )}
          </div>
        )}

        {/* Results Count */}
        <div role="status" aria-live="polite" aria-atomic="true" className={!loading ? 'flex items-center justify-between mb-4' : 'sr-only'}>
          {!loading && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {totalCount === 0
                ? t('learnCatalog.zeroCoursesFound', '0 courses found')
                : `${t('learnCatalog.showing', 'Showing')} ${pageStart}-${pageEnd} ${t('learnCatalog.of', 'of')} ${totalCount} ${totalCount === 1 ? t('learnCatalog.courseSingular', 'course') : t('learnCatalog.coursePlural', 'courses')}`}
            </p>
          )}
        </div>

        {loading ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6" aria-busy="true" aria-label={t('learnCatalog.loadingCourses', 'Loading courses')}>{[1,2,3].map(i => <div key={i} className="motion-safe:animate-pulse bg-lsc-white dark:bg-earth-800 rounded-xl h-72"></div>)}</div>
        ) : filteredCourses.length === 0 ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
            <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('learnCatalog.noCoursesFound', 'No courses found')}</h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('learnCatalog.tryAdjustingFilters', 'Try adjusting your filters or search term.')}</p>
            {activeFilterCount > 0 && (
              <button onClick={clearFilters} className="text-lsc-rose hover:underline">
                {t('learnCatalog.clearAllFilters', 'Clear all filters')}
              </button>
            )}
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCourses.map(course => {
              const difficultyColors = {
                beginner: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300',
                intermediate: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
                advanced: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300',
              };
              return (
                <Link key={course.id} to={`/learn/course/${course.id}`} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md hover:shadow-lg hover:-translate-y-1 transition-all overflow-hidden group">
                    <div className="relative"><CourseThumbnail title={course.title} {...(course.thumbnail_url ? { thumbnailUrl: course.thumbnail_url } : {})} className="w-full" />
                    {course.difficulty && (
                      <div className={`absolute bottom-3 left-3 px-2 py-1 rounded-full text-xs font-medium capitalize ${difficultyColors[course.difficulty]}`}>
                        {course.difficulty}
                      </div>
                    )}
                  </div>
                  <div className="p-5">
                    <h3 className="font-serif font-bold text-lg text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:text-lsc-rose-light">{course.title}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 line-clamp-2" title={course.description}>{course.description}</p>
                    <div className="mt-4 flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="flex items-center gap-1"><BookOpen aria-hidden="true" className="w-4 h-4" />{course.lesson_count} {t('learnCatalog.lessons', 'lessons')}</span>
                      {course.estimated_minutes && <span className="flex items-center gap-1"><Clock aria-hidden="true" className="w-4 h-4" />{course.estimated_minutes} {t('learnCatalog.min', 'min')}</span>}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {!loading && filteredCourses.length > 0 && (hasPrev || hasNext) && (
          <nav
            aria-label="Course catalog pagination"
            className="mt-8 flex items-center justify-between gap-4"
          >
            <button
              type="button"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={!hasPrev}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Previous page"
            >
              <ChevronLeft aria-hidden="true" className="w-4 h-4" />
              Previous
            </button>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Showing {pageStart}-{pageEnd} of {totalCount}
            </span>
            <button
              type="button"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={!hasNext}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-medium bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Next page"
            >
              Next
              <ChevronRight aria-hidden="true" className="w-4 h-4" />
            </button>
          </nav>
        )}

        {/* Divider */}
        {!loading && filteredCourses.length > 0 && (
          <div className="my-12 border-t border-lsc-border dark:border-earth-700"></div>
        )}

        {/* External Resources Section */}
        {!loading && (
          <ExternalResourcesSection
            showFilters={true}
            featuredOnly={false}
            maxResources={20}
            showTitle={true}
          />
        )}
      </div>
    </div>
  );
}