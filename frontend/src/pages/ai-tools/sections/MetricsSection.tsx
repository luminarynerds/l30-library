/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Info } from 'lucide-react'
import { useTranslation } from '@/i18n'
import MetricCard from '../components/MetricCard'

export default function MetricsSection(): React.ReactElement {
  const { t } = useTranslation()
  const headlineMetrics = [
    {
      value: '+34%',
      label: t('aITools.metricCirculation', 'Circulation increase'),
      detail: t('aITools.metricCirculationDetail', 'Year over year, across all formats'),
    },
    {
      value: '+89%',
      label: t('aITools.metricDigital', 'Digital resource usage'),
      detail: t('aITools.metricDigitalDetail', 'Patrons actually finding what we pay for'),
    },
    {
      value: '3 min',
      label: t('aITools.metricResolution', 'Avg. question resolution'),
      detail: t('aITools.metricResolutionDetail', 'Down from 12. Staff can breathe again.'),
    },
  ]
  const secondaryMetrics = [
    {
      value: '40+',
      label: t('aITools.metricPrograms', 'New programs added'),
      detail: t('aITools.metricProgramsDetail', 'Staff time freed up for community work'),
    },
    {
      value: '0',
      label: t('aITools.metricCuts', 'Staff positions cut'),
      detail: t('aITools.metricCutsDetail', 'Augmentation, not replacement. Always.'),
    },
    {
      value: '0',
      label: t('aITools.metricLogged', 'Patron queries logged'),
      detail: t('aITools.metricLoggedDetail', 'Your session is wiped when you close the tab'),
    },
  ]

  return (
    <section id="metrics" className="scroll-mt-24">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
        {t('aITools.metricsHeading', "What's Changed Since We Launched")}
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t(
          'aITools.metricsRange',
          'Measured November 2025 – April 2026, compared to the same period one year prior.',
        )}
      </p>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        {t(
          'aITools.metricsLead',
          'Real numbers from a real library. No cherry-picking, no spin—just what actually happened.',
        )}
      </p>

      <div className="mb-8 flex items-start gap-3 p-4 rounded-xl bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700">
        <Info aria-hidden="true" className="w-5 h-5 flex-shrink-0 mt-0.5 text-lsc-rose dark:text-lsc-rose-light" />
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('aITools.methodologyLabel', 'How we measure this without tracking patrons:')}
          </span>{' '}
          {t(
            'aITools.methodologyBody',
            'Circulation and digital usage come from the ILS aggregate counters (checkouts per day, no patron identifiers). Resolution times are sampled from staff timesheets, not individual queries. AI tool sessions are ephemeral—we count only that a session opened, never what was asked.',
          )}
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {headlineMetrics.map(m => (
          <MetricCard key={m.label} value={m.value} label={m.label} detail={m.detail} />
        ))}
      </div>

      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {secondaryMetrics.map(m => (
          <MetricCard key={m.label} value={m.value} label={m.label} detail={m.detail} />
        ))}
      </div>
    </section>
  )
}
