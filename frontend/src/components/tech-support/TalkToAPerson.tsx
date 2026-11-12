/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Clock, MapPin, Phone, HelpCircle, Calendar } from 'lucide-react'
import type { TechHelpOption } from '@/api/tech-support-api'
import { useTranslation } from '@/i18n'

interface TalkToAPersonProps {
  options: TechHelpOption[]
}

// Stable icon-name -> glyph map. Keys match the lucide-react icon names
// the backend stores in `TechHelpOption.icon`. Small by design — extend
// only when a new help-option icon is actually used.
// Stored kebab-case in tech_help_options.icon (lucide-icon-name convention).
const ICON_BY_NAME: Record<string, React.ReactNode> = {
  'help-circle': <HelpCircle aria-hidden="true" className="w-6 h-6" />,
  'calendar': <Calendar aria-hidden="true" className="w-6 h-6" />,
  'phone': <Phone aria-hidden="true" className="w-6 h-6" />,
}

function getIcon(option: TechHelpOption): React.ReactNode {
  if (option.phone) {
    return <Phone aria-hidden="true" className="w-6 h-6" />
  }
  if (option.icon && option.icon in ICON_BY_NAME) {
    return ICON_BY_NAME[option.icon]
  }
  return <HelpCircle aria-hidden="true" className="w-6 h-6" />
}

// Appointments are identified by `icon === 'calendar'` (stable data
// field, stored kebab-case), not the display title.
function isAppointment(option: TechHelpOption): boolean {
  return option.icon === 'calendar'
}

export default function TalkToAPerson({ options }: TalkToAPersonProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (!options || options.length === 0) {
    return null
  }

  return (
    <section
      aria-labelledby="tech-help-people-heading"
      className="mb-10 p-5 sm:p-6 bg-sage-50 dark:bg-sage-900/20 border border-sage-200 dark:border-sage-800 rounded-xl"
      data-testid="tech-talk-to-a-person"
    >
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle aria-hidden="true" className="w-5 h-5 text-sage-700 dark:text-sage-300" />
        <h2
          id="tech-help-people-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50"
        >
          {t('techSupport.talkToAPersonHeading', 'Need to talk to a person?')}
        </h2>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {options.map((option) => {
          const isHotline = Boolean(option.phone)
          return (
            <div
              key={option.title}
              className="flex flex-col bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lsc-rose dark:text-lsc-rose-light">{getIcon(option)}</span>
                <h3 className="font-serif font-semibold text-base text-lsc-dark dark:text-earth-50">
                  {option.title}
                </h3>
              </div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                {option.description}
              </p>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1 mb-3">
                <p className="flex items-center gap-1.5">
                  <Clock aria-hidden="true" className="w-3.5 h-3.5" />
                  {option.schedule}
                </p>
                {option.location && (
                  <p className="flex items-center gap-1.5">
                    <MapPin aria-hidden="true" className="w-3.5 h-3.5" />
                    {option.location}
                  </p>
                )}
                {option.phone && (
                  <p className="flex items-center gap-1.5">
                    <Phone aria-hidden="true" className="w-3.5 h-3.5" />
                    {option.phone}
                  </p>
                )}
              </div>
              <div className="mt-auto">
                {isHotline && option.phone ? (
                  <a
                    href={`tel:${option.phone.replace(/[^\d+]/g, '')}`}
                    // params form required: 'phone' is a branding default, so the
                    // string-fallback t().replace() pattern gets pre-empted by branding
                    aria-label={t('techSupport.callPhoneAriaLabel', { phone: option.phone })}
                    className="inline-flex items-center justify-center w-full min-h-[44px] px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                    data-testid="tech-help-hotline-call"
                  >
                    <Phone aria-hidden="true" className="w-4 h-4 mr-1.5" />
                    {t('techSupport.callNowLabel', 'Call Now')}
                  </a>
                ) : (
                  <Link
                    to={isAppointment(option) ? '/events' : '/guides'}
                    className="inline-flex items-center justify-center w-full min-h-[44px] px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
                    aria-label={isAppointment(option) ? undefined : t('techSupport.learnMoreAboutAriaLabel', 'Learn more about {{title}}').replace('{{title}}', option.title)}
                  >
                    {isAppointment(option)
                      ? t('techSupport.bookAppointmentLabel', 'Book Appointment')
                      : t('techSupport.learnMoreLabel', 'Learn More')}
                  </Link>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
