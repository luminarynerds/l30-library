/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react";
import { Link } from "react-router-dom";
import { Star, Clock } from "lucide-react";
import { useTranslation } from "@/i18n";

interface CourseCollectionsProps {

  collections: Array<{
    id: string;
    title: string;
    description: string;
    icon: React.ElementType;
    courses: Array<{ id: number; title: string; difficulty?: string; estimated_minutes?: number | null; [k: string]: any }>;
  }>;
}

export function CourseCollections({ collections }: CourseCollectionsProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Star aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        {t('learn.courseCollections', 'Course Collections')}
      </h2>
      <div className="space-y-4">
        {collections.map(collection => {
          const IconComponent = collection.icon;
          return (
            <div key={collection.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
              <div className="px-5 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
                  <IconComponent aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{collection.title}</h3>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{collection.description}</p>
                </div>
              </div>
              <div className="p-4 flex gap-3 overflow-x-auto">
                {collection.courses.map(course => (
                  <Link key={course.id} to={`/learn/course/${course.id}`} className="flex-shrink-0 w-48 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg p-3 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors group">
                    <h4 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream line-clamp-2 group-hover:text-lsc-rose" title={course.title}>{course.title}</h4>
                    <div className="flex items-center gap-2 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {course.difficulty && <span className="capitalize">{course.difficulty}</span>}
                      {course.estimated_minutes && (<span className="flex items-center gap-1"><Clock className="w-3 h-3" />{course.estimated_minutes}m</span>)}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
