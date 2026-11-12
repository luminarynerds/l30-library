/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useEffect, useState, useCallback, useMemo, type KeyboardEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  Plus,
  Edit,
  Trash2,
  Loader2,
  BookOpen,
  GraduationCap,
  Users,
  FileText,
  Layers,
  Search,
  X,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Copy,
  Upload,
  Clock,
  Calendar,
  LayoutTemplate,
} from 'lucide-react';
import {
  getAllCoursesAdmin,
  deleteCourse,
  cloneCourse,
  getCourseReviewQueue,
  transitionCourseStage,
  CourseStageTransitionError,
  type CourseListItemAdmin,
  type CourseLifecycleStage,
} from '@/api/domains/learning/courses-api';
import { LifecycleStageBadge, CourseStatusActions } from '../components/admin/LifecycleStageBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { AdminShell } from '../components/shells';
import { useTranslation } from '@/i18n';
import { useAuth } from '../contexts/AuthContext';
import { useDebounce } from '../hooks/useDebounce';
import type { AccessTab, SortKey } from './admin-courses/types';
import {
  ALL_STAGES,
  ACCESS_TABS,
  defaultTabForRole,
  parseAccessTab,
  parseStageSet,
  parseDifficulty,
  parseSort,
} from './admin-courses/urlParams';
import { AccessLevelBadge, DifficultyBadge } from './admin-courses/CourseBadges';
import { EnrollmentCell, EnrollmentMobileLine } from './admin-courses/EnrollmentCells';
import { DuplicateCourseModal } from './admin-courses/DuplicateCourseModal';
import { FilterChip } from './admin-courses/FilterChip';

type SortableCol = 'title' | 'modules' | 'lessons' | 'enrollment';

const sortForColumn: Record<SortableCol, SortKey> = {
  title: 'title_asc',
  modules: 'modules_desc',
  lessons: 'lessons_desc',
  enrollment: 'enrollees_desc',
};

function SortIcon({ col, sortKey }: { col: SortableCol; sortKey: SortKey }) {
  if (sortKey !== sortForColumn[col]) {
    return <ArrowUpDown className="w-3.5 h-3.5 opacity-50" aria-hidden="true" />;
  }
  return col === 'title' ? (
    <ArrowUp className="w-3.5 h-3.5" aria-hidden="true" />
  ) : (
    <ArrowDown className="w-3.5 h-3.5" aria-hidden="true" />
  );
}

