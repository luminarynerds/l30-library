/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { useTranslation } from "@/i18n";
import type { EnrolledCourse } from "@/types/learning";

interface InProgressCoursesProps {
  courses: EnrolledCourse[];
}

export function InProgressCourses({ courses }: InProgressCoursesProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">{t('learn.continueLearning', 'Continue Learning')}</h2>
      <div className="space-y-4">
        {courses.map(({ course, progress_percentage, completed_lessons, total_lessons }) => {
          const pct = Math.round(progress_percentage);
          return (
            <Link key={course.id} to={`/learn/course/${course.id}`} className="block bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-md transition-shadow">
              <div className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">{course.title}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={course.description}>{course.description}</p>
                  </div>
                  <div className="flex-shrink-0 w-12 h-12 rounded-full bg-lsc-cream dark:bg-lsc-dark/30 flex items-center justify-center">
                    <span
                      className="text-lg font-bold text-lsc-rose dark:text-lsc-rose-light"
                      aria-label={`${pct}% complete`}
                    >
                      {pct}%
                    </span>
                  </div>
                </div>
                <div className="mt-4">
                  <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    <span>{completed_lessons} {t('learn.of', 'of')} {total_lessons} {t('learn.lessons', 'lessons')}</span>
                    {course.estimated_minutes && <span>~{course.estimated_minutes} {t('learn.minTotal', 'min total')}</span>}
                  </div>
                  <div
                    className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden"
                    role="progressbar"
                    aria-valuenow={pct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={`${course.title}: ${pct}% complete`}
                  >
                    <div className="h-full bg-lsc-rose rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
