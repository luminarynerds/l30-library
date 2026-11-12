/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import { useTranslation } from '../../i18n/I18nContext'
import { subscribeToNewsletter } from '@/api/marketing-api'

type SubscribeStatus = 'idle' | 'submitting' | 'success' | 'error' | 'invalid'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function FooterNewsletterForm() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<SubscribeStatus>('idle')

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (status === 'submitting') return
    if (!EMAIL_RE.test(email.trim())) {
      setStatus('invalid')
      return
    }
    setStatus('submitting')
    try {
      await subscribeToNewsletter({ email: email.trim(), consent_source: 'newsletter_form' })
      setStatus('success')
      setEmail('')
    } catch {
      setStatus('error')
    }
  }, [email, status])

  return (
    <div data-focus-hide className="border-t border-earth-800 pt-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
        <form onSubmit={handleSubmit} className="flex gap-2 w-full sm:w-auto sm:max-w-md" noValidate>
          <label htmlFor="footer-newsletter-email" className="sr-only">{t('footer.emailPlaceholder')}</label>
          <input
            id="footer-newsletter-email"
            type="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (status === 'invalid' || status === 'error') setStatus('idle')
            }}
            placeholder={t('footer.emailPlaceholder')}
            disabled={status === 'submitting'}
            aria-invalid={status === 'invalid'}
            aria-describedby="footer-newsletter-status"
            className="flex-1 min-w-0 bg-earth-900 text-white text-sm px-3 py-2 rounded-lg border border-earth-800 placeholder:text-earth-300 focus:outline-none focus:border-lsc-rose disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={status === 'submitting'}
            className="px-4 py-2 bg-lsc-rose hover:bg-status-warning-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {status === 'submitting' ? t('footer.subscribing') : t('footer.subscribe')}
          </button>
        </form>
      </div>
      <p id="footer-newsletter-status" role="status" aria-live="polite" className="text-xs mt-2 min-h-[1rem]">
        {status === 'success' && <span className="text-status-success-400">{t('footer.subscribeSuccess')}</span>}
        {status === 'invalid' && <span className="text-status-danger-300">{t('footer.subscribeInvalid')}</span>}
        {status === 'error' && <span className="text-status-danger-300">{t('footer.subscribeError')}</span>}
      </p>
    </div>
  )
}
