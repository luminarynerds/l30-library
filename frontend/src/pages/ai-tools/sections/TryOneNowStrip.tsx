/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import { MAGNETIC_HOVER } from '../motion'

interface TryOneCard {
  to: string
  icon: React.ElementType
  iconClass: string
  title: string
  scenario: string
  cta: string
}

export default function TryOneNowStrip(): React.ReactElement {
  const { t } = useTranslation()

  const cards: TryOneCard[] = [
    {
      to: '/catalog',
      icon: BookOpen,
      iconClass: 'text-lsc-rose dark:text-lsc-rose-light',
      title: t('aITools.tryReadNextTitle', 'What Should I Read Next?'),
      scenario: t(
        'aITools.tryReadNextScenario',
        'Tell us what you liked. We will suggest something off our own shelves.',
      ),
      cta: t('aITools.tryReadNextCta', 'Find a book'),
    },
  ]

  return (
    <section
      aria-labelledby="ai-try-now-heading"
      className="mb-10"
    >
      <h2
        id="ai-try-now-heading"
        className="text-base font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3"
      >
        {t('aITools.tryOneNowHeading', 'Try one now')}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {cards.map(card => (
          <Link
            key={card.to}
            to={card.to}
            className={clsx(
              'group flex flex-col gap-3 p-5 rounded-xl bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
              MAGNETIC_HOVER,
            )}
          >
            <div className="flex items-center gap-3">
              <card.icon
                aria-hidden="true"
                className={`w-5 h-5 flex-shrink-0 ${card.iconClass}`}
              />
              <span className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {card.title}
              </span>
            </div>
            <p className="text-sm text-lsc-dark dark:text-lsc-cream/80">
              {card.scenario}
            </p>
            <span
              className="inline-flex items-center gap-1 text-sm font-semibold text-lsc-rose dark:text-lsc-rose-light group-hover:gap-2 transition-all"
            >
              {card.cta}
              <ArrowRight aria-hidden="true" className="w-4 h-4" />
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}
