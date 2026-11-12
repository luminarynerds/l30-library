/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef, useId } from 'react'
import { ShieldAlert, MapPin, Volume2, VolumeX } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useAuth } from '../contexts/AuthContext'
import { usePanicAlert } from '../contexts/PanicAlertContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { getActivePanicAlerts, getPanicAlert, acknowledgePanicAlert, type PanicAlert, type PanicAlertList } from '@/api/panic-alert-api'
import { useAlertAudio, DEFAULT_ALERT_SOUND, type AlertSoundPreset } from '@/hooks/useAlertAudio'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

const MANAGER_ROLES = ['admin', 'super_admin', 'staff', 'director']

export default function PanicAlertOverlay() {
  const { user, isAuthenticated } = useAuth()
  const { preferences } = usePanicAlert()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const emergencyServicesEnabled = isFeatureEnabled('emergency_services_enabled')
  const soundPreference: AlertSoundPreset =
    (preferences?.sound_preference as AlertSoundPreset | undefined) ?? DEFAULT_ALERT_SOUND
  const { start: startAlarm, stop: stopAlarm } = useAlertAudio({ preset: soundPreference })
  const { settings } = useAccessibility()
  const [activeAlerts, setActiveAlerts] = useState<PanicAlertList[]>([])
  const [latestAlertDetail, setLatestAlertDetail] = useState<PanicAlert | null>(null)
  const [showBanner, setShowBanner] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [muted, setMuted] = useState(false)
  const [acknowledging, setAcknowledging] = useState(false)
  const previousCountRef = useRef(0)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const titleId = useId()

  const isManager = user && MANAGER_ROLES.includes(user.role)

  // Poll for active alerts: 5s when alerts active, 15s when idle.
  // Skip entirely when emergency_services flag is off — backend 404s on the route.
  useEffect(() => {
    if (!isAuthenticated || !isManager || !emergencyServicesEnabled) return

    const poll = async () => {
      try {
        const alerts = await getActivePanicAlerts()
        setActiveAlerts(alerts)
      } catch {
        // Silent fail on poll
      }
    }

    poll()
    const interval = activeAlerts.length > 0 ? 5000 : 15000
    pollIntervalRef.current = setInterval(poll, interval)

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [isAuthenticated, isManager, activeAlerts.length, emergencyServicesEnabled])

  // Trigger alarm when NEW alerts appear
  useEffect(() => {
    const currentCount = activeAlerts.length

    if (currentCount > previousCountRef.current && currentCount > 0) {
      previousFocusRef.current = document.activeElement as HTMLElement
      setShowBanner(true)
      setDismissed(false)
      if (!muted) startAlarm()

      // Fetch full alert record for situation_notes (list endpoint omits it)
      const firstAlert = activeAlerts[0]
      if (!firstAlert) return
      const latestId = firstAlert.id
      const showNotification = (body: string) => {
        if ('Notification' in window && Notification.permission === 'granted') {
          navigator.serviceWorker?.ready.then((reg) => {
            reg.showNotification('PANIC ALERT', {
              body,
              icon: '/icon-192x192.png',
              tag: 'panic-alert',
              requireInteraction: true,
              vibrate: [200, 100, 200, 100, 200],
            } as NotificationOptions)
          })
        }
      }
      getPanicAlert(latestId)
        .then((detail) => {
          setLatestAlertDetail(detail)
          showNotification(detail.situation_notes || 'Emergency alert triggered by staff')
        })
        .catch(() => {
          showNotification('Emergency alert triggered by staff')
        })
    }

    if (currentCount === 0 && previousCountRef.current > 0) {
      stopAlarm()
      setShowBanner(false)
      setLatestAlertDetail(null)
    }

    previousCountRef.current = currentCount
  }, [activeAlerts, muted, startAlarm, stopAlarm])

  // Request notification permission on mount for managers
  useEffect(() => {
    if (isManager && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [isManager])

  // Restore focus on dismiss
  const restoreFocus = useCallback(() => {
    if (previousFocusRef.current) {
      previousFocusRef.current.focus()
      previousFocusRef.current = null
    }
  }, [])

  const handleAcknowledge = async () => {
    const firstAlert = activeAlerts[0]
    if (!firstAlert) return
    setAcknowledging(true)
    try {
      await acknowledgePanicAlert(firstAlert.id)
      stopAlarm()
      setShowBanner(false)
      setDismissed(true)
      restoreFocus()
    } catch {
      stopAlarm()
      setShowBanner(false)
      restoreFocus()
    } finally {
      setAcknowledging(false)
    }
  }

  const handleDismiss = () => {
    stopAlarm()
    setShowBanner(false)
    setDismissed(true)
    restoreFocus()
  }

  const toggleMute = () => {
    if (muted) {
      setMuted(false)
      if (activeAlerts.length > 0 && showBanner) startAlarm()
    } else {
      setMuted(true)
      stopAlarm()
    }
  }

  if (!emergencyServicesEnabled || !isManager || !showBanner || dismissed || activeAlerts.length === 0) {
    return null
  }

  const latest = activeAlerts[0]
  if (!latest) return null
  const reduceMotion = settings.reduceMotion

  return (
    <FocusTrap
      active={showBanner}
      focusTrapOptions={{
        escapeDeactivates: false,
        allowOutsideClick: false,
        returnFocusOnDeactivate: true,
        fallbackFocus: () => document.body,
      }}
    >
      <div
        className={`fixed inset-0 z-[99999] flex items-center justify-center bg-status-danger-600/95 ${reduceMotion ? '' : 'animate-pulse'}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={`${titleId}-desc`}
      >
        <div className="text-center text-white max-w-lg mx-auto p-8">
          <ShieldAlert className={`h-24 w-24 mx-auto mb-6 ${reduceMotion ? '' : 'animate-bounce'}`} aria-hidden="true" />
          <h1 id={titleId} className="text-4xl font-black mb-4">PANIC ALERT</h1>
          <p id={`${titleId}-desc`} className="text-2xl font-semibold mb-2">
            {latestAlertDetail?.situation_notes || 'Staff needs immediate help'}
          </p>
          {latest.branch_id && (
            <p className="text-xl mb-2 flex items-center justify-center gap-2">
              <MapPin className="h-5 w-5" aria-hidden="true" />
              Branch #{latest.branch_id}
            </p>
          )}
          <p className="text-lg opacity-90 mb-8">
            {activeAlerts.length} active alert{activeAlerts.length > 1 ? 's' : ''}
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <button
              onClick={handleAcknowledge}
              disabled={acknowledging}
              className="px-8 py-4 bg-lsc-cream text-status-danger-700 font-bold text-lg rounded-lg hover:bg-earth-100 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-cream focus:ring-offset-2 focus:ring-offset-status-danger-600"
              aria-label={acknowledging ? 'Acknowledging alert' : 'Acknowledge and respond to panic alert'}
            >
              {acknowledging ? 'Acknowledging...' : 'Acknowledge & Respond'}
            </button>
            <button
              onClick={handleDismiss}
              className="px-8 py-4 bg-status-danger-800 text-white font-bold text-lg rounded-lg hover:bg-status-danger-900 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-status-danger-600"
              aria-label="Dismiss panic alert"
            >
              Dismiss
            </button>
            <button
              onClick={toggleMute}
              className="px-4 py-4 bg-status-danger-800/50 text-white rounded-lg hover:bg-status-danger-900 transition-colors focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-status-danger-600"
              aria-label={muted ? 'Unmute alarm' : 'Mute alarm'}
            >
              {muted ? <VolumeX className="h-6 w-6" aria-hidden="true" /> : <Volume2 className="h-6 w-6" aria-hidden="true" />}
            </button>
          </div>
          <a
            href="/staff/panic-alerts"
            className="inline-block mt-6 text-white/80 underline hover:text-white focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-status-danger-600 rounded"
          >
            Go to panic alerts dashboard
          </a>
        </div>
      </div>
    </FocusTrap>
  )
}
