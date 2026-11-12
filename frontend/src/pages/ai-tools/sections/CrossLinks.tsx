/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, ShieldCheck } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import { MAGNETIC_HOVER } from '../motion'

interface CrossLink {
  to: string
  icon: React.ElementType
  title: string
  subtitle: string
}

export default function CrossLinks(): React.ReactElement {
  const { t } = useTranslation()
  const links: CrossLink[] = [
    {
      to: '/digital',
      icon: BookOpen,
      title: t('aITools.crossLinkDigitalTitle', 'Looking for eBooks, movies, or music?'),
      subtitle: t('aITools.crossLinkDigitalSubtitle', 'See all digital resources'),
    },
    {
      to: '/about/ai-policy',
      icon: ShieldCheck,
      title: t('aITools.crossLinkPolicyTitle', 'Our position on AI in collections'),
      subtitle: t('aITools.crossLinkPolicySubtitle', 'Read the full AI policy'),
    },
  ]
  return (
    <div className="flex flex-col sm:flex-row gap-4">
      {links.map(link => (
        <Link
          key={link.to}
          to={link.to}
          className={clsx(
            'flex-1 flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
            MAGNETIC_HOVER,
          )}
        >
          <link.icon aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">
              {link.title}
            </span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{link.subtitle}</p>
          </div>
          <ArrowRight aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0" />
        </Link>
      ))}
    </div>
  )
}
