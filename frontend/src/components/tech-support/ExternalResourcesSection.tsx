/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ExternalLink, Wifi, Laptop, BookOpen, Printer } from 'lucide-react'
import type { QuickAccessSection } from '@/api/tech-support-api'
import { useTranslation } from '@/i18n'

interface ExternalResourcesSectionProps {
  sections: QuickAccessSection[]
}

// Icon glyphs keyed by the stable lucide-react icon name carried on
// QuickAccessSection.icon. Small on purpose — extend only when a new
// section icon is actually used.
// Stored kebab-case in tech_quick_links.section_icon (lucide-icon-name convention).
const ICON_BY_NAME: Record<string, React.ReactNode> = {
  'wifi': <Wifi aria-hidden="true" className="w-4 h-4 text-lsc-rose/80 dark:text-lsc-rose-light/80" />,
  'laptop': <Laptop aria-hidden="true" className="w-4 h-4 text-lsc-rose/80 dark:text-lsc-rose-light/80" />,
  'book-open': <BookOpen aria-hidden="true" className="w-4 h-4 text-lsc-rose/80 dark:text-lsc-rose-light/80" />,
  'printer': <Printer aria-hidden="true" className="w-4 h-4 text-lsc-rose/80 dark:text-lsc-rose-light/80" />,
}

const DEFAULT_SECTION_ICON = (
  <ExternalLink
    aria-hidden="true"
    className="w-4 h-4 text-lsc-rose/80 dark:text-lsc-rose-light/80"
  />
)

function pickSectionIcon(section: QuickAccessSection): React.ReactNode {
  if (section.icon && section.icon in ICON_BY_NAME) {
    return ICON_BY_NAME[section.icon]
  }
  return DEFAULT_SECTION_ICON
}

export default function ExternalResourcesSection({
  sections,
}: ExternalResourcesSectionProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (!sections || sections.length === 0) {
    return null
  }

  return (
    <section
      aria-labelledby="tech-external-resources-heading"
      className="mb-10"
    >
      <div className="flex items-center gap-2 mb-3">
        <ExternalLink
          aria-hidden="true"
          className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60"
        />
        <h2
          id="tech-external-resources-heading"
          className="font-serif text-base font-semibold text-lsc-dark/80 dark:text-lsc-cream/80"
        >
          {t('techSupport.outsideResourcesHeading', 'Outside resources')}
        </h2>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {sections.map((section) => (
          <div
            key={section.title}
            className="bg-lsc-white/60 dark:bg-earth-800/60 rounded-lg p-3 border border-lsc-border/60 dark:border-earth-700/60"
          >
            <div className="flex items-center gap-1.5 mb-2">
              {pickSectionIcon(section)}
              <h3 className="text-sm font-medium text-lsc-dark/80 dark:text-earth-50/80">
                {section.title}
              </h3>
            </div>
            <ul className="space-y-1">
              {(section.links || []).map((link) => (
                <li key={link.name}>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t('techSupport.opensInNewTabAriaLabel', '{{name}} (opens in a new tab)').replace('{{name}}', link.name)}
                    className="text-xs text-earth-700 dark:text-lsc-cream/80 underline hover:text-earth-900 dark:hover:text-white inline-flex items-center gap-1"
                  >
                    {link.name}
                    <ExternalLink aria-hidden="true" className="w-3 h-3" />
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  )
}
