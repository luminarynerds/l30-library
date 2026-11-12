/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

interface KnowledgeBlock {
  title: string
  body: string
  note: string
}

export default function LocalKnowledgeSection(): React.ReactElement {
  const { t } = useTranslation()
  const blocks: KnowledgeBlock[] = [
    {
      title: t('aITools.knowledgeReadAlikeTitle', "Marlene's Read-Alike Database"),
      body: t(
        'aITools.knowledgeReadAlikeBody',
        '30 years of "if you liked X, try Y" recommendations, manually documented over 6 months',
      ),
      note: t('aITools.knowledgeReadAlikeNote', '2,847 book connections'),
    },
    {
      title: t('aITools.knowledgeCommunityTitle', 'Community Context'),
      body: t(
        'aITools.localEventsSchoolSchedulesReading',
        "Local events, school schedules, reading group themes, what's popular at the farmers market",
      ),
      note: t('aITools.knowledgeCommunityNote', 'Updated monthly'),
    },
    {
      title: t('aITools.masterGardenerWisdomZone', 'Master Gardener Wisdom Zone'),
      body: t(
        'aITools.knowledgeGardenerBody',
        '5b planting guides, frost dates, local soil tips, pest identification',
      ),
      note: t('aITools.fromElmdaleSGardeningClub', "From Elmdale's gardening club"),
    },
    {
      title: t('aITools.knowledgeFaqTitle', 'FAQ History'),
      body: t(
        'aITools.knowledgeFaqBody',
        '5 years of reference desk questions, anonymized and categorized by Thel',
      ),
      note: t('aITools.knowledgeFaqNote', '12,000+ Q&A pairs'),
    },
  ]

  return (
    <section className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
      <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        {t('aITools.localKnowledgeHeading', 'Local Knowledge • What makes it ours')}
      </h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t(
          'aITools.localKnowledgeLead',
          "The AI knows about our community because we taught it. Here's what we fed in:",
        )}
      </p>
      <div className="space-y-4">
        {blocks.map(block => (
          <div key={block.title} className="border-l-4 border-lsc-rose pl-4">
            <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{block.title}</h4>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{block.body}</p>
            <p className="text-xs text-lsc-rose font-medium mt-1">{block.note}</p>
          </div>
        ))}
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-6 italic">
        {t(
          'aITools.localKnowledgeOutro',
          'Marlene was skeptical about "training the AI" until she saw it recommend "Anxious People" to someone who liked "A Man Called Ove." "That\'s exactly what I would have suggested," she said. That\'s when we knew it was working.',
        )}
      </p>
    </section>
  )
}
