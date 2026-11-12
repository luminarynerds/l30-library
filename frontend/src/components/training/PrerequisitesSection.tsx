/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link2, Loader2, Check } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { AvailableCourse, CourseFormData } from './training-types';

interface Props {
  formData: CourseFormData;
  availableCourses: AvailableCourse[];
  loadingCourses: boolean;
  isEdit: boolean;
  onToggle: (courseId: number) => void;
  onClearAll: () => void;
}

export default function PrerequisitesSection({
  formData,
  availableCourses,
  loadingCourses,
  isEdit,
  onToggle,
  onClearAll,
}: Props) {
  const { t } = useTranslation();

  return (
    <section
      className="
        bg-lsc-white dark:bg-earth-800
        shadow-md rounded-xl p-6 md:p-8
        border border-lsc-border dark:border-earth-700
        mb-8
      "
      aria-labelledby="prerequisites-heading"
    >
      <div className="mb-6">
        <h2
          id="prerequisites-heading"
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"
        >
          <Link2 className="w-5 h-5" aria-hidden="true" />
          Prerequisites
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          Select courses that learners must complete before enrolling in this course.
          This helps create structured learning paths.
        </p>
      </div>

      {loadingCourses ? (
        <div className="flex items-center justify-center py-8">
          <Loader2
            className="w-6 h-6 motion-safe:animate-spin text-lsc-rose"
            aria-hidden="true"
          />
          <span className="ml-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            Loading courses...
          </span>
        </div>
      ) : availableCourses.length === 0 ? (
        <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
          No other courses available to set as prerequisites.
          {!isEdit && ' Create this course first, then edit it to add prerequisites.'}
        </p>
      ) : (
        <div
          className="space-y-2"
          role="group"
          aria-label={t('aria.adminCourseForm.selectPrerequisiteCourses')}
        >
          {formData.prerequisite_course_ids.length > 0 && (
            <p
              className="text-sm text-lsc-rose font-medium mb-3"
              aria-live="polite"
            >
              {formData.prerequisite_course_ids.length} prerequisite
              {formData.prerequisite_course_ids.length === 1 ? '' : 's'} selected
            </p>
          )}

          <ul className="divide-y divide-lsc-border dark:divide-earth-700">
            {availableCourses.map((course) => {
              const isSelected = formData.prerequisite_course_ids.includes(course.id);
              return (
                <li key={course.id}>
                  <button
                    type="button"
                    onClick={() => onToggle(course.id)}
                    className={`
                      w-full flex items-center gap-4 p-4 text-left
                      rounded-lg motion-safe:transition-colors
                      focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-inset
                      min-h-[52px]
                      ${
                        isSelected
                          ? 'bg-lsc-rose/10 border-2 border-lsc-rose'
                          : 'hover:bg-lsc-cream dark:hover:bg-earth-700 border-2 border-transparent'
                      }
                    `}
                    aria-pressed={isSelected}
                    aria-label={`${course.title} - ${course.difficulty} level${isSelected ? ' (selected as prerequisite)' : ''}`}
                  >
                    <span
                      className={`
                        flex-shrink-0 w-6 h-6 rounded-lg border-2
                        flex items-center justify-center
                        motion-safe:transition-all
                        ${
                          isSelected
                            ? 'bg-lsc-rose border-lsc-rose'
                            : 'border-lsc-border dark:border-earth-700'
                        }
                      `}
                      aria-hidden="true"
                    >
                      {isSelected && <Check className="w-4 h-4 text-white" />}
                    </span>

                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={course.title}>
                        {course.title}
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                        {course.difficulty} level
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          {formData.prerequisite_course_ids.length > 0 && (
            <div className="pt-4">
              <button
                type="button"
                onClick={onClearAll}
                className="
                  text-sm text-status-danger-600 dark:text-status-danger-400
                  hover:underline focus:outline-none focus:underline
                  min-h-[44px] px-2
                "
              >
                Clear all prerequisites
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
