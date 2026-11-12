/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import type { SortField, SortDirection } from '../utils/dueDate';

export interface SortableThProps {
  label: string;
  sortKey: SortField;
  currentSort: SortField;
  currentDir: SortDirection;
  onSort: (key: SortField) => void;
}

export function SortableTh({
  label,
  sortKey,
  currentSort,
  currentDir,
  onSort,
}: SortableThProps): React.ReactElement {
  const isActive = currentSort === sortKey;
  const ariaSort: 'ascending' | 'descending' | 'none' = isActive
    ? currentDir === 'asc'
      ? 'ascending'
      : 'descending'
    : 'none';

  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className="px-4 py-3 text-left text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70"
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className="inline-flex items-center gap-1 hover:text-lsc-dark dark:hover:text-lsc-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded-sm"
      >
        <span>{label}</span>
        {isActive &&
          (currentDir === 'asc' ? (
            <ChevronUp aria-hidden="true" className="w-4 h-4" />
          ) : (
            <ChevronDown aria-hidden="true" className="w-4 h-4" />
          ))}
      </button>
    </th>
  );
}

export default SortableTh;
