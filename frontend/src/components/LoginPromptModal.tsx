/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { X, LogIn } from 'lucide-react'
import { useTranslation } from '@/i18n'

interface LoginPromptModalProps {
  onClose: () => void
  next?: string
}

export default function LoginPromptModal({ onClose, next = '/programs' }: LoginPromptModalProps): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    closeRef.current?.focus()
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
      <div role="dialog" aria-modal="true" aria-labelledby="login-prompt-title" className="relative z-10 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 w-full max-w-sm mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 id="login-prompt-title" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('loginPrompt.title')}
          </h2>
          <button ref={closeRef} onClick={onClose} className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors" aria-label={t('loginPrompt.cancel')}>
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {t('loginPrompt.description')}
        </p>
        <div className="flex flex-col gap-3">
          <button onClick={() => navigate(`/login?next=${encodeURIComponent(next)}`)} className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors">
            <LogIn className="w-4 h-4" aria-hidden="true" />
            {t('loginPrompt.logIn')}
          </button>
          <button onClick={() => navigate(`/signup?next=${encodeURIComponent(next)}`)} className="w-full px-4 py-3 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream rounded-xl font-semibold transition-colors">
            {t('loginPrompt.createAccount')}
          </button>
          <button onClick={onClose} className="w-full px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors">
            {t('loginPrompt.cancel')}
          </button>
        </div>
      </div>
    </div>
  )
}
