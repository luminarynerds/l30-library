/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { Scale, Star, ExternalLink, ListChecks } from 'lucide-react';
import type { Rubric } from './types';

interface Props {
  rubric: Rubric;
  linkTo?: string;
  showAssessButton?: boolean;
  onAssess?: () => void;
}

/**
 * Card component for displaying a rubric in a list.
 */
export const RubricCard: React.FC<Props> = ({
  rubric,
  linkTo,
  showAssessButton = true,
  onAssess,
}) => {
  const containerClassName =
    'bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700';

  const content = (
    <div className="p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-earth-100 dark:bg-earth-800/40 rounded-lg">
            <Scale className="h-6 w-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg line-clamp-2" title={rubric.title}>
              {rubric.title}
            </h3>
            {rubric.category && (
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                {rubric.category.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>
        {rubric.is_featured && (
          <div className="flex items-center gap-1 text-status-warning-500" title="Featured">
            <Star className="h-5 w-5 fill-current" />
          </div>
        )}
      </div>

      {rubric.description && (
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4 line-clamp-2" title={rubric.description}>
          {rubric.description}
        </p>
      )}

      {rubric.tags && rubric.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {rubric.tags.slice(0, 4).map((tag, idx) => (
            <span
              key={idx}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300"
            >
              {tag}
            </span>
          ))}
          {rubric.tags.length > 4 && (
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">+{rubric.tags.length - 4} more</span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-earth-100 dark:border-earth-700">
        <div className="flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="flex items-center gap-1">
            <ListChecks className="h-4 w-4" />
            {rubric.criteria_count || rubric.criteria?.length || 0} criteria
          </span>
          <span>
            Score: {rubric.min_score}-{rubric.max_score}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {rubric.source_url && (
            <a
              href={rubric.source_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose"
              title="View source"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
          {showAssessButton && onAssess && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onAssess();
              }}
              className="px-3 py-1.5 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light dark:hover:text-lsc-rose hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/30 rounded-lg transition-colors"
            >
              Start Assessment
            </button>
          )}
        </div>
      </div>
    </div>
  );

  if (linkTo) {
    return (
      <Link
        to={linkTo}
        className={`block ${containerClassName} hover:border-lsc-border dark:border-earth-600 dark:hover:border-lsc-rose hover:shadow-md transition-all duration-200`}
      >
        {content}
      </Link>
    );
  }

  return (
    <div className={containerClassName}>
      {content}
    </div>
  );
};

export default RubricCard;
