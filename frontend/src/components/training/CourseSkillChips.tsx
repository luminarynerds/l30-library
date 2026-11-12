/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CourseSkillChips — Wave 5 skill chip strip.
 *
 * Renders the skills a course builds as a small list of chips. Two modes:
 *   - Visual-only (no `onSkillClick`): plain `<span>` chips inside `<li>`.
 *     Used on the trainings-table CourseRow where the row is itself a link
 *     and a button-inside-link would be confusing UX.
 *   - Interactive (`onSkillClick` provided): real `<button type="button">`
 *     chips. Used wherever a chip should navigate / filter.
 *
 * Accessibility (CLAUDE.md + nd-first):
 *   - `<ul>/<li>` semantics; we deliberately do NOT add `role="list"` because
 *     Safari/VoiceOver drops the implicit role on flex containers in some
 *     versions, but the explicit role can also strip the implicit semantics
 *     in older AT — leaving native semantics alone is safer here.
 *   - The level number (L3) is rendered as text, NOT a colored dot, so it's
 *     never color-only meaning (WCAG 1.4.1).
 *   - Chip color tokens (`bg-lsc-cream text-lsc-dark` /
 *     `dark:bg-earth-700 dark:text-lsc-cream`) clear WCAG AA at 4.5:1.
 *   - Each interactive chip has a full plain-language `aria-label` so
 *     screen-reader users hear "Skill: X, taught at level 3 of 5" instead
 *     of just "X L3".
 *   - Empty `skills` → render nothing (chips are optional context, not a
 *     content section that needs an empty state).
 */
import React from 'react';
import type { SkillBrief } from './api';

export interface CourseSkillChipsProps {
  skills: SkillBrief[];
  /**
   * If provided, chips render as `<button>` and call this on click.
   * If omitted, chips render as `<span>` (visual-only) — preferred when the
   * surrounding container is itself a link/clickable row.
   */
  onSkillClick?: (skill: SkillBrief) => void;
  /** Optional className passthrough for layout tweaks at call sites. */
  className?: string;
}

export function CourseSkillChips({
  skills,
  onSkillClick,
  className,
}: CourseSkillChipsProps): React.ReactElement | null {
  if (!skills || skills.length === 0) {
    return null;
  }

  const ulClass = `flex flex-wrap gap-1.5${className ? ` ${className}` : ''}`;

  return (
    <ul className={ulClass}>
      {skills.map((skill) => {
        const chipBase =
          'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ' +
          'bg-lsc-cream text-lsc-dark dark:bg-earth-700 dark:text-lsc-cream';

        if (onSkillClick) {
          return (
            <li key={skill.id}>
              <button
                type="button"
                onClick={() => onSkillClick(skill)}
                aria-label={`Skill: ${skill.name}, taught at level ${skill.level_taught} of 5`}
                className={`${chipBase} hover:bg-lsc-rose/10 dark:hover:bg-earth-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2`}
              >
                <span>{skill.name}</span>
                <span
                  className="text-lsc-dark/60 dark:text-lsc-cream/60"
                  aria-hidden="true"
                >
                  L{skill.level_taught}
                </span>
              </button>
            </li>
          );
        }

        // Visual-only fallback — span chips, no interactivity.
        return (
          <li key={skill.id}>
            <span
              aria-label={`Skill: ${skill.name}, taught at level ${skill.level_taught} of 5`}
              className={chipBase}
            >
              <span>{skill.name}</span>
              <span
                className="text-lsc-dark/60 dark:text-lsc-cream/60"
                aria-hidden="true"
              >
                L{skill.level_taught}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default CourseSkillChips;
