/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-case-declarations */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * useServiceWorker Hook
 *
 * Manages Service Worker registration and offline capability for the circulation desk.
 * Features:
 * - Automatic SW registration
 * - Update detection and user prompts
 * - Online/offline status tracking
 * - Offline queue management and sync
 * - Background sync coordination
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import { API_BASE } from '@/api/types'
import { t } from '@/i18n'

// ==================== Dark Mode Helper ====================

function getThemeColor(lightColor: string, darkColor: string): string {
  if (typeof document !== 'undefined') {
    return document.documentElement.classList.contains('dark') ? darkColor : lightColor
  }
  return lightColor
}

/**
 * Light/dark hex pairs for semantic status colors used in the offline indicator
 * and update toasts. Values mirror the Tailwind status-* tokens so visuals match
 * the rest of the app even though these surfaces are rendered with inline styles.
 *
 * Tuple shape: [light, dark]
 */
const STATUS_COLOR = {
  danger: ['#ef4444', '#f87171'] as const, // status-danger-500 / status-danger-400
  info: ['#3b82f6', '#60a5fa'] as const,   // status-info-500 / status-info-400
  infoButtonBg: ['#3b82f6', '#2563eb'] as const, // status-info-500 / status-info-600
  infoSurfaceBg: ['#f0f9ff', '#1e3a5a'] as const, // light blue tint / dark blue tint
  dangerSurfaceBg: ['#fef2f2', '#3f1f1f'] as const, // status-danger-50 / dark danger tint
} as const

// ==================== Types ====================

export interface ServiceWorkerState {
  /** Whether the service worker is registered and active */
  isRegistered: boolean
  /** Whether a new version is waiting to be activated */
  hasUpdate: boolean
  /** Whether the app is currently online */
  isOnline: boolean
  /** Whether a sync is in progress */
  isSyncing: boolean
  /** Number of operations waiting in the offline queue */
  queuedOperationsCount: number
  /** Current service worker version */
  version: string | null
  /** Any registration error */
  error: Error | null
}

export interface QueuedOperation {
  id: string
  url: string
  timestamp: string
  retryCount: number
}

export interface SyncResult {
  synced: number
  failed: number
  remaining: number
}

interface ServiceWorkerMessage {
  type: string
  version?: string
  count?: number
  operations?: QueuedOperation[]
  operation?: {
    id: string
    url: string
    timestamp?: string
    error?: string
  }
  response?: unknown
  synced?: number
  failed?: number
  remaining?: number
}

// Storage key for persisting queue state
const QUEUE_STORAGE_KEY = 'lsc_sw_queue_state'

// ==================== Hook ====================

