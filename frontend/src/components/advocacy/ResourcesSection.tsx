/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, ExternalLink } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { getResources } from './helpers'

export default function ResourcesSection(): React.ReactElement {
  const { t } = useTranslation()
  const resources = getResources(t)

  return (
    <section aria-labelledby="resources-heading">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h2 id="resources-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          Advocacy Resources
        </h2>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {resources.map((resource) => (
          <a
            key={resource.name}
            href={resource.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 hover:shadow-md hover:border-lsc-rose/50 dark:hover:border-lsc-rose/50 transition-all flex flex-col gap-2"
          >
            <div className="flex items-start justify-between gap-2">
              <ExternalLink
                className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5"
                aria-hidden="true"
              />
              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors ml-auto">
                Visit →
              </span>
            </div>
            <h3 className="font-bold text-lsc-dark dark:text-lsc-cream text-sm leading-snug">
              {resource.name}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{resource.description}</p>
          </a>
        ))}
      </div>
    </section>
  )
}
