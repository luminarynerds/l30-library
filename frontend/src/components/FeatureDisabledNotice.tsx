/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ToggleLeft } from 'lucide-react'

// Acronyms that should stay uppercase when we humanize a feature flag key.
const ACRONYMS = new Set(['ai', 'edi', 'sip2', 'rfid', 'ill', 'ama', 'z3950', 'sms'])

export function humanizeFeature(feature: string): string {
  const words = feature
    .replace(/_enabled$/, '')
    .split('_')
    .filter(Boolean)
    .map((w) => (ACRONYMS.has(w) ? w.toUpperCase() : w))
  const phrase = words.join(' ')
  return phrase.charAt(0).toUpperCase() + phrase.slice(1)
}

interface FeatureDisabledNoticeProps {
  feature: string
}

/**
 * Shown in place of a page whose org feature flag is turned off. Replaces the
 * old `<Navigate to="/404">` so a switched-off feature reads as "turned off"
 * (with a way to turn it back on) instead of a misleading "page not found".
 */
export default function FeatureDisabledNotice({ feature }: FeatureDisabledNoticeProps) {
  const name = humanizeFeature(feature)

  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4 py-12">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-earth-100 dark:bg-earth-800">
          <ToggleLeft className="h-7 w-7 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
        <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
          {name} is turned off
        </h1>
        <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70">
          This feature is switched off for your library, so its page is not
          available right now. An administrator can turn it back on from the
          library configuration settings.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/staff/admin/library-config#features"
            className="inline-flex items-center justify-center min-h-[44px] px-4 py-2 rounded-lg bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900 transition-colors"
          >
            Manage features
          </Link>
          <Link
            to="/staff/admin"
            className="inline-flex items-center justify-center min-h-[44px] px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream font-medium hover:bg-earth-100 dark:hover:bg-earth-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900 transition-colors"
          >
            Back to admin
          </Link>
        </div>
      </div>
    </div>
  )
}
