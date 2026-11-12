/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Gentle Progress Component
 * Shows progress in an encouraging, non-pressuring way
 */
import { CheckCircle2, TrendingUp } from 'lucide-react';

interface GentleProgressProps {
  completed: number;
  total: number;
  showPercentage?: boolean;
}

export function GentleProgress({
  completed,
  total,
  showPercentage = false,
}: GentleProgressProps) {
  const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

  const getMessage = () => {
    if (completed === 0) return "You're just getting started! Take your time.";
    if (completed === total) return "Amazing! You've completed everything!";
    if (percentage >= 75) return `You're almost there! ${completed} of ${total} completed.`;
    if (percentage >= 50) return `Great progress! You've completed ${completed} lessons.`;
    if (percentage >= 25) return `Nice work! You've completed ${completed} of ${total} lessons.`;
    return `You've completed ${completed} lesson${completed !== 1 ? 's' : ''}! Keep going at your own pace.`;
  };

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/30 border border-lsc-border dark:border-earth-700 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {completed === total ? (
            <CheckCircle2 className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          ) : (
            <TrendingUp aria-hidden="true" className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          )}
        </div>
        <div className="flex-1">
          <p className="text-lsc-dark dark:text-earth-300 font-medium mb-1">{getMessage()}</p>
          {showPercentage && (
            <div className="text-sm text-lsc-rose dark:text-lsc-cream/70">{percentage}% complete</div>
          )}
        </div>
      </div>
    </div>
  );
}
