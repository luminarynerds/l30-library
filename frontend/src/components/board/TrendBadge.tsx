/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TrendingUp, TrendingDown } from "lucide-react";

export function TrendBadge({ value }: { value: number }) {
  if (value === 0) {
    return <span className="text-sm text-earth-600 dark:text-earth-400">0.0%</span>;
  }

  const isPositive = value > 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        isPositive
          ? "bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-300"
          : "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-300"
      }`}
    >
      <Icon className="w-3 h-3" />
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}
