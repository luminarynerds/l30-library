/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  BookX,
  Cpu,
  Eye,
  FileSearch,
  NotebookText,
  Receipt,
  type LucideIcon,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import type { OrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

interface HubItem {
  icon: LucideIcon
  title: string
  blurb: string
  href: string
  flag?: keyof OrganizationFeatures
}

export default function TransparencyPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()

  const items: HubItem[] = [
    {
      icon: Receipt,
      title: t('transparency.materialCosts.title', 'Material costs'),
      blurb: t(
        'transparency.materialCosts.blurb',
        'What we paid for the books, databases, and equipment on the shelves -- compared to what you would pay retail.',
      ),
      href: '/transparency/material-costs',
    },
    {
      icon: FileSearch,
      title: t('transparency.publicRecords.title', 'Public records requests'),
      blurb: t(
        'transparency.publicRecords.blurb',
        'Submit a request and read the public disclosure log.',
      ),
      href: '/transparency/records-requests',
    },
    {
      icon: NotebookText,
      title: t('transparency.board.title', 'Board meetings'),
      blurb: t(
        'transparency.board.blurb',
        'Agendas, minutes, recordings, motions, and the public-comment record.',
      ),
      href: '/board/meetings',
      flag: 'board_features_enabled',
    },
    {
      icon: BookX,
      title: t('transparency.banTracker.title', 'Book challenges'),
      blurb: t(
        'transparency.banTracker.blurb',
        'A public log of every challenged item and how we responded.',
      ),
      href: '/ban-tracker',
    },
    {
      icon: Cpu,
      title: t('transparency.ai.title', 'AI at the library'),
      blurb: t(
        'transparency.ai.blurb',
        'How we use AI, the rubric we use to evaluate it, and the things we have gotten wrong.',
      ),
      href: '/ai/how-it-works',
      flag: 'ai_tools_enabled',
    },
    {
      icon: BarChart3,
      title: t('transparency.stats.title', 'By the numbers'),
      blurb: t(
        'transparency.stats.blurb',
        'Circulation, holdings, and other patron-facing statistics.',
      ),
      href: '/about?tab=stats',
    },
  ]

  const visibleItems = items.filter((item) => !item.flag || isFeatureEnabled(item.flag))

  return (
    <StandardPageLayout
      title={t('transparency.title', 'Transparency')}
      subtitle={t(
        'transparency.subtitle',
        'Where the money goes, what gets challenged, what our board decides, and how to ask for more.',
      )}
      icon={Eye}
    >
      <ul
        role="list"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        aria-label={t('transparency.listLabel', 'Transparency resources')}
      >
        {visibleItems.map(({ icon: Icon, title, blurb, href }) => (
          <li key={href}>
            <Link
              to={href}
              className="group flex h-full flex-col gap-3 rounded-xl border border-lsc-border bg-lsc-white p-5 transition-colors hover:border-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:border-earth-700 dark:bg-earth-800 dark:hover:border-lsc-rose-light"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose-light/10 dark:text-lsc-rose-light"
                >
                  <Icon className="h-5 w-5" />
                </span>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {title}
                </h2>
              </div>
              <p className="flex-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{blurb}</p>
              <span className="mt-1 inline-flex items-center gap-1 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light">
                {t('transparency.openLink', 'Open')}
                <ArrowRight
                  aria-hidden="true"
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                />
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </StandardPageLayout>
  )
}
