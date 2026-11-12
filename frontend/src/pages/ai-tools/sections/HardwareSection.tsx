/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

interface HardwareRow {
  label: string
  value: string
}

export default function HardwareSection(): React.ReactElement {
  const { t } = useTranslation()
  const rows: HardwareRow[] = [
    {
      label: t('aITools.hardwareServer', 'Server'),
      value: t(
        'aITools.refurbishedDellPoweredgeRDonated',
        'Refurbished Dell PowerEdge R720 (donated by the county IT department when they upgraded)',
      ),
    },
    {
      label: t('aITools.hardwareModel', 'Model'),
      value: t(
        'aITools.llamaViaOllamaOpenaiWhisper',
        'Llama 3.2 via Ollama. Open-weights, runs locally on the R720. No cloud API calls for any tool on this page.',
      ),
    },
    {
      label: t('aITools.hardwareCost', 'Cost'),
      value: t(
        'aITools.hardwareCostValue',
        "~$200/year in electricity. The server was free. Stevie's time was... extensive.",
      ),
    },
    {
      label: t('aITools.hardwareMaintenance', 'Maintenance'),
      value: t(
        'aITools.stevieChecksItMondaysBob',
        'Stevie checks it Mondays. Bob (from the garage) helped with cooling.',
      ),
    },
    {
      label: t('aITools.hardwareGuardrails', 'Guardrails'),
      value: t(
        'aITools.everyModelIsFineTuned',
        "Every model is fine-tuned with custom system prompts, content filters, and hard limits. No medical, legal, or financial advice. Family-friendly. Admits when it doesn't know.",
      ),
    },
    {
      label: t('aITools.hardwareKillSwitch', 'Kill switch'),
      value: t(
        'aITools.thereSAPlugIf',
        "There's a plug. If anything goes sideways, we unplug it. Every tool can be turned off independently without breaking anything else. Reversibility is one of our eight criteria.",
      ),
    },
  ]

  return (
    <section
      id="hardware"
      className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 scroll-mt-24"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.hardwareHeading', 'The Actual Hardware')}
        </h2>
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('aITools.hardwareLastUpdated', 'Last updated: May 2026')}
        </span>
      </div>
      <dl className="space-y-4 max-w-2xl">
        {rows.map((row, i) => (
          <div
            key={row.label}
            className={i < rows.length - 1 ? 'border-b border-lsc-border dark:border-earth-700 pb-4' : 'pb-4'}
          >
            <dt className="inline font-semibold text-lsc-dark dark:text-lsc-cream">{row.label}:</dt>{' '}
            <dd className="inline font-normal text-lsc-dark/70 dark:text-lsc-cream/70">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
