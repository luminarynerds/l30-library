/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useLibraryContact } from '@/hooks/useLibraryContact'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '../../i18n/I18nContext'
import { getIsOpen } from '@/api/domains/content/homepage-content-api'

function formatTo12Hour(time: string): string {
  const parts = time.split(':').map(Number)
  const h = parts[0] ?? 0
  const m = parts[1] ?? 0
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return m === 0 ? `${hour12} ${suffix}` : `${hour12}:${String(m).padStart(2, '0')} ${suffix}`
}

export function FooterAddress() {
  const branding = useBranding()
  const contact = useLibraryContact()
  const { t } = useTranslation()

  const { data: openStatus } = useQuery({
    queryKey: ['library-is-open'],
    queryFn: getIsOpen,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const libraryStatus = (() => {
    if (!openStatus) return { isOpen: false, statusText: '', statusKey: 'navigation.hoursAndLocations', statusParams: {} as Record<string, string> }
    if (openStatus.is_open) {
      const time = openStatus.closes_at ? formatTo12Hour(openStatus.closes_at) : ''
      return { isOpen: true, statusText: `Open until ${time}`, statusKey: time ? 'home.heartbeat.openUntil' : 'home.heartbeat.open', statusParams: { time } }
    }
    const time = openStatus.opens_at ? formatTo12Hour(openStatus.opens_at) : ''
    return { isOpen: false, statusText: `Opens at ${time}`, statusKey: time ? 'home.heartbeat.opensAt' : 'home.heartbeat.closed', statusParams: { time } }
  })()

  const phoneHref = contact.phone ? `tel:${contact.phone.replace(/[^+\d]/g, '')}` : ''
  const showAddress = Boolean(contact.address_line1 || contact.address_line2 || contact.city)

  return (
    <address className="not-italic">
      <span className="font-semibold text-base tracking-tight text-white">{branding.library_name || t('components.footer.l30Library')}</span>
      <div className="flex items-center gap-2 mt-2">
        <Link
          to="/branches#hours"
          className="group inline-flex items-center gap-1.5 rounded min-h-[44px] min-w-[44px] px-2 -mx-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
        >
          <span
            className={`inline-flex items-center gap-1.5 text-xs font-mono transition-colors ${
              libraryStatus.isOpen ? 'text-status-success-400 group-hover:text-status-success-300' : 'text-brand-300 group-hover:text-brand-200'
            }`}
            role="status"
            aria-live="polite"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${libraryStatus.isOpen ? 'bg-status-success-400' : 'bg-brand-300'}`}
              aria-hidden="true"
            />
            {t(libraryStatus.statusKey, libraryStatus.statusParams) || libraryStatus.statusText}
          </span>
        </Link>
      </div>
      {contact.phone && (
        <p className="text-xs text-earth-300 mt-1 font-mono">
          <a
            href={phoneHref}
            className="inline-flex items-center min-h-[44px] min-w-[44px] hover:text-white transition-colors"
            aria-label={t('footer.callPhone', { phone: contact.phone })}
          >
            {contact.phone}
          </a>
        </p>
      )}
      {showAddress && (
        <p className="text-xs text-earth-300 mt-1 font-mono not-italic">
          {contact.address_line1 && <span>{contact.address_line1}</span>}
          {contact.address_line1 && (contact.address_line2 || contact.city) && <br />}
          {contact.address_line2 && <>{contact.address_line2}<br /></>}
          <span>{[contact.city, contact.state, contact.zip_code].filter(Boolean).join(', ')}</span>
        </p>
      )}
    </address>
  )
}
