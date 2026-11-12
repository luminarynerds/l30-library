/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ElementType } from "react";
import { Link } from "react-router-dom";
import { Clock, Zap, Coffee, Target } from "lucide-react";
import { useTranslation } from "@/i18n";
import type { RecommendedCourse } from "@/types/learning";

interface Bucket {
  courses: RecommendedCourse[];
  label: string;
  labelKey: string;
  icon: ElementType;
  pill: string;
  pillKey: string;
  colorClasses: string;
  pillClasses: string;
}

interface QuickPicksProps {
  quickPicks: {
    fiveMin: RecommendedCourse[];
    fifteenMin: RecommendedCourse[];
    thirtyMin: RecommendedCourse[];
  };
}

export function QuickPicks({ quickPicks }: QuickPicksProps) {
  const { t } = useTranslation();

  const buckets: Bucket[] = [
    {
      courses: quickPicks.fiveMin,
      label: '5 min',
      labelKey: 'learn.quickPick5min',
      icon: Zap,
      pill: '5 min',
      pillKey: 'learn.pill5min',
      colorClasses: 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800 hover:bg-status-success-100 dark:hover:bg-status-success-900/30',
      pillClasses: 'bg-status-success-200 dark:bg-status-success-800 text-status-success-800 dark:text-status-success-200',
    },
    {
      courses: quickPicks.fifteenMin,
      label: '15 min',
      labelKey: 'learn.quickPick15min',
      icon: Coffee,
      pill: '15 min',
      pillKey: 'learn.pill15min',
      colorClasses: 'bg-status-info-50 dark:bg-status-info-900/20 border-status-info-200 dark:border-status-info-800 hover:bg-status-info-100 dark:hover:bg-status-info-900/30',
      pillClasses: 'bg-status-info-200 dark:bg-status-info-800 text-status-info-800 dark:text-status-info-200',
    },
    {
      courses: quickPicks.thirtyMin,
      label: '30 min',
      labelKey: 'learn.quickPick30min',
      icon: Target,
      pill: '30 min',
      pillKey: 'learn.pill30min',
      colorClasses: 'bg-category-50 dark:bg-category-900/20 border-category-200 dark:border-category-800 hover:bg-category-100 dark:hover:bg-category-900/30',
      pillClasses: 'bg-category-200 dark:bg-category-800 text-category-800 dark:text-category-200',
    },
  ].filter(b => b.courses.length > 0);

  if (buckets.length === 0) return null;

  return (
    <section className="mb-6" aria-labelledby="quick-picks-heading">
      <h2 id="quick-picks-heading" className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
        <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        {t('learn.gotAFewMinutes', 'Got a few minutes?')}
      </h2>
      <ul className="flex flex-wrap gap-3 list-none p-0 m-0">
        {buckets.map(bucket => {
          const Icon = bucket.icon;
          const course = bucket.courses[0]!;
          return (
            <li key={bucket.labelKey}>
              <Link
                to={`/learn/course/${course.id}`}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 ${bucket.colorClasses}`}
              >
                <Icon aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${bucket.pillClasses}`}>
                  {t(bucket.pillKey, bucket.pill)}
                </span>
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-40" title={course.title}>
                  {course.title}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
