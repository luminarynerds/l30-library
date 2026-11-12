/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { BookOpen, GraduationCap, Sparkles, Award, BarChart3, Settings } from "lucide-react";
import { useTranslation } from "@/i18n";
import { UserStatsCard } from "@/components/training";

interface LearnSidebarProps {
  isAuthenticated: boolean;
  hideGamification: boolean;
}

export function LearnSidebar({ isAuthenticated, hideGamification }: LearnSidebarProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {isAuthenticated && (
        <UserStatsCard hideGamification={hideGamification} />
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h2 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">{t('learn.quickLinks', 'Quick Links')}</h2>
        <div className="space-y-2">
          <Link to="/learn/catalog" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><BookOpen aria-hidden="true" className="w-5 h-5" />{t('learn.courseCatalog', 'Course Catalog')}</Link>
          <Link to="/learning-paths" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><GraduationCap aria-hidden="true" className="w-5 h-5" />{t('learn.learningPaths', 'Learning Paths')}</Link>
          <Link to="/learn/labs" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><Sparkles aria-hidden="true" className="w-5 h-5" />{t('learn.aiLiteracyLabs', 'AI Literacy Labs')}</Link>
          {isAuthenticated && (
            <>
              <Link to="/learn/achievements" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><Award aria-hidden="true" className="w-5 h-5" />{t('learn.myAchievements', 'My Achievements')}</Link>
              <Link to="/learn/analytics" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><BarChart3 aria-hidden="true" className="w-5 h-5" />{t('learn.analytics', 'Analytics')}</Link>
              <Link to="/account?tab=settings" className="flex items-center gap-3 p-3 rounded-xl text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors"><Settings aria-hidden="true" className="w-5 h-5" />{t('learn.accountSettings', 'Account Settings')}</Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
