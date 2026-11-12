/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertCircle } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { wrongnessLog, wrongnessLogReviewedDate } from '../data/wrongnessLog'

function formatEntryDate(iso: string): string {
  // Construct in UTC so the YYYY-MM-DD never shifts a day in the user's locale.
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  const date = new Date(Date.UTC(y, m - 1, d))
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export default function WrongnessLogSection(): React.ReactElement {
  const { t } = useTranslation()
  const hasEntries = wrongnessLog.length > 0

  return (
    <section id="wrongness" aria-labelledby="wrongness-heading" className="scroll-mt-24">
      <h2
        id="wrongness-heading"
        className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3"
      >
        {t('aITools.wrongnessHeading', 'When the AI was wrong')}
      </h2>
      <p className="text-lsc-dark/80 dark:text-lsc-cream/80 mb-6 max-w-2xl">
        {t(
          'aITools.wrongnessLead',
          'We publish what our AI got wrong, what is actually true, and what we changed in response. New entries appear here when we find them.',
        )}
      </p>

      {hasEntries ? (
        <ol className="space-y-4">
          {wrongnessLog.map(entry => (
            <li key={`${entry.date}-${entry.tool}-${entry.summary}`}>
              <article
                aria-labelledby={`wrongness-entry-${entry.date}-${entry.tool.replace(/\s+/g, '-')}`}
                className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5"
              >
                <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
                  <time
                    dateTime={entry.date}
                    className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    {formatEntryDate(entry.date)}
                  </time>
                  <h3
                    id={`wrongness-entry-${entry.date}-${entry.tool.replace(/\s+/g, '-')}`}
                    className="text-base font-serif font-bold text-lsc-dark dark:text-lsc-cream"
                  >
                    {entry.tool}
                  </h3>
                </header>
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="font-semibold text-lsc-dark dark:text-lsc-cream inline">
                      {t('aITools.wrongnessSummaryLabel', 'What it got wrong:')}
                    </dt>{' '}
                    <dd className="inline text-lsc-dark/80 dark:text-lsc-cream/80">
                      {entry.summary}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-lsc-dark dark:text-lsc-cream inline">
                      {t('aITools.wrongnessCorrectionLabel', 'What is true:')}
                    </dt>{' '}
                    <dd className="inline text-lsc-dark/80 dark:text-lsc-cream/80">
                      {entry.correction}
                    </dd>
                  </div>
                  {entry.response ? (
                    <div>
                      <dt className="font-semibold text-lsc-dark dark:text-lsc-cream inline">
                        {t('aITools.wrongnessResponseLabel', 'What we changed:')}
                      </dt>{' '}
                      <dd className="inline text-lsc-dark/80 dark:text-lsc-cream/80">
                        {entry.response}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              </article>
            </li>
          ))}
        </ol>
      ) : (
        <div
          role="status"
          className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-5 flex items-start gap-3"
        >
          <AlertCircle
            aria-hidden="true"
            className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-0.5"
          />
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            {t(
              'aITools.wrongnessEmpty',
              'No incidents to report yet. When we find a mistake worth correcting, we will list it here with the date, the tool, what was wrong, and what we changed.',
            )}
          </p>
        </div>
      )}

      <p className="mt-6 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        {t('aITools.wrongnessReviewedPrefix', 'Page reviewed:')}{' '}
        <time dateTime={wrongnessLogReviewedDate} className="font-mono">
          {formatEntryDate(wrongnessLogReviewedDate)}
        </time>
      </p>
    </section>
  )
}
