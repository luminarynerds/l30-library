/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Lightbulb, ChevronDown } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import { EASE_OUT_EXPO, MAGNETIC_HOVER } from '../motion'

interface FAQ {
  question: string
  answer: string
}

export default function FAQSection(): React.ReactElement {
  const { t } = useTranslation()

  const faqs: FAQ[] = [
    {
      question: t('aITools.faqPrivateQ', 'Is this really private?'),
      answer: t(
        'aITools.faqPrivateA',
        'Yes. The AI runs on a server in our building, not in "the cloud." Your questions and writing stay on our local server and never leave our network. We do not sell your data.',
      ),
    },
    {
      question: t('aITools.faqReplaceQ', 'Is this going to replace the librarians?'),
      answer: t(
        'aITools.faqReplaceA',
        'No. These tools handle simple questions at 2 AM so staff can focus on complex help during the day. Marlene has 30 years of experience. No AI can replace that. This just lets her expertise reach more people.',
      ),
    },
    {
      question: t('aITools.faqGoodQ', 'How good is it, really?'),
      answer: t(
        'aITools.faqGoodA',
        "Good enough to be useful, limited enough to know when to hand off to a human. The book recommender won't always nail it. Our tools admit when they don't know something. That's by design.",
      ),
    },
    {
      question: t('aITools.faqWhyNotChatGptQ', 'Why not just use ChatGPT?'),
      answer: t(
        'aITools.faqWhyNotChatGptA',
        "Privacy. ChatGPT sends your data to OpenAI's servers. Ours stays in the building. Also, ours knows our catalog, our community, and our local history. ChatGPT doesn't.",
      ),
    },
    {
      question: t('aITools.faqTrainedQ', 'Did you train this on library data?'),
      answer: t(
        'aITools.faqTrainedA',
        "The recommendation engine incorporates Marlene's knowledge and local reading patterns. But we don't train on individual patron data. Your checkout history is your business.",
      ),
    },
    {
      question: t('aITools.faqFromHomeQ', 'Can I use this from home?'),
      answer: t(
        'aITools.faqFromHomeA',
        'Some tools (like What Should I Read Next?) work from anywhere with your library card. The Writing Assistant is in-library only — we need the processing power of our server.',
      ),
    },
    {
      question: t('aITools.faqMistakesQ', 'Can AI make mistakes?'),
      answer: t(
        'aITools.faqMistakesA',
        'Yes — AI can "hallucinate" (make things up confidently). Always double-check facts, dates, and names before using AI-generated content. Every tool on this page has passed our eight-criteria evaluation rubric, but no AI is infallible.',
      ),
    },
  ]

  return (
    <section id="faq" className="scroll-mt-24">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('aITools.faqHeading', 'Questions People Actually Ask')}
        </h2>
      </div>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t('aITools.faqLead', 'And honest answers')}
      </p>
      <div className="space-y-4">
        {faqs.map(faq => (
          <details
            key={faq.question}
            className={clsx(
              'group bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700',
              MAGNETIC_HOVER,
            )}
          >
            <summary className="flex items-center justify-between gap-4 cursor-pointer list-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded-lg">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {faq.question}
              </h3>
              <ChevronDown
                aria-hidden="true"
                className={clsx(
                  'w-5 h-5 flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70 motion-safe:transition-transform motion-safe:duration-300 group-open:rotate-180',
                  EASE_OUT_EXPO,
                )}
              />
            </summary>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">{faq.answer}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
