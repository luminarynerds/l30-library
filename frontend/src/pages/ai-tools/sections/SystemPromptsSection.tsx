/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Lightbulb } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface PromptGroup {
  label: string
  items: string[]
}

export default function SystemPromptsSection(): React.ReactElement {
  const { t } = useTranslation()
  const groups: PromptGroup[] = [
    {
      label: 'ROLE',
      items: [
        t('aITools.suggestBooksBasedOnWhat', 'Suggest books based on what patrons have enjoyed before'),
        t('aITools.considerMoodReadingLevelAnd', 'Consider mood, reading level, and format preferences'),
        t('aITools.drawFromPattySYears', "Draw from Marlene's 30 years of read-alike recommendations"),
        t('aITools.prioritizeTitlesAvailableInOur', 'Prioritize titles available in our catalog'),
      ],
    },
    {
      label: 'LOCAL CONTEXT',
      items: [
        t('aITools.ourCatalogIncludesTitlesAcross', 'Our catalog includes 47,000+ titles across all formats'),
        t('aITools.readingGroupsMeetMonthlySuggest', 'Reading groups meet monthly; suggest titles that spark discussion'),
        t('aITools.weCarryLocalAuthorsAnd', 'We carry local authors and small press titles from the region'),
        t('aITools.largePrintAndAudiobookAlternatives', 'Large print and audiobook alternatives are always worth mentioning'),
      ],
    },
    {
      label: 'GUARDRAILS',
      items: [
        t('aITools.neverGiveMedicalLegalOr', 'Never give medical, legal, or financial advice'),
        t('aITools.ifUnsureAboutARecommendation', 'If unsure about a recommendation, say so and suggest asking staff'),
        t('aITools.stayFamilyFriendlyUnlessThe', 'Stay family-friendly unless the patron specifies otherwise'),
        t('aITools.donTRecommendBooksWe', "Don't recommend books we don't carry without noting it"),
      ],
    },
  ]

  return (
    <section id="system-prompts" className="scroll-mt-24">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.howWeSteerIt', 'How We Steer It')}
        </h2>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
        {t(
          'aITools.howWeSteerItLead',
          "The AI doesn't just work out of the box. Stevie spent months configuring it to be useful, safe, and true to our values. Here's what that actually looks like.",
        )}
      </p>
      <div className="mb-6 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
        <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('aITools.systemPromptsHeading', 'System Prompts • The personality layer')}
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {t(
            'aITools.systemPromptsLead',
            'Every AI tool starts with a "system prompt" - instructions that shape how it behaves. Here\'s an example of how we configure our tools:',
          )}
        </p>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-6 font-mono text-sm text-lsc-dark dark:text-lsc-cream space-y-3 mb-6 overflow-x-auto">
          <p className="font-semibold">
            {t(
              'aITools.youAreAReaderS',
              "You are a reader's advisory assistant for {{libraryShortName}}. You help patrons discover their next great read.",
            )}
          </p>
          {groups.map(group => (
            <div key={group.label}>
              <p className="font-semibold text-lsc-rose">{group.label}:</p>
              <ul className="list-disc list-inside text-xs space-y-1 mt-1">
                {group.items.map(item => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
          <span className="font-semibold">{t('aITools.funFactLabel', 'Fun fact:')}</span>{' '}
          {t(
            'aITools.systemPromptsFunFact',
            "Every system prompt goes through multiple drafts. This one started with Marlene's handwritten notes from 30 years of reader's advisory.",
          )}
        </p>
      </div>
    </section>
  )
}
