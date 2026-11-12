/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { CheckCircle, Target } from 'lucide-react'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useReadingGoal } from '@/hooks/useReadingGoal'
import ReadingGoalModal from './ReadingGoalModal'
import type { ReadingStats } from '@/api/domains/content/reading-status-api'

const CURRENT_YEAR = new Date().getFullYear()

interface StatsBarProps {
  stats: ReadingStats | undefined
}

function ProgressRing({ percent }: { percent: number }) {
  const radius = 18
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - Math.min(percent, 1))

  return (
    <svg
      width={48}
      height={48}
      className="transform -rotate-90"
      aria-hidden="true"
    >
      {/* Background ring */}
      <circle
        cx={24}
        cy={24}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
        className="text-earth-200 dark:text-earth-700"
      />
      {/* Progress arc */}
      <circle
        cx={24}
        cy={24}
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth={4}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className="text-lsc-rose transition-[stroke-dashoffset] duration-500 motion-reduce:transition-none"
      />
    </svg>
  )
}

export default function StatsBar({ stats }: StatsBarProps) {
  const { isFeatureEnabled } = useOrganizationFeatures()
  const goalsEnabled = isFeatureEnabled('reading_goals_enabled')
  const { currentGoal, progress, handleSetGoal, handleRemoveGoal } =
    useReadingGoal(CURRENT_YEAR)
  const [showGoalModal, setShowGoalModal] = useState(false)

  const finishedThisYear = stats?.finished_this_year ?? 0

  const shelfCounts = [
    { label: 'Reading', count: stats?.currently_reading ?? 0 },
    { label: 'Want', count: stats?.want_to_read ?? 0 },
    { label: 'Hold', count: stats?.on_hold ?? 0 },
    { label: 'Done', count: stats?.finished ?? 0 },
    { label: 'DNF', count: stats?.did_not_finish ?? 0 },
  ]

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-4 mb-6">
      <div className="flex flex-wrap items-center gap-4">
        {/* Left: progress ring or plain count */}
        {goalsEnabled && progress ? (
          <div className="flex items-center gap-3">
            <div className="relative">
              <ProgressRing percent={progress.percent} />
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-lsc-dark dark:text-lsc-cream">
                {progress.finished_count}
              </span>
            </div>
            <div>
              <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                {progress.finished_count} of {progress.target_books} books in {CURRENT_YEAR}
              </p>
              <button
                onClick={() => setShowGoalModal(true)}
                className="text-xs text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                Edit goal
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 font-semibold text-sm text-lsc-rose dark:text-lsc-rose-light">
              <CheckCircle className="w-4 h-4" aria-hidden="true" />
              {finishedThisYear} finished this year
            </span>
            {goalsEnabled && !currentGoal && (
              <>
                <span className="text-lsc-border dark:text-earth-600" aria-hidden="true">·</span>
                <button
                  onClick={() => setShowGoalModal(true)}
                  className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light"
                >
                  <Target className="w-3.5 h-3.5" aria-hidden="true" />
                  Set a reading goal
                </button>
              </>
            )}
          </div>
        )}

        {/* Divider */}
        <span className="hidden sm:inline text-lsc-border dark:text-earth-600" aria-hidden="true">|</span>

        {/* Right: per-shelf pills */}
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {shelfCounts.map(({ label, count }) => (
            <span key={label} className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {label}: <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
            </span>
          ))}
        </div>
      </div>

      {showGoalModal && (
        <ReadingGoalModal
          year={CURRENT_YEAR}
          currentTarget={currentGoal?.target_books}
          onSave={handleSetGoal}
          onRemove={currentGoal ? handleRemoveGoal : undefined}
          onClose={() => setShowGoalModal(false)}
        />
      )}
    </div>
  )
}
