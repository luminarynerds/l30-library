/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Monitor, Printer, Wifi, MapPin } from 'lucide-react'
import type { TechFacilitySection } from '@/api/tech-support-api'
import { useTranslation } from '@/i18n'

interface FacilitiesSectionProps {
  sections: TechFacilitySection[]
}

// Stable kind+label icon map. Falls back to `kindFallbackIcon` below
// when a label is unrecognized. Keys are lowercase normalized labels.
const KIND_LABEL_ICON: Record<string, Record<string, React.ReactNode>> = {
  computer_lab: {
    computers: <Monitor aria-hidden="true" className="w-4 h-4" />,
    wifi: <Wifi aria-hidden="true" className="w-4 h-4" />,
    'b&w printing': <Printer aria-hidden="true" className="w-4 h-4" />,
    'color printing': <Printer aria-hidden="true" className="w-4 h-4" />,
  },
}

const kindFallbackIcon: Record<string, React.ReactNode> = {
  computer_lab: <Monitor aria-hidden="true" className="w-4 h-4" />,
  printer: <MapPin aria-hidden="true" className="w-4 h-4" />,
}

const kindHeading: Record<string, string> = {
  computer_lab: 'Public Computer Lab',
  printer: 'Printer Locations',
}

const kindHeadingKey: Record<string, string> = {
  computer_lab: 'techSupport.facilityKind.computerLab',
  printer: 'techSupport.facilityKind.printerLocations',
}

const kindHeadingIcon: Record<string, React.ReactNode> = {
  computer_lab: <Monitor aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />,
  printer: <Printer aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />,
}

function pickIcon(kind: string, label: string): React.ReactNode {
  const normalized = label.toLowerCase().trim()
  const kindMap = KIND_LABEL_ICON[kind]
  if (kindMap) {
    for (const key of Object.keys(kindMap)) {
      if (normalized.includes(key)) {
        return kindMap[key]
      }
    }
  }
  return kindFallbackIcon[kind] ?? <MapPin aria-hidden="true" className="w-4 h-4" />
}

export default function FacilitiesSection({ sections }: FacilitiesSectionProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (!sections || sections.length === 0) {
    return null
  }

  return (
    <section
      aria-labelledby="tech-facilities-heading"
      className="mb-10"
      data-testid="tech-facilities"
    >
      <h2
        id="tech-facilities-heading"
        className="font-serif text-xl font-semibold text-lsc-dark dark:text-earth-50 mb-4"
      >
        {t('techSupport.facilitiesHeading', 'Facilities')}
      </h2>
      <div className="space-y-6">
        {sections.map((section) => {
          const headingKey = kindHeadingKey[section.kind]
          const headingFallback = kindHeading[section.kind] ?? section.kind
          const heading = headingKey ? t(headingKey, headingFallback) : headingFallback
          const isComputerLab = section.kind === 'computer_lab'

          return (
            <div
              key={section.kind}
              data-facility-kind={section.kind}
              className="bg-lsc-cream dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-5 sm:p-6"
            >
              <div className="flex items-center gap-2 mb-3">
                {kindHeadingIcon[section.kind]}
                <h3 className="font-serif font-semibold text-base text-lsc-dark dark:text-earth-50">
                  {heading}
                </h3>
              </div>
              {isComputerLab ? (
                <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {section.facilities.map((facility) => (
                    <span
                      key={facility.id}
                      className="inline-flex items-center gap-1"
                      data-facility-label={facility.label}
                    >
                      {pickIcon(section.kind, facility.label)}
                      <span>
                        <strong className="font-medium text-lsc-dark dark:text-earth-50">
                          {facility.label}:
                        </strong>{' '}
                        {facility.value}
                      </span>
                    </span>
                  ))}
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 gap-3">
                  {section.facilities.map((facility) => (
                    <div
                      key={facility.id}
                      data-facility-label={facility.label}
                      className="bg-lsc-white dark:bg-earth-800/40 rounded-lg p-4"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {pickIcon(section.kind, facility.label)}
                        <h4 className="font-medium text-sm text-lsc-dark dark:text-earth-50">
                          {facility.label}
                        </h4>
                      </div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {facility.value}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}
