/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ExternalLink, MapPin, Phone, Scale } from 'lucide-react'
import type { LegalProviderSummary } from '@/api/legal-api'
import { useTranslation } from '@/i18n'

interface QuickAccessProvidersProps {
  providers: LegalProviderSummary[]
}

export default function QuickAccessProviders({ providers }: QuickAccessProvidersProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (providers.length === 0) return null

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6 mb-8">
      <div className="flex items-center gap-2 mb-6">
        <ExternalLink aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
          {t('components.legal.quickAccessProviders.quickAccessToLegalHelp', 'Quick Access to Legal Help')}
        </h2>
      </div>
      <ul className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 list-none p-0 m-0" role="list" aria-label={t('aria.legalResources.legalServiceProviders', 'Legal service providers')}>
        {providers.slice(0, 4).map((provider) => (
          <li
            key={provider.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700"
          >
            <div className="flex items-center gap-2 mb-3">
              <Scale aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              <h3 className="font-medium text-lsc-dark dark:text-earth-50 line-clamp-2 leading-snug" title={provider.name}>{provider.name}</h3>
            </div>
            <div className="space-y-2 text-sm">
              {provider.phone && (
                <a
                  href={`tel:${provider.phone.replace(/[^\d+]/g, '')}`}
                  aria-label={`Call ${provider.name} at ${provider.phone}`}
                  className="flex items-center gap-2 min-h-[44px] text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                >
                  <Phone aria-hidden="true" className="w-4 h-4" />
                  {provider.phone}
                </a>
              )}
              {provider.city && (
                <p className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <MapPin aria-hidden="true" className="w-4 h-4" />
                  {provider.city}, {provider.state}
                </p>
              )}
              {provider.virtual_services && (
                <span
                  className="inline-block px-2 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded text-xs"
                  title={t('components.legal.quickAccessProviders.phoneAndVideoConsultations', 'Phone and video consultations available')}
                >
                  {t('components.legal.quickAccessProviders.phoneAndVideoAvailable', 'Phone & Video Available')}
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
