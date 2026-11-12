/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ChevronRight, BookOpen } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface RelatedGuide {
  id: string
  title: string
  route: string
}

interface RelatedGuidesProps {
  currentGuideId: string
}

const guideRelationships: Record<string, RelatedGuide[]> = {
  'wifi-troubleshooting': [
    { id: 'email-on-phone', title: 'Check Email on Your Phone', route: '/guides/email-on-phone' },
    { id: 'wireless-printing', title: 'Wireless Printing at the Library', route: '/guides/wireless-printing' },
  ],
  'password-reset': [
    { id: 'email-setup', title: 'Creating an Email Account', route: '/guides/email-account' },
    { id: 'email-on-phone', title: 'Check Email on Your Phone', route: '/guides/email-on-phone' },
  ],
  'email-setup': [
    { id: 'email-on-phone', title: 'Check Email on Your Phone', route: '/guides/email-on-phone' },
    { id: 'password-reset', title: 'Reset a Forgotten Password', route: '/guides/password-reset' },
  ],
  'email-on-phone': [
    { id: 'email-setup', title: 'Creating an Email Account', route: '/guides/email-account' },
    { id: 'password-reset', title: 'Reset a Forgotten Password', route: '/guides/password-reset' },
  ],
  'wireless-printing': [
    { id: 'wifi-troubleshooting', title: 'WiFi Troubleshooting', route: '/guides/wifi-troubleshooting' },
  ],
  'library-card': [
    { id: 'wifi-troubleshooting', title: 'WiFi Troubleshooting', route: '/guides/wifi-troubleshooting' },
    { id: 'email-setup', title: 'Creating an Email Account', route: '/guides/email-account' },
  ],
  'scam-recognition': [
    { id: 'password-reset', title: 'Reset a Forgotten Password', route: '/guides/password-reset' },
    { id: 'email-setup', title: 'Creating an Email Account', route: '/guides/email-account' },
  ],
}

export default function RelatedGuides({ currentGuideId }: RelatedGuidesProps): React.ReactElement | null {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { t: _t } = useTranslation()
  const related = guideRelationships[currentGuideId]

  if (!related || related.length === 0) {
    return null
  }

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mt-8">
      <h2 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-4 flex items-center gap-2">
        <BookOpen className="w-5 h-5 text-lsc-rose" />
        You Might Also Need
      </h2>
      <div className="space-y-2">
        {related.map((guide) => (
          <Link
            key={guide.id}
            to={guide.route}
            className="flex items-center justify-between p-3 rounded-lg bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-earth-700 motion-safe:transition-colors group"
          >
            <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light">
              {guide.title}
            </span>
            <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light" />
          </Link>
        ))}
      </div>
    </div>
  )
}
