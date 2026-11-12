/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * User Stats Card
 * Shows XP, level, streak without pressure
 */
import { useQuery } from '@tanstack/react-query';
import { Flame, BookOpen, Beaker, Trophy } from 'lucide-react';
import { learningApi } from './api';

interface UserStatsCardProps {
  hideGamification?: boolean;
}

export function UserStatsCard({ hideGamification = false }: UserStatsCardProps) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['my-stats'],
    queryFn: learningApi.getMyStats,
  });

  if (hideGamification) return null;

  if (isLoading || !stats) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <div className="motion-safe:animate-pulse h-24 bg-lsc-cream dark:bg-lsc-brown rounded" />
      </div>
    );
  }

  const xpForLevel = (level: number) => Math.floor(100 * Math.pow(1.5, level - 1));
  const currentLevelXp = stats.total_xp % xpForLevel(stats.level);
  const nextLevelXp = xpForLevel(stats.level);
  const xpProgress = (currentLevelXp / nextLevelXp) * 100;

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
      {/* Level & XP */}
      <div className="flex items-center gap-4 mb-6">
        <div className="w-16 h-16 rounded-full bg-lsc-cream dark:bg-lsc-dark/30 flex items-center justify-center">
          <span className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
            {stats.level}
          </span>
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Level {stats.level}</span>
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stats.total_xp} XP</span>
          </div>
          <div className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
            <div className="h-full bg-lsc-rose rounded-full transition-all" style={{ width: `${xpProgress}%` }} />
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {nextLevelXp - currentLevelXp} XP to level {stats.level + 1}
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex items-center gap-3 p-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
          <Flame aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <div>
            <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{stats.current_streak}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">day streak</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
          <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <div>
            <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{stats.lessons_completed}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">lessons</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
          <Trophy aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <div>
            <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{stats.courses_completed}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">courses</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-3 bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl">
          <Beaker aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <div>
            <p className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{stats.labs_completed}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">labs</p>
          </div>
        </div>
      </div>

      {stats.current_streak > 0 && (
        <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4">
          {stats.current_streak === stats.longest_streak
            ? "You're on your longest streak! Keep it up!"
            : `Your best: ${stats.longest_streak} days`}
        </p>
      )}
    </div>
  );
}
