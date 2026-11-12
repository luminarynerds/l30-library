/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Micro Tasks Component
 * Breaks lessons into small, manageable steps for executive function support
 */
import { CheckCircle2, Circle } from 'lucide-react';

interface MicroTask {
  id: string;
  label: string;
  completed: boolean;
}

interface MicroTasksProps {
  tasks: MicroTask[];
  onTaskComplete?: (taskId: string) => void;
  showProgress?: boolean;
}

export function MicroTasks({ tasks, onTaskComplete, showProgress = true }: MicroTasksProps) {
  const completedCount = tasks.filter((t) => t.completed).length;
  const totalCount = tasks.length;
  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;

  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Your Progress</h3>
        {showProgress && (
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {completedCount} of {totalCount} steps
          </span>
        )}
      </div>

      {showProgress && (
        <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2 mb-4">
          <div
            className="bg-lsc-rose h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <ul className="space-y-2">
        {tasks.map((task) => (
          <li
            key={task.id}
            className={`flex items-start gap-3 p-2 rounded-xl ${
              task.completed ? 'bg-lsc-cream dark:bg-lsc-brown/30' : 'bg-lsc-white dark:bg-lsc-brown'
            }`}
          >
            <button
              onClick={() => !task.completed && onTaskComplete?.(task.id)}
              className="mt-0.5 flex-shrink-0"
              aria-label={task.completed ? 'Completed' : 'Mark as complete'}
            >
              {task.completed ? (
                <CheckCircle2 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              ) : (
                <Circle aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors" />
              )}
            </button>
            <span className={`flex-1 ${task.completed ? 'text-lsc-rose dark:text-lsc-cream/70 line-through' : 'text-lsc-dark dark:text-lsc-cream'}`}>
              {task.label}
            </span>
          </li>
        ))}
      </ul>

      {completedCount === totalCount && totalCount > 0 && (
        <div className="mt-4 p-3 bg-lsc-cream dark:bg-lsc-brown/40 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-earth-300 text-sm">
          Great job! You've completed all the steps!
        </div>
      )}
    </div>
  );
}
