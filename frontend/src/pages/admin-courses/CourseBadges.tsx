/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users, Shield, ShieldAlert } from 'lucide-react';

// Access level badge: outline/text-with-icon (demoted from solid fill)
export function AccessLevelBadge({ level, t }: { level: string; t: (k: string) => string }) {
  const config = {
    patron: {
      icon: Users,
      label: t('admin.adminCourses.accessPatron'),
      classes:
        'border border-earth-300 text-earth-800 dark:border-earth-600 dark:text-lsc-cream/90',
    },
    staff: {
      icon: Shield,
      label: t('admin.adminCourses.accessStaff'),
      classes:
        'border border-category-300 text-category-800 dark:border-category-600 dark:text-category-300',
    },
    admin: {
      icon: ShieldAlert,
      label: t('admin.adminCourses.accessAdmin'),
      classes:
        'border border-status-danger-300 text-status-danger-800 dark:border-status-danger-600 dark:text-status-danger-300',
    },
  }[level] || {
    icon: Users,
    label: level,
    classes: 'border border-earth-300 text-earth-800 dark:border-earth-600 dark:text-earth-200',
  };

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.classes}`}
    >
      <Icon className="w-3 h-3" aria-hidden="true" />
      {config.label}
    </span>
  );
}

// Difficulty badge: outline + ascending bars glyph (1/2/3 levels)
export function DifficultyBadge({ difficulty, t }: { difficulty?: string; t: (k: string) => string }) {
  if (!difficulty) return <span className="text-lsc-dark/70 dark:text-lsc-cream/70">-</span>;

  const levelMap: Record<string, { level: 1 | 2 | 3; labelKey: string; classes: string }> = {
    beginner: {
      level: 1,
      labelKey: 'admin.adminCourses.difficultyBeginner',
      classes:
        'border border-status-success-300 text-status-success-800 dark:border-status-success-600 dark:text-status-success-300',
    },
    intermediate: {
      level: 2,
      labelKey: 'admin.adminCourses.difficultyIntermediate',
      classes:
        'border border-status-warning-300 text-status-warning-800 dark:border-status-warning-600 dark:text-status-warning-300',
    },
    advanced: {
      level: 3,
      labelKey: 'admin.adminCourses.difficultyAdvanced',
      classes:
        'border border-status-danger-300 text-status-danger-800 dark:border-status-danger-600 dark:text-status-danger-300',
    },
  };

  const config = levelMap[difficulty] || {
    level: 1 as const,
    labelKey: '',
    classes: 'border border-earth-300 text-earth-800 dark:border-earth-600 dark:text-earth-200',
  };

  const label = config.labelKey ? t(config.labelKey) : difficulty;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.classes}`}
    >
      <span aria-hidden="true" className="inline-flex items-end gap-px h-3">
        <span
          className={`w-0.5 h-1 ${
            config.level >= 1 ? 'bg-current' : 'bg-current opacity-20'
          }`}
        />
        <span
          className={`w-0.5 h-2 ${
            config.level >= 2 ? 'bg-current' : 'bg-current opacity-20'
          }`}
        />
        <span
          className={`w-0.5 h-3 ${
            config.level >= 3 ? 'bg-current' : 'bg-current opacity-20'
          }`}
        />
      </span>
      <span className="capitalize">{label}</span>
    </span>
  );
}