export default function AdminCoursesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [courses, setCourses] = useState<CourseListItemAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState<
    { id: number; title: string; enrollmentCount: number } | null
  >(null);
  const [deleting, setDeleting] = useState(false);
  const [archiving, setArchiving] = useState(false);
  // Duplicate-modal state
  const [duplicateTarget, setDuplicateTarget] = useState<{ id: number; title: string } | null>(null);
  // Annual-review-due aggregate count (header chip). Fetched once on mount;
  // the chip is hidden when zero.
  const [reviewDueCount, setReviewDueCount] = useState(0);

  // Fetch courses on mount
  const fetchCourses = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getAllCoursesAdmin();
      setCourses(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(err instanceof Error ? err.message : t('toast.adminCourses.failedToLoadCourses'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  // Review-queue header aggregate: single GET on mount, no poll loop.
  // Failure is non-fatal — the chip just stays hidden (count 0).
  useEffect(() => {
    let cancelled = false;
    getCourseReviewQueue()
      .then((res) => {
        if (!cancelled) setReviewDueCount(res.due_count);
      })
      .catch((err: unknown) => {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Splice the refreshed admin row in place after a stage transition. The
  // /transition response is a full CourseListItemAdmin so we can replace
  // the row wholesale (unlike the legacy publish toggle).
  const handleTransitioned = useCallback((updated: CourseListItemAdmin) => {
    setCourses((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
  }, []);

  // Handle course deletion (optimistic: drop from local list on success)
  const handleDelete = async (id: number) => {
    setDeleting(true);
    try {
      await deleteCourse(id);
      setCourses((prev) => prev.filter((c) => c.id !== id));
      toast.success(t('toast.adminCourses.courseDeletedSuccessfully'));
      setDeleteConfirm(null);
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(err instanceof Error ? err.message : t('toast.adminCourses.failedToDeleteCourse'));
      setDeleteConfirm(null);
    } finally {
      setDeleting(false);
    }
  };

  // "Archive instead" secondary action in the delete dialog. Same
  // response-driven splice as LifecycleStageBadge.doTransition: await the
  // transition, splice the refreshed row in place (handleTransitioned uses
  // .map(), so the row stays — unlike delete which filters it out), toast,
  // close. confirm: true is safe — the user is already in the destructive
  // delete dialog and has seen the enrollment-impact warning. On failure
  // nothing was applied, so there is nothing to revert; keep the dialog
  // open. Sentry only on the unexpected (generic) catch, matching the badge.
  const handleArchiveInstead = async (id: number) => {
    setArchiving(true);
    try {
      const updated = await transitionCourseStage(id, {
        to_stage: 'archived',
        confirm: true,
      });
      handleTransitioned(updated);
      toast.success(t('toast.adminCourses.courseArchived'));
      setDeleteConfirm(null);
    } catch (err: unknown) {
      if (err instanceof CourseStageTransitionError) {
        toast.error(err.message || t('toast.adminCourses.stageChangeFailed'));
        return;
      }
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      toast.error(t('toast.adminCourses.stageChangeFailed'));
    } finally {
      setArchiving(false);
    }
  };

  // Handle clone submit: append the new draft to local state, default the
  // enrollment aggregates to zero (the row is brand new, no enrollments yet).
  const handleDuplicate = useCallback(
    async (sourceId: number, newTitle: string): Promise<{ ok: true } | { ok: false; error: string }> => {
      try {
        const created = await cloneCourse(sourceId, {
          new_title: newTitle,
          include_unpublished_lessons: true,
        });
        const adminRow: CourseListItemAdmin = {
          ...created,
          enrollment_count: 0,
          completion_count: 0,
          in_progress_count: 0,
          last_activity_at: null,
          // A freshly-cloned course is always a draft with no review history.
          lifecycle_stage: 'draft',
          last_reviewed_at: null,
          review_due_at: null,
          last_reviewed_by: null,
          is_review_due: false,
        };
        setCourses((prev) => [adminRow, ...prev]);
        toast.success(
          (toastObj) => (
            <span className="flex items-center gap-3">
              <span>{t('toast.adminCourses.courseDuplicated', { title: newTitle })}</span>
              <button
                type="button"
                onClick={() => {
                  toast.dismiss(toastObj.id);
                  navigate(`/staff/admin/courses/${created.id}/edit`);
                }}
                className="underline font-medium hover:no-underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
              >
                {t('admin.adminCourses.duplicateOpenLink')}
              </button>
            </span>
          ),
          { duration: 6000 },
        );
        return { ok: true };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.toLowerCase().includes('already exists')) {
          return { ok: false, error: t('admin.adminCourses.duplicateTitleExistsError') };
        }
        if (msg.toLowerCase().includes('3-200') || msg.toLowerCase().includes('3 to 200')) {
          return { ok: false, error: t('admin.adminCourses.duplicateTitleLengthError') };
        }
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        toast.error(t('toast.adminCourses.courseDuplicateFailed'));
        return { ok: false, error: t('toast.adminCourses.courseDuplicateFailed') };
      }
    },
    [t, navigate],
  );

  // Decoded URL state
  const defaultTab = defaultTabForRole(user?.role);
  const accessTab = parseAccessTab(searchParams.get('access'), defaultTab);
  const stageSet = useMemo(
    () => parseStageSet(searchParams.get('stage'), searchParams.get('status')),
    [searchParams],
  );
  const allStagesSelected = stageSet.size === ALL_STAGES.length;
  const reviewDueOnly = searchParams.get('review_due') === 'true';
  const difficultyFilter = parseDifficulty(searchParams.get('difficulty'));
  const hasContentOnly = searchParams.get('has_content') === 'true';
  const sortKey = parseSort(searchParams.get('sort'));
  const urlQuery = searchParams.get('q') ?? '';

  // Search input is local for typing responsiveness; URL gets the debounced value.
  const [searchInput, setSearchInput] = useState(urlQuery);
  const debouncedSearch = useDebounce(searchInput, 200);

  // Sync debounced search input into the URL (preserving other params).
  useEffect(() => {
    if (debouncedSearch === (searchParams.get('q') ?? '')) return;
    const next = new URLSearchParams(searchParams);
    if (debouncedSearch) next.set('q', debouncedSearch);
    else next.delete('q');
    setSearchParams(next, { replace: true });
    // intentionally exclude searchParams/setSearchParams so we only react to user typing
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  // Setter helpers that preserve other URL params.
  const updateParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(searchParams);
      if (value === null || value === '') next.delete(key);
      else next.set(key, value);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const clearAllFilters = useCallback(() => {
    setSearchInput('');
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  // Per-tab counts run against the full course list (status/difficulty/search/sort
  // don't change which tab a course belongs to).
  const tabCounts = useMemo(() => {
    const counts: Record<AccessTab, number> = { all: courses.length, patron: 0, staff: 0, admin: 0 };
    for (const c of courses) {
      if (c.access_level === 'patron' || c.access_level === 'staff' || c.access_level === 'admin') {
        counts[c.access_level] += 1;
      }
    }
    return counts;
  }, [courses]);

  const filtered = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    let out = courses.filter((c) => {
      if (accessTab !== 'all' && c.access_level !== accessTab) return false;
      if (!allStagesSelected && !stageSet.has(c.lifecycle_stage)) return false;
      if (reviewDueOnly && !c.is_review_due) return false;
      if (difficultyFilter !== 'any' && c.difficulty !== difficultyFilter) return false;
      if (hasContentOnly && (c.lesson_count ?? 0) === 0) return false;
      if (q) {
        const title = c.title.toLowerCase();
        const desc = (c.description ?? '').toLowerCase();
        if (!title.includes(q) && !desc.includes(q)) return false;
      }
      return true;
    });

    out = [...out].sort((a, b) => {
      switch (sortKey) {
        case 'title_asc':
          return a.title.localeCompare(b.title);
        case 'created_desc':
          return (b.created_at ?? '').localeCompare(a.created_at ?? '');
        case 'lessons_desc':
          return (b.lesson_count ?? 0) - (a.lesson_count ?? 0);
        case 'modules_desc':
          return (b.module_count ?? 0) - (a.module_count ?? 0);
        case 'enrollees_desc':
          return b.enrollment_count - a.enrollment_count;
        case 'updated_desc':
        default:
          return (b.updated_at ?? b.created_at ?? '').localeCompare(
            a.updated_at ?? a.created_at ?? '',
          );
      }
    });

    return out;
  }, [courses, accessTab, allStagesSelected, stageSet, reviewDueOnly, difficultyFilter, hasContentOnly, debouncedSearch, sortKey]);

  const hasAnyFilter =
    accessTab !== defaultTab ||
    !allStagesSelected ||
    reviewDueOnly ||
    difficultyFilter !== 'any' ||
    hasContentOnly ||
    debouncedSearch.trim() !== '' ||
    sortKey !== 'updated_desc';

  // Toggle one stage chip. Writes the canonical comma list to ?stage=,
  // clears the param entirely when all five are selected (default view),
  // and drops the legacy ?status= alias so the two never conflict.
  const toggleStage = useCallback(
    (s: CourseLifecycleStage) => {
      const next = new Set(stageSet);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      // Never allow an empty set (would hide everything) — re-select all.
      const effective = next.size === 0 ? new Set(ALL_STAGES) : next;
      const params = new URLSearchParams(searchParams);
      params.delete('status');
      if (effective.size === ALL_STAGES.length) {
        params.delete('stage');
      } else {
        params.set(
          'stage',
          ALL_STAGES.filter((x) => effective.has(x)).join(','),
        );
      }
      setSearchParams(params, { replace: true });
    },
    [stageSet, searchParams, setSearchParams],
  );

  const clearReviewDue = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    params.delete('review_due');
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams]);

  // Sortable column header helpers: clicking cycles to that sort key, aria-sort
  // reflects current state. Only one column is "sorted" at a time.
  const ariaSortFor = (col: SortableCol): 'ascending' | 'descending' | 'none' => {
    if (sortKey !== sortForColumn[col]) return 'none';
    return col === 'title' ? 'ascending' : 'descending';
  };

  // Tablist keyboard handler (arrow keys + Home/End). Mirrors BookClubDetailPage.tsx:158.
  const handleTabKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const idx = ACCESS_TABS.indexOf(accessTab);
    let next = idx;
    if (e.key === 'ArrowRight') next = (idx + 1) % ACCESS_TABS.length;
    else if (e.key === 'ArrowLeft') next = (idx - 1 + ACCESS_TABS.length) % ACCESS_TABS.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = ACCESS_TABS.length - 1;
    else return;
    e.preventDefault();
    const nextTab = ACCESS_TABS[next];
    if (!nextTab) return;
    updateParam('access', nextTab === defaultTab ? null : nextTab);
    document.getElementById(`admin-courses-tab-${nextTab}`)?.focus();
  };

  return (
    <AdminShell
      title={t('admin.adminCourses.manageCourses')}
      subtitle={t('admin.adminCourses.manageCoursesSubtitle')}
      icon={<GraduationCap className="w-8 h-8" aria-hidden="true" />}
      actions={
        <>
          {reviewDueCount > 0 && (
            <Link
              to="?review_due=true"
              className="
                inline-flex items-center gap-2 px-4 py-3 rounded-lg font-medium
                bg-status-warning-100 text-status-warning-800
                dark:bg-status-warning-900/30 dark:text-status-warning-300
                hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50
                motion-safe:transition-colors
                focus:outline-none focus:ring-2 focus:ring-status-warning-500 focus:ring-offset-2
                dark:focus:ring-offset-earth-800
                min-h-[44px]
              "
              aria-label={t('aria.adminCourses.reviewDueChip', {
                count: reviewDueCount,
              })}
            >
              <Clock className="w-4 h-4" aria-hidden="true" />
              {t('admin.adminCourses.reviewDueChip', { count: reviewDueCount })}
            </Link>
          )}
          <Link
            to="/staff/admin/courses/templates"
            className="
              border border-lsc-border dark:border-earth-700
              text-lsc-dark dark:text-lsc-cream px-5 py-3 rounded-lg
              flex items-center gap-2 font-medium
              hover:bg-lsc-cream dark:hover:bg-earth-700 motion-safe:transition-colors
              focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
              dark:focus:ring-offset-earth-800
              min-h-[44px]
            "
            aria-label="Use template"
          >
            <LayoutTemplate className="w-5 h-5" aria-hidden="true" />
            Use template
          </Link>
          <Link
            to="/staff/admin/courses/import"
            className="
              border border-lsc-rose text-lsc-rose px-5 py-3 rounded-lg
              flex items-center gap-2 font-medium
              hover:bg-lsc-rose/10 motion-safe:transition-colors
              focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
              dark:focus:ring-offset-earth-800
              min-h-[44px]
            "
            aria-label={t('aria.adminCourses.importCourses')}
          >
            <Upload className="w-5 h-5" aria-hidden="true" />
            {t('admin.adminCourses.importAction')}
          </Link>
          <Link
            to="/staff/admin/courses/new"
            className="
              bg-lsc-rose text-white px-5 py-3 rounded-lg
              flex items-center gap-2 font-medium
              hover:bg-lsc-rose/90 motion-safe:transition-colors
              focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
              dark:focus:ring-offset-earth-800
              min-h-[44px]
            "
            aria-label={t('admin.adminCourses.createANewCourse')}
          >
            <Plus className="w-5 h-5" aria-hidden="true" />
            {t('admin.adminCourses.createCourse')}
          </Link>
        </>
      }
    >
      {loading ? (
        <div
          className="flex flex-col items-center justify-center py-16"
          role="status"
          aria-live="polite"
          aria-busy="true"
        >
          <Loader2
            className="w-10 h-10 motion-safe:animate-spin text-lsc-rose"
            aria-hidden="true"
          />
          <span className="mt-4 text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('admin.adminCourses.loadingCourses')}
          </span>
        </div>
      ) : courses.length === 0 ? (
        /* Empty state with helpful guidance */
        <div
          className="
            bg-lsc-white dark:bg-earth-800
            border border-lsc-border dark:border-earth-700
            rounded-xl p-12 text-center
          "
          role="status"
          aria-live="polite"
        >
          <div className="w-16 h-16 bg-lsc-rose/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <BookOpen className="w-8 h-8 text-lsc-rose" aria-hidden="true" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            {t('admin.adminCourses.noCoursesYet')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-md mx-auto mb-6">
            {t('admin.adminCourses.emptyStateBody')}
          </p>
          <Link
            to="/staff/admin/courses/new"
            className="
              inline-flex items-center gap-2 bg-lsc-rose text-white
              px-6 py-3 rounded-lg font-medium
              hover:bg-lsc-rose/90 motion-safe:transition-colors
              focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
              dark:focus:ring-offset-earth-800
              min-h-[44px]
            "
          >
            <Plus className="w-5 h-5" aria-hidden="true" />
            {t('admin.adminCourses.createYourFirstCourse')}
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Access-level tabs */}
          <div
            role="tablist"
            aria-label={t('aria.adminCourses.accessLevelTabs')}
            onKeyDown={handleTabKeyDown}
            className="flex flex-wrap gap-1 bg-lsc-white dark:bg-earth-800 rounded-xl p-1 border border-lsc-border dark:border-earth-700"
          >
            {ACCESS_TABS.map((tab) => {
              const isActive = accessTab === tab;
              const labelKey =
                tab === 'all'
                  ? 'admin.adminCourses.tabAll'
                  : tab === 'patron'
                    ? 'admin.adminCourses.accessPatron'
                    : tab === 'staff'
                      ? 'admin.adminCourses.accessStaff'
                      : 'admin.adminCourses.accessAdmin';
              return (
                <button
                  key={tab}
                  id={`admin-courses-tab-${tab}`}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => updateParam('access', tab === defaultTab ? null : tab)}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                    motion-safe:transition-colors
                    focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose
                    dark:focus:ring-offset-earth-800
                    ${
                      isActive
                        ? 'bg-lsc-rose text-white'
                        : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'
                    }
                  `}
                >
                  {t(labelKey)}
                  <span
                    className={`
                      inline-flex items-center justify-center min-w-[1.5rem] px-1.5 h-5
                      text-xs font-semibold rounded-full
                      ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80'
                      }
                    `}
                    aria-hidden="true"
                  >
                    {tabCounts[tab]}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Filter / sort / search toolbar */}
          <div
            className="
              bg-lsc-white dark:bg-earth-800
              border border-lsc-border dark:border-earth-700
              rounded-xl p-3 flex flex-wrap items-center gap-2
            "
          >
            <label className="relative flex-1 min-w-[200px]">
              <span className="sr-only">{t('admin.adminCourses.searchLabel')}</span>
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50 pointer-events-none"
                aria-hidden="true"
              />
              <input
                type="search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={t('admin.adminCourses.searchPlaceholder')}
                className="
                  w-full pl-9 pr-3 py-2 rounded-lg
                  bg-lsc-cream/50 dark:bg-earth-900
                  border border-lsc-border dark:border-earth-700
                  text-sm text-lsc-dark dark:text-lsc-cream
                  placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/60
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose
                "
              />
            </label>

            <fieldset className="inline-flex items-center gap-1.5 flex-wrap">
              <legend className="sr-only">
                {t('admin.adminCourses.filterStageLegend')}
              </legend>
              <span
                className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-hidden="true"
              >
                {t('admin.adminCourses.filterStageLabel')}
              </span>
              {ALL_STAGES.map((s) => {
                const active = stageSet.has(s);
                return (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleStage(s)}
                    className={`
                      px-3 py-1.5 rounded-full text-xs font-medium
                      motion-safe:transition-colors
                      focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1
                      dark:focus:ring-offset-earth-800
                      ${
                        active
                          ? 'bg-lsc-rose text-white'
                          : 'border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700'
                      }
                    `}
                  >
                    {t(`admin.adminCourses.stage_${s}`)}
                  </button>
                );
              })}
            </fieldset>

            <FilterChip
              label={t('admin.adminCourses.filterDifficultyLabel')}
              value={difficultyFilter}
              options={[
                { value: 'any', label: t('admin.adminCourses.filterDifficultyAny') },
                { value: 'beginner', label: t('admin.adminCourses.difficultyBeginner') },
                { value: 'intermediate', label: t('admin.adminCourses.difficultyIntermediate') },
                { value: 'advanced', label: t('admin.adminCourses.difficultyAdvanced') },
              ]}
              onChange={(v) => updateParam('difficulty', v === 'any' ? null : v)}
            />

            <label className="inline-flex items-center gap-2 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream cursor-pointer">
              <input
                type="checkbox"
                checked={hasContentOnly}
                onChange={(e) => updateParam('has_content', e.target.checked ? 'true' : null)}
                className="w-4 h-4 rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
              />
              {t('admin.adminCourses.filterHideEmpty')}
            </label>

            <label className="inline-flex items-center gap-2 text-sm">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('admin.adminCourses.sortLabel')}
              </span>
              <select
                value={sortKey}
                onChange={(e) => updateParam('sort', e.target.value === 'updated_desc' ? null : e.target.value)}
                className="
                  px-3 py-2 rounded-lg
                  bg-lsc-cream/50 dark:bg-earth-900
                  border border-lsc-border dark:border-earth-700
                  text-sm text-lsc-dark dark:text-lsc-cream
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose
                "
              >
                <option value="updated_desc">{t('admin.adminCourses.sortUpdatedDesc')}</option>
                <option value="created_desc">{t('admin.adminCourses.sortCreatedDesc')}</option>
                <option value="title_asc">{t('admin.adminCourses.sortTitleAsc')}</option>
                <option value="lessons_desc">{t('admin.adminCourses.sortLessonsDesc')}</option>
                <option value="enrollees_desc">{t('admin.adminCourses.sortEnrolleesDesc')}</option>
              </select>
            </label>

            {hasAnyFilter && (
              <button
                type="button"
                onClick={clearAllFilters}
                className="
                  inline-flex items-center gap-1 px-3 py-2 rounded-lg
                  text-sm font-medium
                  text-lsc-dark/70 dark:text-lsc-cream/70
                  hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose
                "
              >
                <X className="w-4 h-4" aria-hidden="true" />
                {t('admin.adminCourses.clearFilters')}
              </button>
            )}
          </div>

          {reviewDueOnly && (
            <div
              className="
                flex items-center justify-between gap-3 flex-wrap
                bg-status-warning-50 dark:bg-status-warning-900/20
                border border-status-warning-200 dark:border-status-warning-800
                rounded-xl px-4 py-2.5
              "
            >
              <span className="inline-flex items-center gap-2 text-sm text-status-warning-800 dark:text-status-warning-300">
                <Clock className="w-4 h-4" aria-hidden="true" />
                {t('admin.adminCourses.reviewDueBreadcrumb', {
                  count: filtered.length,
                })}
              </span>
              <button
                type="button"
                onClick={clearReviewDue}
                className="
                  inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium
                  text-status-warning-800 dark:text-status-warning-300
                  hover:bg-status-warning-100 dark:hover:bg-status-warning-900/40
                  motion-safe:transition-colors
                  focus:outline-none focus:ring-2 focus:ring-status-warning-500
                "
              >
                <X className="w-4 h-4" aria-hidden="true" />
                {t('admin.adminCourses.reviewDueClear')}
              </button>
            </div>
          )}

          {filtered.length === 0 ? (
            <div
              className="
                bg-lsc-white dark:bg-earth-800
                border border-lsc-border dark:border-earth-700
                rounded-xl p-10 text-center
              "
              role="status"
              aria-live="polite"
            >
              <div className="sr-only">
                {t('admin.adminCourses.coursesMatchCount', { count: 0 })}
              </div>
              <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-4">
                {t('admin.adminCourses.noMatchesBody')}
              </p>
              <button
                type="button"
                onClick={clearAllFilters}
                className="
                  inline-flex items-center gap-2
                  px-4 py-2 rounded-lg font-medium
                  bg-lsc-rose text-white
                  hover:bg-lsc-rose/90 motion-safe:transition-colors
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2
                  dark:focus:ring-offset-earth-800
                  min-h-[44px]
                "
              >
                <X className="w-4 h-4" aria-hidden="true" />
                {t('admin.adminCourses.clearFilters')}
              </button>
            </div>
          ) : (
            /* Courses table (desktop) + card list (mobile) */
            <div
              className="
                bg-lsc-white dark:bg-earth-800
                shadow-md rounded-xl overflow-hidden
                border border-lsc-border dark:border-earth-700
              "
            >
              {/* Polite live region: announces filtered result count */}
              <div className="sr-only" role="status" aria-live="polite">
                {t('admin.adminCourses.coursesMatchCount', { count: filtered.length })}
              </div>

              {/* Desktop table */}
              <div className="overflow-x-auto hidden md:block">
                <table
                  className="w-full divide-y divide-lsc-border dark:divide-earth-700 hidden md:table"
                  aria-label={t('aria.adminCourses.trainingCourses')}
                >
                  <thead className="bg-lsc-cream dark:bg-earth-700">
                    <tr>
                      <th
                        scope="col"
                        aria-sort={ariaSortFor('title')}
                        className="px-6 py-4 text-left text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        <button
                          type="button"
                          onClick={() => updateParam('sort', sortForColumn.title === 'updated_desc' ? null : sortForColumn.title)}
                          className="inline-flex items-center gap-1.5 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          {t('admin.adminCourses.columnCourse')}
                          <SortIcon col="title" sortKey={sortKey} />
                        </button>
                      </th>
                      <th
                        scope="col"
                        className="px-6 py-4 text-left text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        {t('admin.adminCourses.columnStatus')}
                      </th>
                      <th
                        scope="col"
                        className="px-6 py-4 text-left text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        {t('admin.adminCourses.columnDifficulty')}
                      </th>
                      <th
                        scope="col"
                        className="px-6 py-4 text-left text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        {t('admin.adminCourses.columnAccess')}
                      </th>
                      <th
                        scope="col"
                        aria-sort={ariaSortFor('modules')}
                        className="px-6 py-4 text-center text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        <button
                          type="button"
                          onClick={() => updateParam('sort', sortForColumn.modules)}
                          className="inline-flex items-center gap-1.5 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          <Layers className="w-4 h-4" aria-hidden="true" />
                          {t('admin.adminCourses.columnModules')}
                          <SortIcon col="modules" sortKey={sortKey} />
                        </button>
                      </th>
                      <th
                        scope="col"
                        aria-sort={ariaSortFor('lessons')}
                        className="px-6 py-4 text-center text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        <button
                          type="button"
                          onClick={() => updateParam('sort', sortForColumn.lessons)}
                          className="inline-flex items-center gap-1.5 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          <FileText className="w-4 h-4" aria-hidden="true" />
                          {t('admin.adminCourses.columnLessons')}
                          <SortIcon col="lessons" sortKey={sortKey} />
                        </button>
                      </th>
                      <th
                        scope="col"
                        aria-sort={ariaSortFor('enrollment')}
                        className="px-6 py-4 text-left text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        <button
                          type="button"
                          onClick={() => updateParam('sort', sortForColumn.enrollment)}
                          className="inline-flex items-center gap-1.5 hover:text-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                        >
                          <Users className="w-4 h-4" aria-hidden="true" />
                          {t('admin.adminCourses.columnEnrollment')}
                          <SortIcon col="enrollment" sortKey={sortKey} />
                        </button>
                      </th>
                      <th
                        scope="col"
                        className="px-6 py-4 text-right text-xs font-semibold text-lsc-dark/80 dark:text-lsc-cream/80 uppercase tracking-wider"
                      >
                        {t('admin.adminCourses.columnActions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-lsc-white dark:bg-earth-800 divide-y divide-lsc-border dark:divide-earth-700">
                    {filtered.map((course) => (
                      <tr
                        key={course.id}
                        className="hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 motion-safe:transition-colors"
                      >
                        {/* Course title and description */}
                        <td className="px-6 py-4">
                          <div className="flex items-start gap-3">
                            {course.thumbnail_url ? (
                              <img
                                src={course.thumbnail_url}
                                alt={t('admin.adminCourses.thumbnailAlt', { title: course.title })}
                                className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                              />
                            ) : (
                              <div className="w-12 h-12 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
                                <BookOpen className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
                              </div>
                            )}
                            <div className="min-w-0">
                              <p
                                className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs"
                                title={course.title}
                              >
                                {course.title}
                              </p>
                              {course.description && (
                                <p
                                  className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xs mt-1" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                                  title={course.description}
                                >
                                  {course.description}
                                </p>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Stage */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex flex-col items-start gap-1.5">
                            <LifecycleStageBadge stage={course.lifecycle_stage} t={t} />
                            <CourseStatusActions course={course} t={t} onTransitioned={handleTransitioned} />
                          </div>
                        </td>

                        {/* Difficulty */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <DifficultyBadge
                            {...(course.difficulty ? { difficulty: course.difficulty } : {})}
                            t={t}
                          />
                        </td>

                        {/* Access level */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <AccessLevelBadge level={course.access_level} t={t} />
                        </td>

                        {/* Module count */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {course.module_count ?? 0}
                            <span className="sr-only"> {t('admin.adminCourses.columnModules')}</span>
                          </span>
                        </td>

                        {/* Lesson count */}
                        <td className="px-6 py-4 whitespace-nowrap text-center">
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {course.lesson_count ?? 0}
                            <span className="sr-only"> {t('admin.adminCourses.columnLessons')}</span>
                          </span>
                        </td>

                        {/* Enrollment + progress */}
                        <td className="px-6 py-4 whitespace-nowrap">
                          <EnrollmentCell course={course} t={t} />
                        </td>

                        {/* Actions */}
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              to="/staff/admin/sessions"
                              className="
                                inline-flex items-center justify-center
                                w-11 h-11 rounded-lg
                                text-lsc-dark/70 dark:text-lsc-cream/70
                                hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                                motion-safe:transition-colors
                                focus:outline-none focus:ring-2 focus:ring-lsc-rose
                              "
                              aria-label={`${t('admin.adminCourses.scheduleSession', 'Schedule session')}: ${course.title}`}
                              title={t('admin.adminCourses.scheduleSession', 'Schedule session')}
                            >
                              <Calendar className="w-5 h-5" aria-hidden="true" />
                            </Link>
                            <Link
                              to={`/staff/admin/courses/${course.id}/edit`}
                              className="
                                inline-flex items-center justify-center
                                w-11 h-11 rounded-lg
                                text-lsc-rose hover:bg-lsc-rose/10
                                motion-safe:transition-colors
                                focus:outline-none focus:ring-2 focus:ring-lsc-rose
                              "
                              aria-label={t('aria.adminCourses.editCourse', { title: course.title })}
                            >
                              <Edit className="w-5 h-5" aria-hidden="true" />
                            </Link>
                            <button
                              type="button"
                              onClick={() => setDuplicateTarget({ id: course.id, title: course.title })}
                              className="
                                inline-flex items-center justify-center
                                w-11 h-11 rounded-lg
                                text-lsc-dark/70 dark:text-lsc-cream/70
                                hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                                motion-safe:transition-colors
                                focus:outline-none focus:ring-2 focus:ring-lsc-rose
                              "
                              aria-label={t('aria.adminCourses.duplicateCourse', { title: course.title })}
                            >
                              <Copy className="w-5 h-5" aria-hidden="true" />
                            </button>
                            <button
                              onClick={() =>
                                setDeleteConfirm({
                                  id: course.id,
                                  title: course.title,
                                  enrollmentCount: course.enrollment_count,
                                })
                              }
                              className="
                                inline-flex items-center justify-center
                                w-11 h-11 rounded-lg
                                text-status-danger-600 dark:text-status-danger-400
                                hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/20
                                motion-safe:transition-colors
                                focus:outline-none focus:ring-2 focus:ring-status-danger-500
                              "
                              aria-label={t('aria.adminCourses.deleteCourse', { title: course.title })}
                            >
                              <Trash2 className="w-5 h-5" aria-hidden="true" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile card list */}
              <ul className="md:hidden divide-y divide-lsc-border dark:divide-earth-700">
                {filtered.map((course) => (
                  <li key={course.id} className="p-4 space-y-3">
                    {/* Row 1: thumbnail + title */}
                    <div className="flex items-start gap-3">
                      {course.thumbnail_url ? (
                        <img
                          src={course.thumbnail_url}
                          alt={t('admin.adminCourses.thumbnailAlt', { title: course.title })}
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p
                          className="text-sm font-medium text-lsc-dark dark:text-lsc-cream"
                          title={course.title}
                        >
                          {course.title}
                        </p>
                        {course.description && (
                          <p
                            className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1" style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                            title={course.description}
                          >
                            {course.description}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Row 2: three badges */}
                    <div className="flex flex-wrap items-center gap-2">
                      <LifecycleStageBadge stage={course.lifecycle_stage} t={t} />
                      <DifficultyBadge
                        {...(course.difficulty ? { difficulty: course.difficulty } : {})}
                        t={t}
                      />
                      <AccessLevelBadge level={course.access_level} t={t} />
                    </div>

                    {/* Row 3: counts */}
                    <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="inline-flex items-center gap-1.5">
                        <Layers className="w-4 h-4" aria-hidden="true" />
                        {course.module_count ?? 0} {t('admin.adminCourses.columnModules')}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <FileText className="w-4 h-4" aria-hidden="true" />
                        {course.lesson_count ?? 0} {t('admin.adminCourses.columnLessons')}
                      </span>
                    </div>

                    {/* Row 3b: mobile enrollment line */}
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <EnrollmentMobileLine course={course} t={t} />
                    </div>

                    {/* Row 4: status action + other actions */}
                    <div className="flex items-center justify-end gap-2 flex-wrap">
                      <CourseStatusActions course={course} t={t} onTransitioned={handleTransitioned} />
                      <Link
                        to="/staff/admin/sessions"
                        className="
                          inline-flex items-center justify-center
                          w-11 h-11 rounded-lg
                          text-lsc-dark/70 dark:text-lsc-cream/70
                          hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                          motion-safe:transition-colors
                          focus:outline-none focus:ring-2 focus:ring-lsc-rose
                        "
                        aria-label={`${t('admin.adminCourses.scheduleSession', 'Schedule session')}: ${course.title}`}
                        title={t('admin.adminCourses.scheduleSession', 'Schedule session')}
                      >
                        <Calendar className="w-5 h-5" aria-hidden="true" />
                      </Link>
                      <Link
                        to={`/staff/admin/courses/${course.id}/edit`}
                        className="
                          inline-flex items-center justify-center
                          w-11 h-11 rounded-lg
                          text-lsc-rose hover:bg-lsc-rose/10
                          motion-safe:transition-colors
                          focus:outline-none focus:ring-2 focus:ring-lsc-rose
                        "
                        aria-label={t('aria.adminCourses.editCourse', { title: course.title })}
                      >
                        <Edit className="w-5 h-5" aria-hidden="true" />
                      </Link>
                      <button
                        type="button"
                        onClick={() => setDuplicateTarget({ id: course.id, title: course.title })}
                        className="
                          inline-flex items-center justify-center
                          w-11 h-11 rounded-lg
                          text-lsc-dark/70 dark:text-lsc-cream/70
                          hover:bg-lsc-cream/50 dark:hover:bg-earth-700
                          motion-safe:transition-colors
                          focus:outline-none focus:ring-2 focus:ring-lsc-rose
                        "
                        aria-label={t('aria.adminCourses.duplicateCourse', { title: course.title })}
                      >
                        <Copy className="w-5 h-5" aria-hidden="true" />
                      </button>
                      <button
                        onClick={() =>
                          setDeleteConfirm({
                            id: course.id,
                            title: course.title,
                            enrollmentCount: course.enrollment_count,
                          })
                        }
                        className="
                          inline-flex items-center justify-center
                          w-11 h-11 rounded-lg
                          text-status-danger-600 dark:text-status-danger-400
                          hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/20
                          motion-safe:transition-colors
                          focus:outline-none focus:ring-2 focus:ring-status-danger-500
                        "
                        aria-label={t('aria.adminCourses.deleteCourse', { title: course.title })}
                      >
                        <Trash2 className="w-5 h-5" aria-hidden="true" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title={t('admin.adminCourses.deleteCourseTitle')}
        message={
          <span>
            {deleteConfirm && deleteConfirm.enrollmentCount > 0 && (
              <span className="block mb-2">
                <strong>{deleteConfirm.enrollmentCount}</strong>{' '}
                {t('admin.adminCourses.deleteWarningWithEnrollmentLead')}{' '}
                {t('admin.adminCourses.deleteWarningWithEnrollmentTail')}
              </span>
            )}
            <span className="block">
              {t('admin.adminCourses.deleteCourseMessage', {
                title: deleteConfirm?.title ?? '',
              })}
            </span>
            <span className="block mt-3 text-xs">
              {/* Secondary footer action: archive keeps the row (lifecycle
                  transition) instead of deleting it. confirm: true is safe —
                  this dialog already showed the enrollment-impact warning. */}
              <button
                type="button"
                onClick={() => {
                  if (deleteConfirm) handleArchiveInstead(deleteConfirm.id);
                }}
                disabled={archiving || deleting}
                aria-label={t('aria.adminCourses.archiveCourseInstead', {
                  title: deleteConfirm?.title ?? '',
                })}
                className="
                  inline-flex items-center gap-1.5
                  text-lsc-dark/70 dark:text-lsc-cream/70
                  underline decoration-dotted
                  hover:text-lsc-rose dark:hover:text-lsc-rose
                  motion-safe:transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed
                  focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded
                "
              >
                {archiving && (
                  <Loader2
                    className="w-3.5 h-3.5 motion-safe:animate-spin"
                    aria-hidden="true"
                  />
                )}
                {t('admin.adminCourses.archiveInstead')}
              </button>
            </span>
          </span>
        }
        confirmText={
          deleteConfirm && deleteConfirm.enrollmentCount > 0
            ? t('admin.adminCourses.deleteAnyway')
            : t('admin.adminCourses.deleteCourseConfirm')
        }
        cancelText={t('admin.adminCourses.deleteCourseCancel')}
        confirmVariant="danger"
        loading={deleting}
        onConfirm={() => {
          if (deleteConfirm) handleDelete(deleteConfirm.id);
        }}
        onCancel={() => setDeleteConfirm(null)}
      />

      {duplicateTarget && (
        <DuplicateCourseModal
          sourceTitle={duplicateTarget.title}
          sourceId={duplicateTarget.id}
          onCancel={() => setDuplicateTarget(null)}
          onSubmit={async (newTitle) => {
            const result = await handleDuplicate(duplicateTarget.id, newTitle);
            if (result.ok) setDuplicateTarget(null);
            return result;
          }}
          t={t}
        />
      )}
    </AdminShell>
  );
}
