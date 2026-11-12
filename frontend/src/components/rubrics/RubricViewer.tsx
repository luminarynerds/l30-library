/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';
import { ExternalLink, Info, Scale } from 'lucide-react';
import type { Rubric } from './types';
import { useTranslation } from '@/i18n'

interface Props {
  rubric: Rubric;
  showAttribution?: boolean;
  compact?: boolean;
}

/**
 * Displays a rubric in a clean, accessible grid format.
 * Shows criteria as rows with level descriptors in columns.
 */
export const RubricViewer: React.FC<Props> = ({
  rubric,
  showAttribution = true,
  compact = false,
}) => {
  const { t } = useTranslation()
  const criteria = rubric.criteria || [];
  const levels = Object.keys(rubric.level_labels).sort((a, b) => Number(b) - Number(a));

  if (criteria.length === 0) {
    return (
      <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Scale className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>{t('components.rubrics.rubricViewer.thisRubricHasNoCriteria')}</p>
      </div>
    );
  }

  return (
    <div className="rubric-viewer">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {rubric.title}
        </h2>
        {rubric.description && (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {rubric.description}
          </p>
        )}
        {rubric.tags && rubric.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {rubric.tags.map((tag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-lsc-rose-light/80"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Rubric Grid */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse border border-lsc-border dark:border-earth-700">
          <thead>
            <tr className="bg-earth-100 dark:bg-earth-800">
              <th className="border border-lsc-border dark:border-earth-700 px-4 py-3 text-left font-semibold text-lsc-dark dark:text-lsc-cream min-w-[200px]">
                Criteria
              </th>
              {levels.map((level) => (
                <th
                  key={level}
                  className="border border-lsc-border dark:border-earth-700 px-4 py-3 text-center font-semibold text-lsc-dark dark:text-lsc-cream min-w-[180px]"
                >
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-lg">{rubric.level_labels?.[level] || `Level ${level}`}</span>
                    <span className="text-sm font-normal text-lsc-dark/70 dark:text-lsc-cream/70">
                      ({level})
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {criteria.map((criterion, idx) => (
              <tr
                key={criterion.id}
                className={idx % 2 === 0 ? 'bg-lsc-white dark:bg-earth-900' : 'bg-earth-50 dark:bg-earth-800'}
              >
                <td className="border border-lsc-border dark:border-earth-700 px-4 py-4 align-top">
                  <div className="font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                    {criterion.name}
                  </div>
                  {criterion.description && !compact && (
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {criterion.description}
                    </div>
                  )}
                  {criterion.weight > 1 && (
                    <div className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-1">
                      Weight: {criterion.weight}x
                    </div>
                  )}
                </td>
                {levels.map((level) => {
                  const descriptors = criterion.levels[level] || [];
                  return (
                    <td
                      key={level}
                      className="border border-lsc-border dark:border-earth-700 px-4 py-4 align-top text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                    >
                      {descriptors.length > 0 ? (
                        <ul className={`${compact ? 'list-none space-y-1' : 'list-disc list-inside space-y-2'}`}>
                          {descriptors.map((desc, i) => (
                            <li key={i} className={compact ? '' : 'leading-relaxed'}>
                              {desc}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70 italic">Not specified</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Attribution */}
      {showAttribution && rubric.source_attribution && (
        <div className="mt-6 p-4 bg-earth-50 dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-earth-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {rubric.source_attribution}
              </p>
              {rubric.source_url && (
                <a
                  href={rubric.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light dark:hover:text-lsc-rose mt-2"
                >
                  View original source
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RubricViewer;
