/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import {
  triggerPanicAlert,
  getMyNotificationPreferences,
  setMyNotificationPreferences,
  getActivePanicAlerts,
  PanicAlert,
  PanicAlertList,
  PanicAlertNotificationPreferences,
  PanicAlertNotificationPreferencesCreate,
  PanicAlertSource,
} from '@/api/panic-alert-api'
import { usePanicAlertServiceWorker } from '@/hooks/usePanicAlertServiceWorker'
import { useAuth } from './AuthContext'
import { clean } from '@/lib/utils'

export interface PanicAlertContextType {
  // Current alert state
  lastAlertTriggered: PanicAlert | null
  isLoading: boolean
  error: string | null

  // Notification preferences
  preferences: PanicAlertNotificationPreferences | null
  preferencesLoading: boolean

  // Active alerts (for managers/admins to see)
  activeAlerts: PanicAlertList[]
  activeAlertsLoading: boolean

  // Methods
  triggerAlert: (source: PanicAlertSource, notes?: string) => Promise<PanicAlert>
  loadPreferences: () => Promise<void>
  updatePreferences: (prefs: PanicAlertNotificationPreferencesCreate) => Promise<void>
  loadActiveAlerts: (branchId?: number) => Promise<void>

  // UI state for discreet button
  showButton: boolean
  buttonPosition: 'corner' | 'hidden'

  // Device detection
  isMobileDevice: boolean
}

export const PanicAlertContext = createContext<PanicAlertContextType | undefined>(
  undefined,
)

export const PanicAlertProvider: React.FC<{
  children: React.ReactNode
}> = ({ children }) => {
  const { isAuthenticated } = useAuth()
  const [lastAlertTriggered, setLastAlertTriggered] = useState<PanicAlert | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [preferences, setPreferences] = useState<PanicAlertNotificationPreferences | null>(
    null,
  )
  const [preferencesLoading, setPreferencesLoading] = useState(false)

  const [activeAlerts, setActiveAlerts] = useState<PanicAlertList[]>([])
  const [activeAlertsLoading, setActiveAlertsLoading] = useState(false)

  const [showButton, _setShowButton] = useState(true)
  const [buttonPosition] = useState<'corner' | 'hidden'>('corner')

  const [isMobileDevice, setIsMobileDevice] = useState(false)

  // Track shake gesture on mobile
  const shakeThresholdRef = useRef(15)
  const lastShakeTimeRef = useRef(0)

  // Register service worker for system freeze resilience
  usePanicAlertServiceWorker()

  const triggerAlert = useCallback(
    async (source: PanicAlertSource, notes?: string): Promise<PanicAlert> => {
      setIsLoading(true)
      setError(null)

      try {
        const alert = await triggerPanicAlert(clean({
          activation_source: source,
          situation_notes: notes,
          metadata: {
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
          },
        }))

        setLastAlertTriggered(alert)

        // If mobile with vibration enabled, vibrate
        if (isMobileDevice && preferences?.vibration_enabled && 'vibrate' in navigator) {
          navigator.vibrate([100, 50, 100]) // Pattern: 100ms vibrate, 50ms pause, 100ms vibrate
        }

        return alert
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to trigger alert'
        setError(errorMsg)
        throw err
      } finally {
        setIsLoading(false)
      }
    },
    [isMobileDevice, preferences?.vibration_enabled],
  )


  // Detect mobile device
  useEffect(() => {
    const isMobile =
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
        navigator.userAgent,
      ) || navigator.maxTouchPoints > 2

    setIsMobileDevice(isMobile)

    // Setup shake detection if mobile
    if (isMobile && 'DeviceMotionEvent' in window) {
      const handleDeviceMotion = (event: DeviceMotionEvent) => {
        const acceleration = event.accelerationIncludingGravity
        if (!acceleration) return

        const x = acceleration.x || 0
        const y = acceleration.y || 0
        const z = acceleration.z || 0

        const shakeDetected =
          Math.abs(x) > shakeThresholdRef.current ||
          Math.abs(y) > shakeThresholdRef.current ||
          Math.abs(z) > shakeThresholdRef.current

        if (shakeDetected) {
          const now = Date.now()
          // Only trigger once per 2 seconds to avoid spam
          if (now - lastShakeTimeRef.current > 2000) {
            lastShakeTimeRef.current = now
            // Auto-trigger panic alert on shake (with user's permission)
            void triggerAlert('mobile_gesture')
          }
        }
      }

      window.addEventListener('devicemotion', handleDeviceMotion)
      return () => window.removeEventListener('devicemotion', handleDeviceMotion)


    }

  }, [])

  const loadPreferences = useCallback(async () => {
    setPreferencesLoading(true)
    try {
      const prefs = await getMyNotificationPreferences()
      setPreferences(prefs)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setPreferencesLoading(false)
    }
  }, [])

  const updatePreferences = useCallback(
    async (prefs: PanicAlertNotificationPreferencesCreate) => {
      try {
        const updated = await setMyNotificationPreferences(prefs)
        setPreferences(updated)
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to update preferences'
        setError(errorMsg)
        throw err
      }
    },
    [],
  )

  const loadActiveAlerts = useCallback(async (branchId?: number) => {
    setActiveAlertsLoading(true)
    try {
      const alerts = await getActivePanicAlerts(branchId)
      setActiveAlerts(alerts)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setActiveAlertsLoading(false)
    }
  }, [])

  // Load preferences only when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      void loadPreferences()
    }
  }, [isAuthenticated, loadPreferences])

  const value: PanicAlertContextType = {
    lastAlertTriggered,
    isLoading,
    error,
    preferences,
    preferencesLoading,
    activeAlerts,
    activeAlertsLoading,
    triggerAlert,
    loadPreferences,
    updatePreferences,
    loadActiveAlerts,
    showButton,
    buttonPosition,
    isMobileDevice,
  }

  return (
    <PanicAlertContext.Provider value={value}>
      {children}
    </PanicAlertContext.Provider>
  )
}

// Safe default when context is unavailable — prevents crashes
const defaultContext: PanicAlertContextType = {
  lastAlertTriggered: null,
  isLoading: false,
  error: null,
  preferences: null,
  preferencesLoading: false,
  activeAlerts: [],
  activeAlertsLoading: false,
  triggerAlert: async () => { throw new Error('PanicAlertProvider not available') },
  loadPreferences: async () => {},
  updatePreferences: async () => {},
  loadActiveAlerts: async () => {},
  showButton: true,
  buttonPosition: 'corner',
  isMobileDevice: false,
}

export const usePanicAlert = (): PanicAlertContextType => {
  const context = useContext(PanicAlertContext)
  if (!context) {
    Sentry.captureMessage('[PanicAlert] usePanicAlert called outside PanicAlertProvider', 'warning')
    return defaultContext
  }
  return context
}
