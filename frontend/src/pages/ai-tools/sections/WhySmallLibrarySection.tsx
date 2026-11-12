/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

export default function WhySmallLibrarySection(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <section
      id="why"
      className="scroll-mt-24 bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6"
    >
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        {t('aITools.whyHeading', 'Why a Small Library Does AI')}
      </h2>
      <div className="space-y-6 text-lsc-dark/70 dark:text-lsc-cream/70">
        <p>
          {t(
            'aITools.whyPara1',
            'Last year, Stevie came to a board meeting with a proposal. "Everyone\'s talking about AI," she said. "Most of it is hype. But some of it could actually help people. We should figure out which is which." She wasn\'t wrong.',
          )}
        </p>
        <p>
          {t(
            'aITools.whyPara2',
            'Harold (board member, retired accountant, skeptical of everything) asked the obvious question: "How much does it cost?" Stevie had an answer: we could run open-source models on a refurbished server for less than what we spend on printer toner.',
          )}
        </p>
        <p>
          {t(
            'aITools.whyPara3',
            'Marlene (30 years at the reference desk, seen every trend come and go) asked the better question: "What problem does it solve?" The answer: patrons need help with writing, research, and recommendations at 2 AM when we\'re closed. They need answers without judgment. They need tools that don\'t spy on them.',
          )}
        </p>
        <p>
          {t(
            'aITools.whyPara4',
            'The board approved the pilot. Within months, we had a writing assistant running on a computer in our server room. Then we expanded. Now we have a whole suite of tools, and the results speak for themselves. Nothing leaves the building. Nothing gets sold. Nothing gets used to train corporate models.',
          )}
        </p>
        <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
          {t(
            'aITools.whyPara5',
            "We're not trying to replace librarians. We're trying to extend their reach. Marlene's 30 years of reader's advisory expertise now helps people at 2 AM. And Stevie gets to stop answering the wifi password question.",
          )}
        </p>
        <p className="italic">
          {t(
            'aITools.whyPara6',
            "Big tech wants AI to extract value from communities. We want AI to give value back. That's the difference.",
          )}
        </p>
      </div>
    </section>
  )
}
