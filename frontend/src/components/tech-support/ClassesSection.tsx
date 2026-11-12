/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Users, Calendar, Clock, MapPin, ArrowRight } from 'lucide-react'
import type { TechClass } from '@/api/tech-support-api'
import { useTranslation } from '@/i18n'

interface ClassesSectionProps {
  classes: TechClass[]
}

const TEASER_COUNT = 2

export default function ClassesSection({ classes }: ClassesSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const teaser = classes.slice(0, TEASER_COUNT)

  return (
    <section aria-labelledby="tech-classes-heading" className="mb-10">
      <div className="flex items-center gap-2 mb-3">
        <Users aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2
          id="tech-classes-heading"
          className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50"
        >
          {t('techSupport.classesHeading', 'Tech Classes & Workshops')}
        </h2>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-5">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('techSupport.classesIntro', 'Free classes for beginners and beyond. Drop-ins welcome if space allows.')}
        </p>
        {teaser.length > 0 && (
          <ul className="space-y-3 mb-4">
            {teaser.map((cls) => (
              <li
                key={cls.title}
                className="border-l-2 border-lsc-rose/40 pl-3"
              >
                <div className="font-medium text-sm text-lsc-dark dark:text-earth-50">
                  {cls.title}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  <span className="inline-flex items-center gap-1">
                    <Calendar aria-hidden="true" className="w-3 h-3" />
                    {cls.date}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Clock aria-hidden="true" className="w-3 h-3" />
                    {cls.time}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MapPin aria-hidden="true" className="w-3 h-3" />
                    {cls.location}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
        <Link
          to="/events"
          data-testid="tech-classes-see-all"
          className="inline-flex items-center gap-1 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          {t('techSupport.seeAllClasses', 'See all classes')}
          <ArrowRight aria-hidden="true" className="w-4 h-4" />
        </Link>
      </div>
    </section>
  )
}
