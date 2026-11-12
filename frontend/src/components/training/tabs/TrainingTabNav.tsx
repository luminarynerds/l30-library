/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TrainingTabNav - WAI-ARIA tablist for the staff training dashboard.
 *
 * Implements the APG tabs pattern:
 *   https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
 *
 * - Roving tabindex (selected tab is tabIndex 0, others -1)
 * - ArrowLeft/ArrowRight cycle with wrap, Home/End jump to first/last
 * - Enter/Space activate (manual activation; matches expected behavior with
 *   panels that mount data-fetching children)
 */
import React, { useCallback, useRef } from 'react';
import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';
import type { TrainingTab } from '../utils/dueDate';
import { tabIdFor, panelIdFor } from './tabIds';

export interface TrainingTabDescriptor {
  id: TrainingTab;
  label: string;
  icon: LucideIcon;
}

export interface TrainingTabNavProps {
  activeTab: TrainingTab;
  onTabChange: (tab: TrainingTab) => void;
  tabs: TrainingTabDescriptor[];
}

export function TrainingTabNav({
  activeTab,
  onTabChange,
  tabs,
}: TrainingTabNavProps): React.ReactElement {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const focusTab = useCallback((index: number) => {
    const btn = buttonRefs.current[index];
    if (btn) {
      btn.focus();
    }
  }, []);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
      const last = tabs.length - 1;
      let nextIndex: number | null = null;

      switch (event.key) {
        case 'ArrowRight':
          nextIndex = currentIndex === last ? 0 : currentIndex + 1;
          break;
        case 'ArrowLeft':
          nextIndex = currentIndex === 0 ? last : currentIndex - 1;
          break;
        case 'Home':
          nextIndex = 0;
          break;
        case 'End':
          nextIndex = last;
          break;
        case 'Enter':
        case ' ': {
          event.preventDefault();
          const current = tabs[currentIndex];
          if (current) onTabChange(current.id);
          return;
        }
        default:
          return;
      }

      if (nextIndex !== null) {
        event.preventDefault();
        const target = tabs[nextIndex];
        if (target) {
          onTabChange(target.id);
          focusTab(nextIndex);
        }
      }
    },
    [tabs, onTabChange, focusTab],
  );

  return (
    <div
      role="tablist"
      aria-label="Training sections"
      className="flex gap-1 border-b border-lsc-border dark:border-earth-700"
    >
      {tabs.map((tab, index) => {
        const isSelected = tab.id === activeTab;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              buttonRefs.current[index] = el;
            }}
            type="button"
            role="tab"
            id={tabIdFor(tab.id)}
            aria-selected={isSelected}
            aria-controls={panelIdFor(tab.id)}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={clsx(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
              isSelected
                ? 'text-lsc-rose border-lsc-rose'
                : 'text-lsc-dark/70 dark:text-lsc-cream/70 border-transparent hover:text-lsc-dark dark:hover:text-lsc-cream',
            )}
          >
            <Icon aria-hidden="true" className="w-4 h-4" />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
