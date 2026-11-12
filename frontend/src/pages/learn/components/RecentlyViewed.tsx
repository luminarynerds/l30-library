/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { History } from "lucide-react";
import { useTranslation } from "@/i18n";
import type { RecentlyViewedCourse } from "@/types/learning";

interface RecentlyViewedProps {
  courses: RecentlyViewedCourse[];
}

export function RecentlyViewed({ courses }: RecentlyViewedProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <History aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        {t('learn.recentlyViewed', 'Recently Viewed')}
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {courses.map(course => (
          <Link key={course.id} to={`/learn/course/${course.id}`} className="flex-shrink-0 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors">
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream whitespace-nowrap">{course.title}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
