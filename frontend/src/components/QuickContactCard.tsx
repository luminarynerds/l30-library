/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Phone } from 'lucide-react'
import { useBranding } from '@/contexts/BrandingContext'
import { useTranslation } from '@/i18n'

interface QuickContactCardProps {
  variant?: 'full' | 'compact'
}

const CRISIS_NUMBERS = [
  { label: '211', description: 'Community services', tel: '211' },
  { label: '988', description: 'Mental health crisis', tel: '988' },
  { label: '911', description: 'Emergency', tel: '911' },
]

export default function QuickContactCard({ variant = 'full' }: QuickContactCardProps) {
  const branding = useBranding()
  const { t } = useTranslation()
  const phoneTel = branding.phone.replace(/\D/g, '')
  const PHONE_NUMBERS = [
    { label: 'Main Line', number: branding.phone, tel: phoneTel },
    { label: 'Tech Help', number: `${branding.phone} ext. 5`, tel: `${phoneTel},5` },
    { label: "Children's", number: `${branding.phone} ext. 3`, tel: `${phoneTel},3` },
    { label: 'Reference', number: `${branding.phone} ext. 2`, tel: `${phoneTel},2` },
  ]
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Phone aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">Quick Numbers</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4">
        {PHONE_NUMBERS.map(({ label, number, tel }) => (
          <a
            key={label}
            href={`tel:${tel}`}
            className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors group"
          >
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
            <span className="text-sm font-medium text-lsc-rose dark:text-lsc-rose-light group-hover:underline">{number}</span>
          </a>
        ))}
      </div>

      {/* 711 / Ohio Relay -- replaces the hardcoded fake TTY number. */}
      {branding.phone && (
        <div className="border-t border-lsc-border dark:border-earth-700 pt-3 mt-3 bg-earth-50 dark:bg-earth-800/30 rounded-lg -mx-2 px-3 py-2">
          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            {t('contact.relay711Heading')}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('contact.relay711Body', { phone: branding.phone })}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {t('contact.relayVrsBody', { phone: branding.phone })}
          </p>
        </div>
      )}

      {variant === 'full' && (
        <div className="border-t border-lsc-border dark:border-earth-700 pt-3 mt-3">
          <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/60 uppercase tracking-wide mb-2">Crisis Lines</p>
          <div className="flex flex-wrap gap-2">
            {CRISIS_NUMBERS.map(({ label, description, tel }) => (
              <a
                key={label}
                href={`tel:${tel}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded-lg text-sm font-medium hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 transition-colors"
              >
                <Phone aria-hidden="true" className="w-3 h-3" />
                {label} &mdash; {description}
              </a>
            ))}
          </div>
        </div>
      )}

      {variant === 'full' && (
        <div className="border-t border-lsc-border dark:border-earth-700 pt-3 mt-3">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Mon-Thu: 9 AM - 8 PM &middot; Fri-Sat: 10 AM - 6 PM &middot; Sun: 9 AM - 8 PM
          </p>
        </div>
      )}
    </div>
  )
}
