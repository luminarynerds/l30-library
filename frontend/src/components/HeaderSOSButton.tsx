/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import { triggerPanicAlert, resolvePanicAlert } from '@/api/panic-alert-api'
import { ShieldAlert, X } from 'lucide-react'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import FocusTrap from 'focus-trap-react'

type State = 'idle' | 'menu' | 'sending' | 'sent' | 'cancelling'

const REASON_KEYS = [
  { labelKey: 'components.headerSOSButton.reasonLoudDisruptive', note: 'Loud or disruptive patron' },
  { labelKey: 'components.headerSOSButton.reasonInappropriateContent', note: 'Inappropriate content on screen' },
  { labelKey: 'components.headerSOSButton.reasonThreateningBehavior', note: 'Threatening or aggressive behavior' },
  { labelKey: 'components.headerSOSButton.reasonMedicalEmergency', note: 'Medical emergency' },
  { labelKey: 'components.headerSOSButton.reasonSuspiciousActivity', note: 'Suspicious activity' },
] as const

export default function HeaderSOSButton({ variant }: { variant?: 'desktop' | 'mobile' }) {
  const { t } = useTranslation()
  const [state, setState] = useState<State>('idle')
  const [cancelSecondsLeft, setCancelSecondsLeft] = useState<number | null>(null)
  const alertIdRef = useRef<number | null>(null)
  const cancelTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)
  const buttonRef = useRef<HTMLButtonElement | null>(null)

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (cancelTimerRef.current) clearTimeout(cancelTimerRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [])

  // Close menu on click outside or Escape
  useEffect(() => {
    if (state !== 'menu') return

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      if (panelRef.current?.contains(target) || buttonRef.current?.contains(target)) return
      setState('idle')
    }

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setState('idle')
        buttonRef.current?.focus()
      }
    }

    window.addEventListener('mousedown', handleClickOutside)
    window.addEventListener('keydown', handleEscape)
    return () => {
      window.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [state])

  const handleToggleMenu = () => {
    if (state === 'idle') {
      setState('menu')
    } else if (state === 'menu') {
      setState('idle')
    }
  }

  const handleTrigger = async (reason?: string) => {
    if (state !== 'menu') return
    setState('sending')

    try {
      const alert = await triggerPanicAlert(clean({
        activation_source: 'hidden_ui_button',
        situation_notes: reason,
        metadata: {
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
        },
      }))
      alertIdRef.current = alert.id
      setState('sent')
      toast.success(t('components.headerSOSButton.alertSent'))

      // Auto-reset after 30 seconds
      cancelTimerRef.current = setTimeout(() => {
        setState('idle')
        alertIdRef.current = null
        if (countdownRef.current) clearInterval(countdownRef.current)
        countdownRef.current = null
        setCancelSecondsLeft(null)
      }, 30000)

      setCancelSecondsLeft(30)
      countdownRef.current = setInterval(() => {
        setCancelSecondsLeft(s => {
          if (s !== null && s > 1) return s - 1
          if (countdownRef.current) {
            clearInterval(countdownRef.current)
            countdownRef.current = null
          }
          return null
        })
      }, 1000)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.headerSOSButton.alertFailed'))
      setState('idle')
    }
  }

  const handleCancel = async () => {
    if (!alertIdRef.current) return
    setState('cancelling')

    try {
      await resolvePanicAlert(alertIdRef.current, 'False alarm — cancelled by user')
      if (cancelTimerRef.current) clearTimeout(cancelTimerRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
      countdownRef.current = null
      setCancelSecondsLeft(null)
      alertIdRef.current = null
      setState('idle')
      toast.success(t('components.headerSOSButton.alertCancelled'))
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      toast.error(t('components.headerSOSButton.cancelFailed'))
      setState('idle')
    }
  }

  // After alert sent: show "Oops" cancel button in place of the "?" icon
  if (state === 'sent' || state === 'cancelling') {
    return (
      <div className={variant === 'desktop' ? 'hidden lg:block' : variant === 'mobile' ? 'lg:hidden' : undefined}>
        <button
          onClick={handleCancel}
          disabled={state === 'cancelling'}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-status-danger-500/20 text-status-danger-900 dark:text-status-danger-100 hover:bg-status-danger-500/30 transition-colors"
          aria-label={t('components.headerSOSButton.cancelAlertFalseAlarm')}
        >
          {state === 'cancelling' ? (
            <span className="w-3.5 h-3.5 border-2 border-status-danger-300 border-t-transparent rounded-full motion-safe:animate-spin" />
          ) : (
            <X className="w-3.5 h-3.5" />
          )}
          <span className="font-serif italic text-base font-bold tracking-tight">
            {cancelSecondsLeft !== null
              ? t('components.headerSOSButton.cancelWithCountdown', 'Oops — false alarm ({{count}}s)').replace('{{count}}', String(cancelSecondsLeft))
              : t('components.headerSOSButton.oops')}
          </span>
        </button>
      </div>
    )
  }

  return (
    <div className={`relative${variant === 'desktop' ? ' hidden lg:block' : variant === 'mobile' ? ' lg:hidden' : ''}`}>
      {/* Trigger icon — looks like a help button */}
      <button
        ref={buttonRef}
        onClick={handleToggleMenu}
        className="relative flex items-center justify-center w-11 h-11 rounded-full text-earth-600 dark:text-earth-300 hover:bg-earth-50 dark:hover:bg-earth-800/10 hover:text-earth-950 dark:hover:text-lsc-cream transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
        aria-expanded={state === 'menu'}
        aria-haspopup="true"
        aria-label={t('aria.discretePanicButton.help')}
        title={t('components.headerSOSButton.help')}
      >
        <span className="text-base font-bold">?</span>
      </button>

      {/* Dropdown panel */}
      {state === 'menu' && (
        <FocusTrap active={state==="menu"} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
        <div
          ref={panelRef}
          className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 shadow-lg p-4 z-50"
          role="dialog"
          aria-label={t('aria.headerSOSButton.emergencyAlert')}
        >
          <div className="flex items-center gap-2 mb-3">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-status-danger-100 dark:bg-status-danger-900/40">
              <ShieldAlert className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{t('components.headerSOSButton.needHelp')}</h3>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{t('components.headerSOSButton.alertWillBeSentSilently')}</p>
            </div>
          </div>

          {/* Reason chips — tap to trigger immediately */}
          {(state as State) === 'sending' ? (
            <div className="flex items-center justify-center gap-2 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="w-4 h-4 border-2 border-status-danger-500 border-t-transparent rounded-full motion-safe:animate-spin" />
              {t('components.headerSOSButton.sendingAlert')}
            </div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {REASON_KEYS.map(({ labelKey, note }) => (
                <button
                  key={labelKey}
                  onClick={() => handleTrigger(note)}
                  className="w-full text-left rounded-lg border border-lsc-border dark:border-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 hover:border-status-danger-300 dark:hover:border-status-danger-800 transition-colors"
                >
                  {t(labelKey)}
                </button>
              ))}

              {/* Generic fallback */}
              <button
                onClick={() => handleTrigger()}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-status-danger-600 hover:bg-status-danger-700 text-white text-sm font-medium px-4 py-2.5 mt-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-danger-500 focus-visible:ring-offset-2"
              >
                <ShieldAlert className="w-4 h-4" aria-hidden="true" />
                {t('components.headerSOSButton.otherSendAlert')}
              </button>
            </div>
          )}

          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2 text-center">
            {t('components.headerSOSButton.managersWillBeNotified')}
          </p>
        </div>
        </FocusTrap>
      )}
    </div>
  )
}
