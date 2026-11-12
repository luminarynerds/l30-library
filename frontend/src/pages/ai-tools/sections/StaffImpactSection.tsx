/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

interface TimeBreakdown {
  label: string
  routinePct: number
  meaningfulPct: number
  detail: string
}

function TimeBar({ breakdown }: { breakdown: TimeBreakdown }): React.ReactElement {
  const routineDominant = breakdown.routinePct >= breakdown.meaningfulPct
  return (
    <div>
      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">{breakdown.label}</p>
      <div className="flex gap-4 items-center">
        <div className="flex-1 flex gap-2 h-12">
          <div
            style={{ flex: breakdown.routinePct }}
            className={`${routineDominant ? 'bg-lsc-rose' : 'bg-lsc-rose/30'} rounded-l-lg flex items-center justify-center`}
          >
            <span className={`text-xs font-semibold ${routineDominant ? 'text-white' : 'text-lsc-dark dark:text-lsc-cream'}`}>
              {breakdown.routinePct}% routine
            </span>
          </div>
          <div
            style={{ flex: breakdown.meaningfulPct }}
            className={`${!routineDominant ? 'bg-lsc-rose' : 'bg-lsc-rose/30'} rounded-r-lg flex items-center justify-center`}
          >
            <span className={`text-xs font-semibold ${!routineDominant ? 'text-white' : 'text-lsc-dark dark:text-lsc-cream'}`}>
              {breakdown.meaningfulPct}% meaningful
            </span>
          </div>
        </div>
      </div>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{breakdown.detail}</p>
    </div>
  )
}

export default function StaffImpactSection(): React.ReactElement {
  const { t } = useTranslation()
  const breakdowns: TimeBreakdown[] = [
    {
      label: t('aITools.beforeAi', 'Before AI'),
      routinePct: 60,
      meaningfulPct: 40,
      detail: t(
        'aITools.beforeAiDetail',
        '60% routine queries (passwords, printing, "where is...") • 40% meaningful work',
      ),
    },
    {
      label: t('aITools.afterAi', 'After AI'),
      routinePct: 25,
      meaningfulPct: 75,
      detail: t('aITools.afterAiDetail', '25% routine queries • 75% meaningful work'),
    },
  ]

  const wins = [
    {
      title: t('aITools.winProgramsTitle', '40 new programs'),
      body: t('aITools.winProgramsBody', '— Coding club, "tech help, no judgment" sessions'),
    },
    {
      title: t('aITools.winOutreachTitle', 'Community outreach'),
      body: t('aITools.winOutreachBody', '— Regular visits to the senior center, food bank, and high school'),
    },
    {
      title: t('aITools.winReferenceTitle', 'Deep reference work'),
      body: t('aITools.winReferenceBody', '— Genealogy, local history with Moira, business research—the work librarians trained for'),
    },
    {
      title: t('aITools.winCollectionTitle', 'Better collection development'),
      body: t('aITools.winCollectionBody', '— More time to talk to patrons and build a collection that reflects our community'),
    },
  ]

  return (
    <section className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-8">
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t(
          'aITools.staffImpactHeading',
          "AI Didn't Replace Our Staff. It Let Them Be Librarians Again.",
        )}
      </h2>
      <div className="space-y-8">
        <div className="bg-lsc-cream dark:bg-lsc-dark/20 rounded-xl p-6">
          <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-6">
            {t('aITools.timeSpentOnDifferentWork', 'Time Spent on Different Work')}
          </p>
          <div className="space-y-6">
            {breakdowns.map(b => (
              <TimeBar key={b.label} breakdown={b} />
            ))}
          </div>
        </div>
        <div>
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('aITools.whereTheTimeWent', 'Where the Time Went')}
          </h4>
          <ul className="space-y-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {wins.map(win => (
              <li key={win.title} className="flex gap-3">
                <span className="text-lsc-rose font-bold mt-0.5">+</span>
                <span>
                  <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{win.title}</span>{' '}
                  {win.body}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
