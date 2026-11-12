/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react";
import { LearningPathCard } from "./LearningPathCard";
import { useTranslation } from '@/i18n'

interface LearningPath {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  difficulty: string | null;
  estimated_hours: number | null;
  total_courses?: number;
  progress?: number;
  is_enrolled?: boolean;
  status?: "draft" | "published" | "archived";
}

interface LearningPathListProps {
  paths: LearningPath[];
  loading?: boolean;
}

export const LearningPathList: React.FC<LearningPathListProps> = ({ paths, loading = false }) => {
  const { t } = useTranslation()
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((n) => (
          <div key={n} className="bg-earth-200 dark:bg-earth-600 rounded-lg h-96 motion-safe:animate-pulse" />
        ))}
      </div>
    );
  }

  if (!paths || paths.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg">{t('components.learningPaths.learningPathList.noLearningPathsAvailableYet')}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {paths.map((path) => (
        <LearningPathCard key={path.id} {...path} />
      ))}
    </div>
  );
};
