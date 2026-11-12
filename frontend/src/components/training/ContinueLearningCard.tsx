/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Continue Learning Card
 * Shows enrolled courses with progress
 */
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, ChevronRight, Clock, CheckCircle } from 'lucide-react';
import { learningApi } from './api';
import { useTranslation } from '@/i18n'

export function ContinueLearningCard() {
  const { t } = useTranslation()
  const { data: courses, isLoading, error } = useQuery({
    queryKey: ['my-courses'],
    queryFn: learningApi.getMyCourses,
  });

  if (isLoading) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <div className="motion-safe:animate-pulse space-y-4">
          <div className="h-6 bg-lsc-cream dark:bg-lsc-brown rounded w-48" />
          <div className="h-24 bg-lsc-cream dark:bg-lsc-brown rounded" />
        </div>
      </div>
    );
  }

  if (error || !courses?.length) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <div className="text-center py-8">
          <BookOpen aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">No courses yet</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('components.training.continueLearningCard.startLearningSomethingNew')}</p>
          <Link
            to="/learn/catalog"
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose"
          >
            Browse Courses <ChevronRight aria-hidden="true" className="w-4 h-4" />
          </Link>
        </div>
      </div>
    );
  }

  const inProgress = courses.filter(c => !c.enrollment.completed_at);
  const completed = courses.filter(c => c.enrollment.completed_at);

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        Continue Learning
      </h2>

      {inProgress.length > 0 && (
        <div className="space-y-3 mb-6">
          {inProgress.slice(0, 3).map((cp) => (
            <Link
              key={cp.course.id}
              to={`/learn/course/${cp.course.id}`}
              className="block p-4 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={cp.course.title}>
                    {cp.course.title}
                  </h3>
                  <div className="flex items-center gap-3 mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span>{cp.completed_lessons}/{cp.total_lessons} lessons</span>
                    {cp.course.estimated_minutes && (
                      <span className="flex items-center gap-1">
                        <Clock aria-hidden="true" className="w-3 h-3" />
                        {cp.course.estimated_minutes} min
                      </span>
                    )}
                  </div>
                  <div className="mt-2 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                    <div
                      className="h-full bg-lsc-rose rounded-full transition-all"
                      style={{ width: `${cp.progress_percentage}%` }}
                    />
                  </div>
                </div>
                <ChevronRight aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0" />
              </div>
            </Link>
          ))}
        </div>
      )}

      {completed.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2 flex items-center gap-2">
            <CheckCircle aria-hidden="true" className="w-4 h-4 text-lsc-rose" />
            Completed ({completed.length})
          </h3>
          <div className="space-y-2">
            {completed.slice(0, 2).map((cp) => (
              <Link
                key={cp.course.id}
                to={`/learn/course/${cp.course.id}`}
                className="block p-3 bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl text-lsc-rose dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30"
              >
                {cp.course.title}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