export function useServiceWorker() {
  // State
  const [state, setState] = useState<ServiceWorkerState>({
    isRegistered: false,
    hasUpdate: false,
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isSyncing: false,
    queuedOperationsCount: 0,
    version: null,
    error: null,
  })

  const [queuedOperations, setQueuedOperations] = useState<QueuedOperation[]>([])

  // Refs
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null)
  const updateToastIdRef = useRef<string | null>(null)

  // ==================== Registration ====================

  /**
   * Register the service worker
   */
  const register = useCallback(async () => {
    if (!('serviceWorker' in navigator)) {
      Sentry.captureMessage('[useServiceWorker] Service workers not supported', 'warning')
      setState((prev) => ({
        ...prev,
        error: new Error('Service workers are not supported in this browser'),
      }))
      return
    }

    try {
      console.log('[useServiceWorker] Registering service worker...')

      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
      })

      registrationRef.current = registration
      console.log('[useServiceWorker] Service worker registered:', registration.scope)

      // Handle initial state
      if (registration.active) {
        setState((prev) => ({
          ...prev,
          isRegistered: true,
          error: null,
        }))
        requestVersion()
        requestQueueStatus()
        sendApiBaseToServiceWorker()
      }

      // Handle installing worker
      if (registration.installing) {
        trackInstallation(registration.installing)
      }

      // Handle waiting worker (update available)
      if (registration.waiting) {
        setState((prev) => ({ ...prev, hasUpdate: true }))
        showUpdateNotification()
      }

      // Listen for new workers
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (newWorker) {
          trackInstallation(newWorker)
        }
      })

      // Check for updates periodically (every 30 minutes)
      setInterval(() => {
        registration.update().catch((e) => Sentry.captureException(e instanceof Error ? e : new Error(String(e))))
      }, 30 * 60 * 1000)

    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      setState((prev) => ({
        ...prev,
        isRegistered: false,
        error: error instanceof Error ? error : new Error('Registration failed'),
      }))
     
     
    }
   
  }, [])

  /**
   * Track the installation progress of a service worker
   */
  const trackInstallation = useCallback((worker: ServiceWorker) => {
    worker.addEventListener('statechange', () => {
      console.log('[useServiceWorker] Worker state changed:', worker.state)

      if (worker.state === 'installed') {
        if (navigator.serviceWorker.controller) {
          // New update is waiting
          setState((prev) => ({ ...prev, hasUpdate: true }))
          showUpdateNotification()
        } else {
          // First installation
          setState((prev) => ({ ...prev, isRegistered: true }))
          toast.success(t('toast.common.appReadyForOfflineUse'))
        }
      }

      if (worker.state === 'activated') {
        setState((prev) => ({
          ...prev,
          isRegistered: true,
          hasUpdate: false,
        }))
        requestVersion()
        requestQueueStatus()
        sendApiBaseToServiceWorker()
      }
     
     
    })
   
  }, [])

  /**
   * Show update notification to user
   */
  const showUpdateNotification = useCallback(() => {
    // Dismiss any existing update toast
    if (updateToastIdRef.current) {
      toast.dismiss(updateToastIdRef.current)
    }

    updateToastIdRef.current = toast(
      (t) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span><strong>Update available!</strong></span>
          <span style={{ fontSize: '0.875rem' }}>A new version of the app is ready.</span>
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              onClick={() => {
                applyUpdate()
                toast.dismiss(t.id)
              }}
              style={{
                background: getThemeColor('#e07d4c', '#f59e6b'),
                color: 'white',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Update Now
            </button>
            <button
              onClick={() => toast.dismiss(t.id)}
              style={{
                background: 'transparent',
                border: `1px solid ${getThemeColor('#ccc', '#6b7280')}`,
                color: getThemeColor('#374151', '#d1d5db'),
                padding: '6px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Later
            </button>
          </div>
        </div>
      ),
      {
        duration: Infinity,
        position: 'bottom-right',
      }
     
     
    )
   
  }, [])

  /**
   * Apply the waiting update
   */
  const applyUpdate = useCallback(() => {
    const registration = registrationRef.current
    if (!registration?.waiting) return

    // Tell the waiting worker to skip waiting
    registration.waiting.postMessage({ type: 'SKIP_WAITING' })

    // Reload the page when the new worker takes over
    let refreshing = false
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (refreshing) return
      refreshing = true
      window.location.reload()
    })
  }, [])

  // ==================== Message Handling ====================

  /**
   * Request version from service worker
   */
  const requestVersion = useCallback(() => {
    navigator.serviceWorker.controller?.postMessage({ type: 'GET_VERSION' })
  }, [])

  /**
   * Request queue status from service worker
   */
  const requestQueueStatus = useCallback(() => {
    navigator.serviceWorker.controller?.postMessage({ type: 'GET_QUEUE_STATUS' })
  }, [])

  const sendApiBaseToServiceWorker = useCallback(() => {
    if (!navigator.serviceWorker.controller || !API_BASE) return
    navigator.serviceWorker.controller.postMessage({
      type: 'SET_API_BASE',
      payload: { apiBase: API_BASE },
    })
  }, [])

  /**
   * Handle messages from service worker
   */
  const handleServiceWorkerMessage = useCallback((event: MessageEvent<ServiceWorkerMessage>) => {
    const { type } = event.data

    switch (type) {
      case 'SW_ACTIVATED':
        setState((prev) => ({
          ...prev,
          isRegistered: true,
          hasUpdate: false,
          version: event.data.version || null,
        }))
        requestQueueStatus()
        sendApiBaseToServiceWorker()
        break

      case 'VERSION':
        setState((prev) => ({ ...prev, version: event.data.version || null }))
        break

      case 'QUEUE_STATUS':
        setQueuedOperations(event.data.operations || [])
        setState((prev) => ({
          ...prev,
          queuedOperationsCount: event.data.count || 0,
        }))
        break

      case 'OPERATION_QUEUED':
        // An operation was queued while offline
        setState((prev) => ({
          ...prev,
          queuedOperationsCount: prev.queuedOperationsCount + 1,
        }))
        if (event.data.operation) {
          setQueuedOperations((prev) => [
            ...prev,
            {
              id: event.data.operation!.id,
              url: event.data.operation!.url,
              timestamp: event.data.operation!.timestamp || new Date().toISOString(),
              retryCount: 0,
            },
          ])
        }
        toast('Operation saved for sync', {
          icon: '⏳',
          duration: 5000,
        })
        break

      case 'OPERATION_SYNCED':
        // An operation was successfully synced
        if (event.data.operation) {
          setQueuedOperations((prev) =>
            prev.filter((op) => op.id !== event.data.operation!.id)
          )
          setState((prev) => ({
            ...prev,
            queuedOperationsCount: Math.max(0, prev.queuedOperationsCount - 1),
          }))
        }
        break

      case 'OPERATION_FAILED':
        // An operation permanently failed
        if (event.data.operation) {
          setQueuedOperations((prev) =>
            prev.filter((op) => op.id !== event.data.operation!.id)
          )
          toast.error(t('toast.common.failedToSyncErrorasyncissue', { errorasyncissue: event.data.operation.error || 'a sync issue' }))
        }
        break

      case 'SYNC_COMPLETE':
        setState((prev) => ({ ...prev, isSyncing: false }))
        const { synced = 0, failed = 0, remaining = 0 } = event.data
        if (synced > 0) {
          toast.success(t('toast.common.syncedSyncedOperationsynced1s', { synced: synced, synced1s: synced !== 1 ? 's' : '' }))
        }
        if (failed > 0) {
          toast.error(t('toast.common.failedOperationfailed1sFailedToSync', { failed: failed, failed1s: failed !== 1 ? 's' : '' }))
        }
        if (remaining > 0) {
          toast(`${remaining} operation${remaining !== 1 ? 's' : ''} will retry later`, {
            icon: '⏳',
          })
        }
        requestQueueStatus()
        sendApiBaseToServiceWorker()
        break

      default:
        console.log('[useServiceWorker] Unknown message type:', type)
     
     
    }
   
  }, [requestQueueStatus])

  // ==================== Online/Offline Handling ====================

  /**
   * Handle online status change
   */
  const handleOnline = useCallback(() => {
    setState((prev) => ({ ...prev, isOnline: true }))
    toast.success(t('toast.common.backOnline'))

    // Trigger sync if we have queued operations
    if (state.queuedOperationsCount > 0) {
      syncNow()
     
     
    }
   
  }, [state.queuedOperationsCount])

  /**
   * Handle offline status change
   */
  const handleOffline = useCallback(() => {
    setState((prev) => ({ ...prev, isOnline: false }))
    toast('You are offline. Changes will be saved locally.', {
      icon: '📴',
      duration: 5000,
    })
  }, [])

  // ==================== Sync Operations ====================

  /**
   * Manually trigger sync
   */
  const syncNow = useCallback(async (): Promise<SyncResult | null> => {
    if (!navigator.serviceWorker.controller) {
      Sentry.captureMessage('[useServiceWorker] No active service worker', 'warning')
      return null
    }

    if (!state.isOnline) {
      toast.error(t('toast.common.syncingIsntAvailableWhileOffline'))
      return null
    }

    if (state.queuedOperationsCount === 0) {
      toast('No operations to sync', { icon: '✓' })
      return { synced: 0, failed: 0, remaining: 0 }
    }

    setState((prev) => ({ ...prev, isSyncing: true }))
    toast.loading('Syncing...', { id: 'sync-toast' })

    // Request sync from service worker
    navigator.serviceWorker.controller.postMessage({ type: 'SYNC_OFFLINE_QUEUE' })

    // Also try background sync API if available
    if ('sync' in navigator.serviceWorker.ready) {
      try {
        const registration = await navigator.serviceWorker.ready
        await (registration as ServiceWorkerRegistration & { sync: { register: (tag: string) => Promise<void> } }).sync.register('circulation-sync')
      } catch (error: unknown) {
        console.log('[useServiceWorker] Background sync not available:', error)
      }
    }

    return null // Result will come via message
  }, [state.isOnline, state.queuedOperationsCount])

  /**
   * Clear all caches
   */
  const clearCaches = useCallback(async () => {
    navigator.serviceWorker.controller?.postMessage({ type: 'CLEAR_CACHES' })
    toast.success(t('toast.common.cachesCleared'))
  }, [])

  /**
   * Unregister the service worker
   */
  const unregister = useCallback(async () => {
    if (registrationRef.current) {
      await registrationRef.current.unregister()
      registrationRef.current = null
      setState((prev) => ({
        ...prev,
        isRegistered: false,
        hasUpdate: false,
        version: null,
      }))
      toast.success(t('toast.common.serviceWorkerUnregistered'))
    }
  }, [])

  // ==================== Effects ====================

  // Register service worker on mount
  useEffect(() => {
    register()
  }, [register])

  // Set up message listener
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', handleServiceWorkerMessage)
      return () => {
        navigator.serviceWorker.removeEventListener('message', handleServiceWorkerMessage)
      }
    }
  }, [handleServiceWorkerMessage])

  // Set up online/offline listeners
  useEffect(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [handleOnline, handleOffline])

  // Persist queue state for UI restoration
  useEffect(() => {
    if (queuedOperations.length > 0) {
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify({
        count: queuedOperations.length,
        lastUpdated: new Date().toISOString(),
      }))
    } else {
      localStorage.removeItem(QUEUE_STORAGE_KEY)
    }
  }, [queuedOperations])

  // Restore queue state on mount
  useEffect(() => {
    const savedState = localStorage.getItem(QUEUE_STORAGE_KEY)
    if (savedState) {
      try {
        const { count } = JSON.parse(savedState)
        setState((prev) => ({
          ...prev,
          queuedOperationsCount: count,
        }))
      } catch {
        // Ignore parse errors
      }
    }
  }, [])

  // Request queue status when coming back online
  useEffect(() => {
    if (state.isOnline && state.isRegistered) {
      requestQueueStatus()
    }
  }, [state.isOnline, state.isRegistered, requestQueueStatus])

  // ==================== Return ====================

  return {
    // State
    ...state,
    queuedOperations,

    // Actions
    register,
    unregister,
    applyUpdate,
    syncNow,
    clearCaches,
    requestQueueStatus,
  }
}

