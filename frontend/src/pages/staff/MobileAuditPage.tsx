/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, Wifi, WifiOff, RefreshCw, ChevronDown } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../../contexts/AuthContext'
import { fetchApi } from '@/lib/api-client'

// ── Types ──

interface Audit {
  id: number
  name: string
  location_filter: string | null
  started_at: string
  completed_at: string | null
  items_expected: number
  items_found: number
  items_missing: number
  items_misplaced: number
}

interface QueuedScan {
  barcode: string
  auditId: number
  timestamp: number
}

type ScanStatus = 'idle' | 'in_order' | 'out_of_order' | 'not_found' | 'already_scanned'

const QUEUE_KEY = 'l30_mobile_audit_offline_queue'

function loadQueue(): QueuedScan[] {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
  } catch {
    return []
  }
}

function saveQueue(queue: QueuedScan[]): void {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
}

// ── Main Component ──

export default function MobileAuditPage(): React.ReactElement {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [audits, setAudits] = useState<Audit[]>([])
  const [selectedAuditId, setSelectedAuditId] = useState<number | null>(null)
  const [loadingAudits, setLoadingAudits] = useState(true)

  const [barcode, setBarcode] = useState('')
  const [scanning, setScanning] = useState(false)
  const [lastStatus, setLastStatus] = useState<ScanStatus>('idle')
  const [lastTitle, setLastTitle] = useState('')

  const [scannedCount, setScannedCount] = useState(0)
  const [inOrderCount, setInOrderCount] = useState(0)

  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [offlineQueue, setOfflineQueue] = useState<QueuedScan[]>(loadQueue)
  const [syncing, setSyncing] = useState(false)
  const [manualEntry, setManualEntry] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  // Auth guard
  useEffect(() => {
    if (!authLoading && (!user || user.role === 'patron')) {
      toast.error('Staff access required')
      navigate('/account')
    }
  }, [authLoading, user, navigate])

  // Online/offline listeners
  useEffect(() => {
    const goOnline = () => setIsOnline(true)
    const goOffline = () => setIsOnline(false)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  // Load active audits
  useEffect(() => {
    if (!token) return
    setLoadingAudits(true)
    fetchApi<{ items: Audit[] }>('/inventory/audits', { token })
      .then((data) => {
        const active = data.items.filter((a) => !a.completed_at)
        setAudits(active)
        if (active.length === 1 && active[0]) setSelectedAuditId(active[0].id)
      })
      .catch(() => toast.error('Failed to load audits'))
      .finally(() => setLoadingAudits(false))
  }, [token])

  const selectedAudit = audits.find((a) => a.id === selectedAuditId) ?? null

  // Refresh audit stats from server
  const refreshAudit = useCallback(async () => {
    if (!token || !selectedAuditId) return
    try {
      const updated = await fetchApi<Audit>(`/inventory/audits/${selectedAuditId}`, { token })
      setAudits((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
    } catch { /* silent */ }
  }, [token, selectedAuditId])

  // Handle scan
  const handleScan = useCallback(async () => {
    const code = barcode.trim()
    if (!code || !token || !selectedAuditId || scanning) return

    setScanning(true)
    setBarcode('')

    try {
      const result = await fetchApi<{
        id: number
        barcode: string
        catalog_title: string | null
        is_misplaced: boolean
      }>(`/inventory/audits/${selectedAuditId}/scan`, {
        method: 'POST',
        body: { barcode: code },
        token,
      })

      setScannedCount((c) => c + 1)
      if (result.is_misplaced) {
        setLastStatus('out_of_order')
        setLastTitle(result.catalog_title || code)
      } else {
        setLastStatus('in_order')
        setInOrderCount((c) => c + 1)
        setLastTitle(result.catalog_title || code)
      }
      refreshAudit()
    } catch (err: unknown) {
      const isNetworkError =
        err instanceof TypeError ||
        (err instanceof Error && err.message === 'Failed to fetch') ||
        !navigator.onLine

      if (isNetworkError) {
        // Queue for offline sync
        const scan: QueuedScan = { barcode: code, auditId: selectedAuditId, timestamp: Date.now() }
        const updated = [...offlineQueue, scan]
        setOfflineQueue(updated)
        saveQueue(updated)
        setScannedCount((c) => c + 1)
        setLastStatus('in_order')
        setLastTitle(`${code} (queued offline)`)
        toast('Scan queued offline', { icon: '!' })
      } else {
        const detail = err instanceof Error ? err.message : ''
        if (detail.includes('not found')) {
          setLastStatus('not_found')
          setLastTitle(code)
          setScannedCount((c) => c + 1)
        } else if (detail.includes('already scanned')) {
          setLastStatus('already_scanned')
          setLastTitle(code)
        } else {
          setLastStatus('not_found')
          setLastTitle(code)
          setScannedCount((c) => c + 1)
        }
      }
    } finally {
      setScanning(false)
      inputRef.current?.focus()
    }
  }, [barcode, token, selectedAuditId, scanning, offlineQueue, refreshAudit])

  // Sync offline queue
  const syncQueue = useCallback(async () => {
    if (!token || offlineQueue.length === 0 || syncing) return
    setSyncing(true)
    const remaining: QueuedScan[] = []

    for (const scan of offlineQueue) {
      try {
        await fetchApi(`/inventory/audits/${scan.auditId}/scan`, {
          method: 'POST',
          body: { barcode: scan.barcode },
          token,
        })
      } catch (err: unknown) {
        const isNetworkError =
          err instanceof TypeError ||
          (err instanceof Error && err.message === 'Failed to fetch') ||
          !navigator.onLine
        if (isNetworkError) {
          remaining.push(scan, ...offlineQueue.slice(offlineQueue.indexOf(scan) + 1))
          break
        }
        // API errors (already scanned, not found) -- drop from queue
      }
    }

    setOfflineQueue(remaining)
    saveQueue(remaining)
    setSyncing(false)
    if (remaining.length === 0) {
      toast.success('All offline scans synced')
    } else {
      toast.error(`${remaining.length} scans still queued`)
    }
    refreshAudit()
  }, [token, offlineQueue, syncing, refreshAudit])

  // Auto-sync when coming back online
  useEffect(() => {
    if (isOnline && offlineQueue.length > 0 && !syncing) {
      syncQueue()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOnline])

  const accuracyPct = scannedCount > 0 ? Math.round((inOrderCount / scannedCount) * 100) : 0

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-lsc-cream dark:bg-earth-900">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!user || user.role === 'patron') return <></>

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 flex flex-col">
      {/* ── Top bar: session + status ── */}
      <header className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {loadingAudits ? (
            <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" />
          ) : audits.length === 0 ? (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No active audits</span>
          ) : (
            <div className="relative flex-1 max-w-xs">
              <select
                value={selectedAuditId ?? ''}
                onChange={(e) => {
                  setSelectedAuditId(e.target.value ? Number(e.target.value) : null)
                  setScannedCount(0)
                  setInOrderCount(0)
                  setLastStatus('idle')
                }}
                className="w-full appearance-none bg-earth-50 dark:bg-earth-700 border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 pr-8 text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate"
                aria-label="Select audit session"
              >
                <option value="">Select session...</option>
                {audits.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600 pointer-events-none" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 ml-3">
          {offlineQueue.length > 0 && (
            <button
              onClick={syncQueue}
              disabled={syncing || !isOnline}
              className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded-lg disabled:opacity-50"
              aria-label="Sync offline scans"
            >
              <RefreshCw className={`w-3 h-3 ${syncing ? 'motion-safe:animate-spin' : ''}`} />
              {offlineQueue.length} queued
            </button>
          )}
          {isOnline ? (
            <Wifi className="w-5 h-5 text-status-success-500" aria-label="Online" />
          ) : (
            <WifiOff className="w-5 h-5 text-status-danger-500" aria-label="Offline" />
          )}
        </div>
      </header>

      {/* ── Spacer pushes controls to bottom half ── */}
      <div className="flex-1 min-h-0" />

      {/* ── Bottom 60%: scan UI ── */}
      <div className="flex flex-col px-4 pb-6 gap-4" style={{ minHeight: '60vh' }}>

        {/* Status display */}
        <div className="flex-shrink-0">
          <span className="sr-only" role="status" aria-live="assertive">
            {lastStatus === 'idle'
              ? ''
              : lastStatus === 'in_order'
                ? `In order: ${lastTitle}`
                : lastStatus === 'out_of_order'
                  ? `Misplaced: ${lastTitle}`
                  : lastStatus === 'not_found'
                    ? `Not found: ${lastTitle}`
                    : `Duplicate: ${lastTitle}`}
          </span>
          {lastStatus === 'idle' ? (
            <div className="rounded-xl bg-lsc-white dark:bg-earth-800 border-2 border-lsc-border dark:border-earth-700 p-6 text-center">
              <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
                {selectedAuditId ? 'Ready to scan' : 'Select an audit session above'}
              </p>
            </div>
          ) : lastStatus === 'in_order' ? (
            <div className="rounded-xl bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-400 dark:border-status-success-700 p-6 text-center">
              <p className="text-3xl font-bold text-status-success-600 dark:text-status-success-400">IN ORDER</p>
              <p className="text-sm text-status-success-700/70 dark:text-status-success-300/70 mt-1 truncate">{lastTitle}</p>
            </div>
          ) : lastStatus === 'out_of_order' ? (
            <div className="rounded-xl bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-400 dark:border-status-danger-700 p-6 text-center">
              <p className="text-3xl font-bold text-status-danger-600 dark:text-status-danger-400">MISPLACED</p>
              <p className="text-sm text-status-danger-700/70 dark:text-status-danger-300/70 mt-1 truncate">{lastTitle}</p>
            </div>
          ) : lastStatus === 'not_found' ? (
            <div className="rounded-xl bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-400 dark:border-status-warning-700 p-6 text-center">
              <p className="text-3xl font-bold text-status-warning-600 dark:text-status-warning-400">NOT FOUND</p>
              <p className="text-sm text-status-warning-700/70 dark:text-status-warning-300/70 mt-1 truncate">{lastTitle}</p>
            </div>
          ) : (
            <div className="rounded-xl bg-earth-100 dark:bg-earth-700/50 border-2 border-earth-300 dark:border-earth-600 p-6 text-center">
              <p className="text-3xl font-bold text-earth-600 dark:text-earth-400">DUPLICATE</p>
              <p className="text-sm text-earth-600/70 dark:text-earth-400/70 mt-1 truncate">{lastTitle}</p>
            </div>
          )}
        </div>

        {/* Running stats */}
        <div className="grid grid-cols-3 gap-3 flex-shrink-0">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 text-center border border-lsc-border dark:border-earth-700">
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{scannedCount}</p>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">Scanned</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 text-center border border-lsc-border dark:border-earth-700">
            <p className="text-3xl font-bold text-status-success-600 dark:text-status-success-400">{accuracyPct}%</p>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">In Order</p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 text-center border border-lsc-border dark:border-earth-700">
            <p className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">
              {selectedAudit ? selectedAudit.items_found : 0}
            </p>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">Total Found</p>
          </div>
        </div>

        {/* Barcode input */}
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleScan()
          }}
          className="flex-shrink-0"
        >
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              inputMode={manualEntry ? 'text' : 'none'}
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              placeholder="Scan barcode..."
              disabled={!selectedAuditId || scanning}
              autoFocus
              className="flex-1 px-4 py-4 rounded-xl border-2 border-lsc-rose/50 focus:border-lsc-rose bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-lg font-mono disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Barcode input"
            />
            <button
              type="submit"
              disabled={!selectedAuditId || !barcode.trim() || scanning}
              className="px-6 py-4 rounded-xl bg-lsc-rose text-white font-bold text-lg disabled:opacity-50 disabled:cursor-not-allowed active:bg-lsc-rose/80 min-w-[80px]"
            >
              {scanning ? (
                <Loader2 className="w-6 h-6 motion-safe:animate-spin mx-auto" />
              ) : (
                'Scan'
              )}
            </button>
          </div>
          <button
            type="button"
            onClick={() => setManualEntry((v) => !v)}
            aria-pressed={manualEntry}
            className="mt-2 text-sm text-lsc-rose dark:text-lsc-rose-light underline"
          >
            {manualEntry ? 'Disable manual keyboard entry' : 'Enable manual keyboard entry'}
          </button>
        </form>

        {/* Offline queue banner */}
        {offlineQueue.length > 0 && (
          <div className="flex items-center justify-between bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-300 dark:border-status-warning-700 rounded-xl px-4 py-3 flex-shrink-0">
            <span className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300">
              {offlineQueue.length} scan{offlineQueue.length !== 1 ? 's' : ''} queued offline
            </span>
            <button
              onClick={syncQueue}
              disabled={syncing || !isOnline}
              className="flex items-center gap-1 px-3 py-2 bg-status-warning-200 dark:bg-status-warning-800 text-status-warning-800 dark:text-status-warning-200 rounded-lg text-sm font-medium disabled:opacity-50 active:bg-status-warning-300"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'motion-safe:animate-spin' : ''}`} />
              Sync Now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
