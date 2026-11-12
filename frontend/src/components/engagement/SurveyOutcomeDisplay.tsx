/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Award, ExternalLink, Heart, Lightbulb } from 'lucide-react'
import type { Survey, SurveyResponseResult } from '@/api/domains/engagement'

interface Props {
  survey: Survey
  result: SurveyResponseResult
}

export function SurveyOutcomeDisplay({ survey, result }: Props) {
  const outcomes = result.outcomes
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden border border-lsc-border dark:border-earth-700">
      <div className="p-6 md:p-8 space-y-5">
        <header className="space-y-1">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Thank you
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Your response was recorded for "{survey.title}".
          </p>
        </header>

        {result.derived_track && (
          <Banner tone="info" icon={<Lightbulb className="w-5 h-5" />}>
            <strong>Recommended track:</strong>{' '}
            <span className="font-mono">{result.derived_track}</span>
          </Banner>
        )}

        {result.score !== null && (
          <Banner tone="muted">
            <strong>Score:</strong> {result.score}
          </Banner>
        )}

        {outcomes.length === 0 ? null : (
          <ul className="space-y-3">
            {outcomes.map((o, idx) => (
              <li key={idx}>
                <OutcomeCard outcome={o} />
              </li>
            ))}
          </ul>
        )}

        {result.blocked && (
          <Banner tone="warn">
            Some answers suggest a quick review may help. We've queued a
            short remedial lesson for you.
          </Banner>
        )}
      </div>
    </div>
  )
}

function OutcomeCard({
  outcome,
}: {
  outcome: { outcome_type: string; target: string | null; status: string }
}) {
  const { outcome_type, target } = outcome

  if (outcome_type === 'badge_awarded') {
    return (
      <div className="flex items-start gap-3 p-4 rounded-xl bg-lsc-rose/10 border border-lsc-rose">
        <Award className="w-6 h-6 text-lsc-rose shrink-0" />
        <div>
          <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Badge earned
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {target ? <code>{target}</code> : 'Civic engagement milestone'}
          </p>
        </div>
      </div>
    )
  }

  if (outcome_type === 'civic_email_sent') {
    return (
      <div className="flex items-start gap-3 p-4 rounded-xl bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700">
        <Heart className="w-6 h-6 text-lsc-rose shrink-0" />
        <div className="flex-1">
          <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            We've sent you a link to get involved
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Check your inbox for next steps.
          </p>
          {target && (
            <a
              href={target}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-sm text-lsc-rose hover:underline"
            >
              Open now <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    )
  }

  if (outcome_type === 'peer_tip_shown') {
    return (
      <div className="flex items-start gap-3 p-4 rounded-xl bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700">
        <Lightbulb className="w-6 h-6 text-lsc-rose shrink-0" />
        <div>
          <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            A tip from your peers
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {target || 'Take another look at this section when you have a minute.'}
          </p>
        </div>
      </div>
    )
  }

  if (outcome_type === 'remedial_lesson_queued') {
    return (
      <div className="flex items-start gap-3 p-4 rounded-xl bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700">
        <Lightbulb className="w-6 h-6 text-lsc-rose shrink-0" />
        <div>
          <p className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            A short refresher is ready
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            We queued lesson{' '}
            <code className="text-xs">{target}</code> for you.
          </p>
        </div>
      </div>
    )
  }

  return null
}

function Banner({
  tone,
  icon,
  children,
}: {
  tone: 'info' | 'warn' | 'muted'
  icon?: React.ReactNode
  children: React.ReactNode
}) {
  const cls =
    tone === 'warn'
      ? 'bg-lsc-cream dark:bg-earth-900 border-lsc-rose'
      : tone === 'info'
      ? 'bg-lsc-rose/10 border-lsc-rose'
      : 'bg-lsc-cream dark:bg-earth-900 border-lsc-border dark:border-earth-700'
  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border text-lsc-dark dark:text-lsc-cream ${cls}`}
    >
      {icon}
      <div className="text-sm">{children}</div>
    </div>
  )
}
