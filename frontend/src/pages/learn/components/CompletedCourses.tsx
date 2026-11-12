/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom";
import { CheckCircle, Award, ChevronRight } from "lucide-react";
import { useTranslation } from "@/i18n";
import type { EnrolledCourse } from "@/types/learning";

interface CompletedCoursesProps {
  courses: EnrolledCourse[];
}

export function CompletedCourses({ courses }: CompletedCoursesProps) {
  const { t } = useTranslation();

  return (
    <div>
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <CheckCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        {t('learn.completedHeading', 'Completed')}
      </h2>
      <div className="grid sm:grid-cols-2 gap-4">
        {courses.map(({ course }) => (
          <Link key={course.id} to={`/learn/course/${course.id}`} className="flex items-center gap-4 p-4 bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 transition-colors">
            <Award aria-hidden="true" className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-lsc-dark dark:text-earth-300 truncate" title={course.title}>{course.title}</h3>
              <p className="text-xs text-lsc-rose dark:text-lsc-rose-light">{t('learn.viewCertificate', 'View certificate')}</p>
            </div>
            <ChevronRight aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </Link>
        ))}
      </div>
    </div>
  );
}
