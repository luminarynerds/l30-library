/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

interface Criterion {
  name: string
  question: string
}

export default function RubricSection(): React.ReactElement {
  const { t } = useTranslation()
  const criteria: Criterion[] = [
    {
      name: t('aITools.rubricPrivacy', 'Privacy'),
      question: t('aITools.isTheSessionWipedWhen', 'Is the session wiped when you close the tab?'),
    },
    {
      name: t('aITools.rubricTransparency', 'Transparency'),
      question: t('aITools.canWeExplainHowThis', 'Can we explain how this works to a curious 10-year-old?'),
    },
    {
      name: t('aITools.rubricLocalControl', 'Local Control'),
      question: t('aITools.doesYourDataStayOn', 'Does your data stay on the library network?'),
    },
    {
      name: t('aITools.rubricEquity', 'Equity'),
      question: t('aITools.doesThisWorkInSensory', 'Does this work in Sensory Quiet Mode? All abilities and bandwidths?'),
    },
    {
      name: t('aITools.rubricBias', 'Bias Audit'),
      question: t('aITools.haveWeTestedForBias', 'Have we tested for bias? Do results reflect our whole community?'),
    },
    {
      name: t('aITools.rubricStaffImpact', 'Staff Impact'),
      question: t('aITools.doesThisHelpOurTeam', 'Does this help our team do better work (not replace them)?'),
    },
    {
      name: t('aITools.rubricPatronBenefit', 'Patron Benefit'),
      question: t('aITools.isThisActuallyForPatrons', 'Is this actually for patrons (not just our convenience)?'),
    },
    {
      name: t('aITools.rubricReversibility', 'Reversibility'),
      question: t('aITools.canWeTurnThisOff', 'Can we turn this off without breaking everything?'),
    },
  ]

  return (
    <section
      id="rubric"
      className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-8 mb-8 scroll-mt-24"
    >
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
        {t('aITools.rubricHeading', 'How We Evaluate Every AI Feature')}
      </h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
        {t(
          'aITools.rubricLead',
          'Before anything goes live, it must pass all eight criteria. No exceptions. No "well, maybe just this once."',
        )}
      </p>
      <div className="grid md:grid-cols-2 gap-6">
        {criteria.map(c => (
          <div key={c.name} className="border-l-4 border-lsc-rose pl-4">
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{c.name}</h4>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">{c.question}</p>
            <p className="text-xs font-bold text-lsc-rose">
              {t('aITools.rubricMustBeYes', 'Must be YES')}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
