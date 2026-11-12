/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { Search, BookOpen, ChevronRight } from "lucide-react";
import { useTranslation } from "@/i18n";

interface EmptyStateProps {
  isAuthenticated: boolean;
  searchTerm: string;
  hasEnrolledCourses: boolean;
  onClearSearch: () => void;
}

export function EmptyState({ isAuthenticated, searchTerm, hasEnrolledCourses, onClearSearch }: EmptyStateProps) {
  const { t } = useTranslation();

  if (hasEnrolledCourses && searchTerm) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
        <Search aria-hidden="true" className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learn.noCoursesMatch', 'No courses match')} &ldquo;{searchTerm}&rdquo;</p>
        <button onClick={onClearSearch} className="text-sm text-lsc-rose hover:underline mt-2">{t('learn.clearSearch', 'Clear search')}</button>
      </div>
    );
  }

  if (!hasEnrolledCourses && isAuthenticated) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
        <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('learn.readyToStartLearning')}</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('learn.exploreOurCoursesAndFind')}</p>
        <Link to="/learn/catalog" className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-6 py-3 rounded-xl font-medium">
          {t('learn.exploreCourses', 'Explore Courses')} <ChevronRight aria-hidden="true" className="w-5 h-5" />
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
      <BookOpen aria-hidden="true" className="w-16 h-16 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" />
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('learn.registerToTakeClasses')}</h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('learn.browseFreelyBlurb', 'Browse our courses freely. Create a free account to enroll in classes and track your progress.')}</p>
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Link to="/account" className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white px-6 py-3 rounded-xl font-medium">
          {t('learn.createFreeAccount', 'Create Free Account')} <ChevronRight aria-hidden="true" className="w-5 h-5" />
        </Link>
        <Link to="/learn/catalog" className="inline-flex items-center gap-2 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream px-6 py-3 rounded-xl font-medium">
          {t('learn.browseCourses', 'Browse Courses')}
        </Link>
      </div>
    </div>
  );
}
