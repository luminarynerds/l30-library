/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Monitor, Wrench, BookOpen, Users, Scale, Package } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'

interface ActionItem {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  icon: React.ComponentType<any>
  titleKey: string
  link: string
  featureFlag?: string
}

const ActionGrid: React.FC = () => {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()

  const actions = useMemo(() => {
    const all: ActionItem[] = [
      { icon: Wrench, titleKey: 'home.actionGrid.makerspace', link: '/makerspace', featureFlag: 'makerspace_enabled' },
      { icon: BookOpen, titleKey: 'home.actionGrid.kidsTeens', link: '/youth', featureFlag: 'community_features_enabled' },
      { icon: Users, titleKey: 'home.actionGrid.bookClubs', link: '/book-clubs', featureFlag: 'book_clubs_enabled' },
      { icon: Scale, titleKey: 'home.actionGrid.legalAid', link: '/legal', featureFlag: 'legal_services_enabled' },
      { icon: Monitor, titleKey: 'home.actionGrid.digitalResources', link: '/digital', featureFlag: 'collection_management_enabled' },
      { icon: Package, titleKey: 'home.actionGrid.libraryOfThings', link: '/catalog?format=equipment', featureFlag: 'collection_management_enabled' },
    ]
    return all.filter(a => !a.featureFlag || isFeatureEnabled(a.featureFlag as any))
  }, [isFeatureEnabled])

  if (actions.length === 0) return null

  return (
    <section>
      <div className="mb-6 md:mb-10">
        <h2 id="at-library-heading" className="font-serif text-2xl md:text-3xl text-lsc-dark dark:text-lsc-cream">
          {t('home.actionGrid.title')}
        </h2>
        <p className="text-sm md:text-base text-earth-600 dark:text-earth-400 mt-2">
          {t('home.actionGrid.subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <Link
              key={action.titleKey}
              to={action.link}
              className="flex min-h-[56px] min-w-0 items-center gap-3 py-3 border-b border-lsc-border dark:border-earth-700/30 text-lsc-dark dark:text-lsc-cream hover:text-sage-700 dark:hover:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 rounded-sm group"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center">
                <Icon className="w-5 h-5 text-sage-700 dark:text-lsc-rose" aria-hidden={true} />
              </div>
              <span className="text-sm md:text-base font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-sage-600 dark:group-hover:text-lsc-rose transition-colors duration-500">
                {t(action.titleKey)}
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

export default ActionGrid
