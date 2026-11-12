/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { GraduationCap, ChevronRight } from "lucide-react";
import { useTranslation } from "@/i18n";
import type { LearningPath } from "@/types/learning";

interface LearningPathsSectionProps {
  paths: LearningPath[];
}

export function LearningPathsSection({ paths }: LearningPathsSectionProps) {
  const { t } = useTranslation();

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <GraduationCap aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          {t('learn.learningPaths', 'Learning Paths')}
        </h2>
        <Link to="/learning-paths" className="text-sm text-lsc-rose hover:underline flex items-center gap-1">
          {t('learn.viewAll', 'View all')} <ChevronRight className="w-4 h-4" />
        </Link>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        {paths.slice(0, 2).map(path => (
          <Link key={path.id} to={`/learning-paths/${path.id}`} className="flex items-center gap-4 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md hover:border-lsc-rose dark:hover:border-lsc-rose transition-all">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-lsc-rose/20 to-lsc-brown/30 flex items-center justify-center flex-shrink-0">
              <GraduationCap aria-hidden="true" className="w-6 h-6 text-lsc-rose" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={path.title}>{path.title}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {path.total_courses} {path.total_courses === 1 ? t('learn.courseLabel', 'course') : t('learn.coursesLabel', 'courses')}
                {path.is_enrolled && path.progress !== undefined && ` \u2022 ${path.progress}% ${t('learn.complete', 'complete')}`}
              </p>
            </div>
            <ChevronRight aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </Link>
        ))}
      </div>
    </div>
  );
}
