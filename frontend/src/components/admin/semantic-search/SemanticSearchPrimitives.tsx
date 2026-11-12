/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ChevronDown, ChevronUp, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { ENTITY_TYPES } from './semantic-search-admin-data';
import { getEmbeddingProgress } from './semantic-search-api-helpers';

export function ProgressBar({ percent, color = 'bg-lsc-rose' }: { percent: number; color?: string }) {
  return (
    <div className="w-full bg-earth-100 dark:bg-earth-700 rounded-full h-2 overflow-hidden">
      <div
        className={`h-2 rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
      />
    </div>
  );
}

export function StatCard({
  label,
  value,
  subValue,
  color = 'text-lsc-dark dark:text-lsc-cream',
  bg = 'bg-earth-50 dark:bg-earth-700/50',
}: {
  label: string;
  value: string | number;
  subValue?: string;
  color?: string;
  bg?: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-4 text-center`}>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{label}</p>
      {subValue && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{subValue}</p>}
    </div>
  );
}

export function AccordionSection({
  id: _id,
  title,
  icon,
  badge,
  expanded,
  onToggle,
  children,
}: {
  id: string;
  title: string;
  icon: React.ReactNode;
  badge?: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-3">
          {icon}
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{title}</span>
          {badge}
        </div>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        ) : (
          <ChevronDown className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        )}
      </button>

      {expanded && (
        <div className="px-6 pb-6 border-t border-lsc-border dark:border-earth-700 pt-4">
          {children}
        </div>
      )}
    </div>
  );
}

export function EntityProgressCard({ entityType }: { entityType: typeof ENTITY_TYPES[number] }) {
  const { data: progress, isLoading } = useQuery({
    queryKey: ['embedding-progress', entityType.id],
    queryFn: () => getEmbeddingProgress(entityType.id),
    refetchInterval: (data) =>
      data?.state?.data?.status === 'running' ? 3000 : 30000,
  });

  const statusBadge = () => {
    if (!progress || progress.status === 'not_started') {
      return (
        <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 text-xs rounded-full">
          Not started
        </span>
      );
    }
    if (progress.status === 'running') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light text-xs rounded-full">
          <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
          Running
        </span>
      );
    }
    if (progress.status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 text-xs rounded-full">
          <CheckCircle className="w-3 h-3" />
          Completed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300 text-xs rounded-full">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    );
  };

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
              {entityType.label}
            </h3>
            {entityType.recommended && (
              <span className="px-1.5 py-0.5 bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light text-xs rounded">
                Recommended
              </span>
            )}
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{entityType.description}</p>
        </div>
        <div className="flex-shrink-0 ml-3">{isLoading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" /> : statusBadge()}</div>
      </div>

      {progress?.progress && (
        <div className="space-y-2">
          <ProgressBar
            percent={progress.progress.progress_percent}
            color={progress.status === 'failed' ? 'bg-status-danger-500' : 'bg-lsc-rose'}
          />
          <div className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
            <span>
              {progress.progress.embedded_count.toLocaleString()} / {progress.progress.total_count.toLocaleString()} embedded
            </span>
            <span>{progress.progress.progress_percent.toFixed(1)}%</span>
          </div>
          {progress.progress.failed_count > 0 && (
            <p className="text-xs text-status-danger-600 dark:text-status-danger-400">
              {progress.progress.failed_count} failed
            </p>
          )}
          {progress.progress.completed_at && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              Completed: {new Date(progress.progress.completed_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {!progress?.progress && !isLoading && (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          No embedding data yet. Run generation to get started.
        </p>
      )}
    </div>
  );
}
