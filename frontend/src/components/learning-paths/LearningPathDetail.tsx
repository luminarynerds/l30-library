/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react";
import { Link } from "react-router-dom";
import { CourseInPathCard } from "./CourseInPathCard";
import { Clock, BookOpen, CheckCircle, ChevronRight, Bell, BellOff } from "lucide-react";
import { useTranslation } from '@/i18n'

interface Course {
  id: number;
  course_id: number;
  course_title: string | null;
  course_thumbnail: string | null;
  is_required: boolean;
  is_completed: boolean;
  can_access: boolean;
  sort_order: number;
}

interface LearningPathDetailProps {
  title: string;
  description: string | null;
  difficulty: string | null;
  total_minutes: number | null;
  total_courses: number;
  required_courses: number;
  optional_courses: number;
  courses: Course[];
  is_enrolled: boolean;
  enrollment_progress: number;
  status: 'draft' | 'published' | 'archived';
  isAuthenticated?: boolean;
  onEnroll?: () => void;
  onJoinWaitlist?: () => void;
  waitlistJoined?: boolean;
  waitlistCount?: number;
}

export const LearningPathDetail: React.FC<LearningPathDetailProps> = ({
  title,
  description,
  difficulty,
  total_minutes,
  total_courses,
  required_courses,
  optional_courses: _optional_courses,
  courses,
  is_enrolled,
  enrollment_progress,
  status: pathStatus,
  isAuthenticated = true,
  onEnroll,
  onJoinWaitlist,
  waitlistJoined = false,
  waitlistCount = 0,
}) => {
  const { t } = useTranslation()
  const isComingSoon = pathStatus !== 'published';

  const difficultyColors = {
    beginner: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-400",
    intermediate: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300",
    advanced: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300",
  };

  const colorClass = difficultyColors[difficulty as keyof typeof difficultyColors] || "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream";

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-8 mb-6 border border-lsc-border dark:border-earth-700">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{title}</h1>
              {isComingSoon && (
                <span className="bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 px-3 py-1 rounded-full text-sm font-semibold">
                  Coming Soon
                </span>
              )}
            </div>
            {difficulty && (
              <span className={`${colorClass} px-3 py-1 rounded-full text-sm font-semibold capitalize`}>
                {difficulty}
              </span>
            )}
          </div>
          {/* Published + not enrolled + authenticated => Enroll */}
          {!isComingSoon && !is_enrolled && isAuthenticated && onEnroll && (
            <button
              onClick={onEnroll}
              className="bg-lsc-rose text-white px-6 py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 transition-colors"
            >
              Enroll Now
            </button>
          )}
          {/* Published + not enrolled + not authenticated => Sign in */}
          {!isComingSoon && !is_enrolled && !isAuthenticated && (
            <Link
              to="/account"
              className="inline-flex items-center gap-2 bg-lsc-rose text-white px-6 py-3 rounded-lg font-semibold hover:bg-lsc-rose/90 transition-colors"
            >
              Sign In to Enroll
              <ChevronRight className="w-5 h-5" />
            </Link>
          )}
          {/* Coming soon + authenticated => Waitlist */}
          {isComingSoon && isAuthenticated && onJoinWaitlist && (
            <div className="text-right">
              {waitlistJoined ? (
                <div className="flex items-center gap-2 text-status-success-700 dark:text-status-success-400">
                  <BellOff className="w-5 h-5" />
                  <span className="font-semibold">You'll be notified</span>
                </div>
              ) : (
                <button
                  onClick={onJoinWaitlist}
                  className="inline-flex items-center gap-2 bg-status-warning-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-status-warning-700 transition-colors"
                >
                  <Bell className="w-5 h-5" />
                  Notify Me
                </button>
              )}
              {waitlistCount > 0 && (
                <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
                  {waitlistCount} {waitlistCount === 1 ? 'person' : 'people'} waiting
                </p>
              )}
            </div>
          )}
          {/* Coming soon + not authenticated => Sign in to join waitlist */}
          {isComingSoon && !isAuthenticated && (
            <Link
              to="/account"
              className="inline-flex items-center gap-2 bg-status-warning-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-status-warning-700 transition-colors"
            >
              Sign In for Updates
              <ChevronRight className="w-5 h-5" />
            </Link>
          )}
          {is_enrolled && (
            <div className="text-center">
              <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{enrollment_progress}%</div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Complete</div>
            </div>
          )}
        </div>

        {description && <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{description}</p>}

        <div className="flex items-center gap-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {total_minutes !== null && total_minutes > 0 && (
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              <span>
                {total_minutes < 60
                  ? `${total_minutes} min`
                  : `${Math.round(total_minutes / 60 * 10) / 10} hours`}
              </span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            <span>{total_courses} {total_courses === 1 ? 'course' : 'courses'}</span>
          </div>
          {required_courses > 0 && (
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              <span>{required_courses} {required_courses === 1 ? 'required' : 'required'}</span>
            </div>
          )}
        </div>

        {is_enrolled && enrollment_progress > 0 && (
          <div className="mt-6">
            <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3">
              <div
                className="bg-lsc-rose h-3 rounded-full transition-all duration-300"
                style={{ width: `${enrollment_progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Courses List */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-8">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">{t('components.learningPaths.learningPathDetail.coursesInThisPath')}</h2>
        <div className="space-y-4">
          {courses.length === 0 ? (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">{t('components.learningPaths.learningPathDetail.noCoursesInThisPath')}</p>
          ) : (
            [...courses]
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((course, idx) => (
                <CourseInPathCard key={course.id} {...course} step_number={idx + 1} />
              ))
          )}
        </div>
      </div>
    </div>
  );
};
