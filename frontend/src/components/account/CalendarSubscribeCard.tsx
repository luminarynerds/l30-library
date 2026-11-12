/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Patron calendar subscription card.
 *
 * Shown inside SettingsTab on the Account page. Mints a signed webcal://
 * URL the patron can subscribe to from Apple Calendar / Google Calendar /
 * Outlook to see their checkouts' due dates and ready-for-pickup holds.
 */
import { useState } from 'react'
import { Calendar, Copy, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchApi } from '@/lib/api-client'
import { useTranslation } from '@/i18n'

interface CalendarTokenResponse {
  url: string
}

export function CalendarSubscribeCard(): React.ReactElement {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [calendarUrl, setCalendarUrl] = useState<string | null>(null)

  const handleMint = async () => {
    setLoading(true)
    try {
      const data = await fetchApi<CalendarTokenResponse>('/me/calendar/token', {
        method: 'POST',
      })
      setCalendarUrl(data.url)
    } catch (_err) {
      toast.error(t('account.calendarFeed.mintFailed', 'Could not generate calendar link'))
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (!calendarUrl) return
    try {
      await navigator.clipboard.writeText(calendarUrl)
      toast.success(t('account.calendarFeed.copied', 'Calendar URL copied'))
    } catch {
      toast.error(t('account.calendarFeed.copyFailed', 'Copy failed'))
    }
  }

  // Google Calendar's subscribe-by-URL endpoint takes the webcal URL as the
  // `cid` query param. We URL-encode the whole thing.
  const googleUrl = calendarUrl
    ? `https://calendar.google.com/calendar/u/0/r?cid=${encodeURIComponent(calendarUrl)}`
    : null

  return (
    <div className="p-4 bg-cream dark:bg-earth-800 rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <Calendar className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" aria-hidden="true" />
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
          {t('account.calendarFeed.title', 'Subscribe to your calendar')}
        </h3>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/80 mb-3">
        {t(
          'account.calendarFeed.description',
          'Get a personal calendar feed with your due dates and ready holds. Works with Apple Calendar, Google Calendar, and Outlook.'
        )}
      </p>

      {!calendarUrl ? (
        <button
          type="button"
          onClick={handleMint}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-lsc-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-60"
        >
          {loading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
          {t('account.calendarFeed.getLink', 'Get calendar link')}
        </button>
      ) : (
        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              readOnly
              value={calendarUrl}
              aria-label={t('account.calendarFeed.urlLabel', 'Calendar subscription URL')}
              className="flex-1 px-3 py-2 border border-sage/30 rounded-xl bg-lsc-white dark:bg-earth-900 text-sm text-lsc-dark dark:text-lsc-cream"
              onFocus={(e) => e.currentTarget.select()}
            />
            <button
              type="button"
              onClick={handleCopy}
              aria-label={t('account.calendarFeed.copy', 'Copy URL')}
              className="inline-flex items-center gap-1 px-3 py-2 border border-sage/40 rounded-xl hover:bg-sage/10 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              <Copy className="w-4 h-4" aria-hidden="true" />
              {t('account.calendarFeed.copy', 'Copy')}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {googleUrl && (
              <a
                href={googleUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-2 border border-sage/40 rounded-xl hover:bg-sage/10 text-sm text-lsc-dark dark:text-lsc-cream"
              >
                {t('account.calendarFeed.addToGoogle', 'Add to Google Calendar')}
              </a>
            )}
            <a
              href={calendarUrl}
              className="inline-flex items-center gap-1 px-3 py-2 border border-sage/40 rounded-xl hover:bg-sage/10 text-sm text-lsc-dark dark:text-lsc-cream"
            >
              {t('account.calendarFeed.addToApple', 'Add to Apple Calendar')}
            </a>
          </div>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">
            {t(
              'account.calendarFeed.privacyNote',
              'Anyone with this link can see your due dates. Keep it private.'
            )}
          </p>
        </div>
      )}
    </div>
  )
}

export default CalendarSubscribeCard
