/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { QuizResult } from '../lesson-types'

interface Props {
  quizResult: QuizResult | null
  visible: boolean
}

function recommendationFor(weightedScore: number): string {
  if (weightedScore > 35) {
    return "Start with Course 3: The Scanner & The Stack -- you're ready to build tools, and the library needs you to."
  }
  if (weightedScore > 20) {
    return "Start with Course 2: The Reference Interview vs. The Chatbot -- you're ready to test your judgment against the machine."
  }
  return 'Start with Course 1: AI for the Exhausted -- designed for skeptical and overworked staff who want relevance before theory.'
}

export function PlacementRecommendation({ quizResult, visible }: Props) {
  if (!visible || !quizResult) return null
  const ws = quizResult.weighted_score ?? 0
  if (ws <= 0) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="mt-6 p-4 bg-lsc-cream dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700"
    >
      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        Your Recommended Starting Point
      </h3>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{recommendationFor(ws)}</p>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2">
        This is a suggestion, not a gate. You are in charge of your pace.
      </p>
    </div>
  )
}