// ==================== Utility Hook for Offline Status ====================

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  )

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return isOnline
}

// ==================== Offline Indicator Component ====================

export function OfflineIndicator() {
  const { isOnline, isSyncing, queuedOperationsCount, syncNow } = useServiceWorker()

  if (isOnline && queuedOperationsCount === 0) {
    return null
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '4px 12px',
        background: isOnline
          ? getThemeColor(...STATUS_COLOR.infoSurfaceBg)
          : getThemeColor(...STATUS_COLOR.dangerSurfaceBg),
        borderRadius: '9999px',
        fontSize: '0.875rem',
      }}
    >
      {!isOnline && (
        <>
          <span style={{ color: getThemeColor(...STATUS_COLOR.danger) }}>Offline</span>
        </>
      )}
      {queuedOperationsCount > 0 && (
        <>
          <span style={{ color: isOnline ? getThemeColor(...STATUS_COLOR.info) : getThemeColor(...STATUS_COLOR.danger) }}>
            {queuedOperationsCount} pending
          </span>
          {isOnline && !isSyncing && (
            <button
              onClick={syncNow}
              style={{
                background: getThemeColor(...STATUS_COLOR.infoButtonBg),
                color: 'white',
                border: 'none',
                padding: '2px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem',
              }}
            >
              Sync
            </button>
          )}
          {isSyncing && (
            <span style={{ color: getThemeColor(...STATUS_COLOR.info) }}>Syncing...</span>
          )}
        </>
      )}
    </div>
  )
}

export default useServiceWorker
