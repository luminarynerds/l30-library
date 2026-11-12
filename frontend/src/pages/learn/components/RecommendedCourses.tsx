/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { Compass, TrendingUp, Clock } from "lucide-react";
import { CourseThumbnail } from "@/components/training";
import { useTranslation } from "@/i18n";
import type { RecommendedCourse } from "@/types/learning";

interface RecommendedCoursesProps {
  courses: RecommendedCourse[];
}

// Shared with the catalog card (LearnCatalogPage) so difficulty reads the same everywhere.
// Colour plus the word (never colour alone) keeps it legible for colour-blind readers.
const difficultyColors: Record<string, string> = {
  beginner: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
  intermediate: "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  advanced: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300",
};

export function RecommendedCourses({ courses }: RecommendedCoursesProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Compass aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        {t('learn.recommendedForYou', 'Recommended for You')}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map(course => (
          <Link key={course.id} to={`/learn/course/${course.id}`} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-md hover:border-lsc-rose dark:hover:border-lsc-rose transition-all group">
            <div className="relative">
              <CourseThumbnail title={course.title} size="sm" className="w-full rounded-t-xl" />
              {course.difficulty && difficultyColors[course.difficulty] && (
                <span className={`absolute bottom-2 left-2 px-2 py-0.5 rounded-full text-xs font-medium capitalize ${difficultyColors[course.difficulty]}`}>
                  {course.difficulty}
                </span>
              )}
            </div>
            <div className="p-4">
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose line-clamp-1" title={course.title}>{course.title}</h3>
              <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" aria-hidden="true" />{course.reason}
              </p>
              {course.estimated_minutes && (
                <div className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" aria-hidden="true" />{course.estimated_minutes} {t('learn.min', 'min')}</span>
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
