/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react";
import { Link } from "react-router-dom";
import { Check, Lock, BookOpen } from "lucide-react";

interface CourseInPathCardProps {
  course_id: number;
  course_title: string | null;
  course_thumbnail: string | null;
  is_required: boolean;
  is_completed: boolean;
  can_access: boolean;
  sort_order: number;
  step_number: number;
}

export const CourseInPathCard: React.FC<CourseInPathCardProps> = ({
  course_id,
  course_title,
  course_thumbnail,
  is_required,
  is_completed,
  can_access,
  step_number,
}) => {
  const cardClasses = `
    flex items-center gap-4 p-4 rounded-lg border-2 transition-all
    ${is_completed ? "bg-status-success-50 dark:bg-status-success-900/20 border-status-success-300 dark:border-status-success-700" : "bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700"}
    ${can_access && !is_completed ? "hover:border-lsc-rose dark:hover:border-lsc-rose cursor-pointer" : ""}
    ${!can_access ? "opacity-60" : ""}
  `;

  const content = (
    <>
      <div className="flex-shrink-0">
        <div className="w-16 h-16 rounded-lg bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center overflow-hidden">
          {course_thumbnail ? (
            <img src={course_thumbnail} alt={course_title || ""} className="w-full h-full object-cover" />
          ) : (
            <BookOpen className="w-8 h-8 text-lsc-rose" />
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Step {step_number}</span>
          {!is_required && (
            <span className="text-xs bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream px-2 py-0.5 rounded">Optional</span>
          )}
        </div>
        <h4 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={course_title || `Course #${course_id}`}>
          {course_title || `Course #${course_id}`}
        </h4>
      </div>

      <div className="flex-shrink-0">
        {is_completed ? (
          <div className="w-10 h-10 rounded-full bg-status-success-500 flex items-center justify-center">
            <Check className="w-6 h-6 text-white" />
          </div>
        ) : !can_access ? (
          <div className="w-10 h-10 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center">
            <Lock className="w-6 h-6 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </div>
        ) : null}
      </div>
    </>
  );

  if (can_access && !is_completed) {
    return (
      <Link to={`/learn/course/${course_id}`} className={cardClasses}>
        {content}
      </Link>
    );
  }

  return <div className={cardClasses}>{content}</div>;
};
