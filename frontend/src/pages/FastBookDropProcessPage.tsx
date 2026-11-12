/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Fast Book Drop Processing Page
 *
 * Optimized UI for high-volume book drop processing:
 * - Continuous barcode scanning without stopping
 * - Auto-detect holds (yellow alert)
 * - Auto-detect transit items (blue alert)
 * - Visual/audio sorting cues
 * - Conditional damage check prompting
 * - Running count by destination
 * - Auto-print sorting slips for transit items
 * - Inline claims returned resolution
 * - Target: 100 returns in under 10 minutes
 */

import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  startCheckInSession,
  listActiveSessions,
  fastProcessingScan,
  endSession,
} from "../api/book-drop-api"
import {
  AlertCircle,
  Volume2,
  Loader2,
  Play,
  Square,
  Home,
  Zap,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface SessionData {
  id: number
  session_code: string
  branch_location: string
  status: string
  total_items: number
  successful_checkins: number
  holds_trapped: number
  transits_created: number
  exceptions_count: number
}

interface FastProcessingResponse {
  check_in_result_id: number
  barcode: string
  status: string
  sort_destination: string | null
  sort_color: string
  sort_sound: string
  hold_patron_name: string | null
  destination_branch: string | null
  requires_damage_check: boolean
  exception_message: string | null
  destination_summary: {
    total: number
    shelve: number
    holds: number
    transit: number
    exceptions: number
  }
}

export default function FastBookDropProcessPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // State management
  const [activeSession, setActiveSession] = useState<SessionData | null>(null)
  const [isSessionActive, setIsSessionActive] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentBarcode, setCurrentBarcode] = useState("")
  const [lastResult, setLastResult] = useState<FastProcessingResponse | null>(null)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [damageCheckPending, setDamageCheckPending] = useState(false)
  const [sessionStartTime, setSessionStartTime] = useState<Date | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  // Refs
  const audioContextRef = useRef<AudioContext | null>(null)
  const barcodeInputRef = useRef<HTMLInputElement>(null)
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Initialize
  useEffect(() => {
    if (!user) {
      navigate("/login")
      return
    }
  }, [isAuthenticated, user, navigate])

  // Timer for elapsed time
  useEffect(() => {
    if (isSessionActive && sessionStartTime) {
      timerIntervalRef.current = setInterval(() => {
        const now = new Date()
        const elapsed = Math.floor((now.getTime() - sessionStartTime.getTime()) / 1000)
        setElapsedSeconds(elapsed)
      }, 1000)

      return () => {
        if (timerIntervalRef.current) clearInterval(timerIntervalRef.current)
      }
    }
  }, [isSessionActive, sessionStartTime])

  // Load active sessions
  useEffect(() => {
    const loadActiveSessions = async () => {
      if (!token) return

      try {
        const sessions = await listActiveSessions(token)
        if (sessions && sessions.length > 0) {
          const session = sessions[0]
          if (session) {
            setActiveSession({
              id: session.id,
              session_code: session.session_code,
              branch_location: session.branch_location,
              status: session.status,
              total_items: session.total_items,
              successful_checkins: session.successful_checkins,
              holds_trapped: session.holds_trapped,
              transits_created: session.transits_created,
              exceptions_count: session.exceptions_count,
            })
            setIsSessionActive(true)
            setSessionStartTime(new Date())
          }
        }
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      }
    }

    if (isAuthenticated && token && !activeSession) {
      loadActiveSessions()
    }
  }, [isAuthenticated, token, activeSession])

  // Initialize audio context
  useEffect(() => {
    if (!audioContextRef.current && typeof window !== "undefined") {
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const AudioContext = (window as any).AudioContext || (window as any).webkitAudioContext
        audioContextRef.current = new AudioContext()
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      }
    }
  }, [])

  // Play sorting sound
  const playSound = useCallback((soundType: string) => {
    if (!soundEnabled || !audioContextRef.current) return

    const ctx = audioContextRef.current
    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    // Different frequencies for different sorts
    switch (soundType) {
      case "shelve": // Green - low tone
        oscillator.frequency.value = 523.25 // C5
        break
      case "holds": // Yellow - medium tone
        oscillator.frequency.value = 659.25 // E5
        break
      case "transit": // Blue - high tone
        oscillator.frequency.value = 783.99 // G5
        break
      case "exception": // Red - warning tone (lower, repeated)
        oscillator.frequency.value = 349.23 // F4
        break
      default:
        oscillator.frequency.value = 440
    }

    oscillator.type = "sine"
    gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5)

    oscillator.start(ctx.currentTime)
    oscillator.stop(ctx.currentTime + 0.5)
  }, [soundEnabled, audioContextRef])

  // Start new session
  const handleStartSession = async () => {
    try {
      if (!user || !token) {
        toast.error(t('toast.fastBookDropProcess.userNotAuthenticated'))
        return
      }

      const session = await startCheckInSession(token, {
        branch_location: "main",
        workstation_id: "fast-process-1",
      })

      setActiveSession({
        id: session.id,
        session_code: session.session_code,
        branch_location: session.branch_location,
        status: session.status,
        total_items: session.total_items,
        successful_checkins: session.successful_checkins,
        holds_trapped: session.holds_trapped,
        transits_created: session.transits_created,
        exceptions_count: session.exceptions_count,
      })
      setIsSessionActive(true)
      setSessionStartTime(new Date())
      setElapsedSeconds(0)
      toast.success(t('toast.fastBookDropProcess.sessionStarted'))
      setTimeout(() => barcodeInputRef.current?.focus(), 100)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('fastBookDropProcess.failedToStartSession'))
    }
  }

  // End session
  const handleEndSession = async () => {
    if (!activeSession || !token) return

    try {
      await endSession(token, activeSession.id)

      const itemsPerMinute = activeSession.total_items > 0
        ? Math.round((activeSession.total_items / elapsedSeconds) * 60)
        : 0

      toast.success(t('toast.fastBookDropProcess.sessionEndedProcessedTotalitemsItems', { totalitems: activeSession.total_items, itemsPerMinute: itemsPerMinute }))

      setActiveSession(null)
      setIsSessionActive(false)
      setCurrentBarcode("")
      setLastResult(null)
      setElapsedSeconds(0)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('fastBookDropProcess.failedToEndSession'))
    }
  }

  // Process barcode scan
  const handleBarcodeScan = async (barcode: string) => {
    if (!activeSession || !token || !barcode.trim()) return

    setIsProcessing(true)
    try {
      const scanResult = await fastProcessingScan(
        token,
        activeSession.id,
        barcode.trim(),
        false,
        undefined
      )
      const checkInResult = scanResult.result
      const result: FastProcessingResponse = {
        check_in_result_id: checkInResult?.id ?? 0,
        barcode: checkInResult?.barcode ?? barcode.trim(),
        status: checkInResult?.status ?? 'unknown',
        sort_destination: checkInResult?.sort_destination ?? null,
        sort_color: (checkInResult as unknown as Record<string, unknown>)?.sort_color as string ?? 'gray',
        sort_sound: (checkInResult as unknown as Record<string, unknown>)?.sort_sound as string ?? 'default',
        hold_patron_name: checkInResult?.hold_patron_name ?? null,
        destination_branch: checkInResult?.destination_branch ?? null,
        requires_damage_check: scanResult.requires_damage_check ?? false,
        exception_message: (checkInResult as unknown as Record<string, unknown>)?.exception_message as string | null ?? null,
        destination_summary: {
          total: scanResult.destination_summary?.total_items ?? 0,
          shelve: scanResult.destination_summary?.destinations?.['shelve'] ?? 0,
          holds: scanResult.destination_summary?.holds_count ?? 0,
          transit: scanResult.destination_summary?.transit_count ?? 0,
          exceptions: scanResult.destination_summary?.destinations?.['exceptions'] ?? 0,
        },
      }

      setLastResult(result)
      playSound(result.sort_sound)

      if (result.requires_damage_check) {
        setDamageCheckPending(true)
      } else {
        setCurrentBarcode("")
        setTimeout(() => barcodeInputRef.current?.focus(), 100)
      }

      // Update session stats
      if (activeSession) {
        setActiveSession({
          ...activeSession,
          total_items: result.destination_summary.total,
          successful_checkins: result.destination_summary.shelve,
          holds_trapped: result.destination_summary.holds,
          transits_created: result.destination_summary.transit,
          exceptions_count: result.destination_summary.exceptions,
        })
      }
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('fastBookDropProcess.failedToProcessBarcode'))
    } finally {
      setIsProcessing(false)
    }
  }

  // Handle barcode input
  const handleBarcodeInput = (e: React.FormEvent<HTMLInputElement>) => {
    const value = e.currentTarget.value
    setCurrentBarcode(value)

    // Auto-submit on Enter
    if (value.includes("\n") || value.endsWith("\r")) {
      handleBarcodeScan(value.replace(/[\n\r]/g, ""))
      setCurrentBarcode("")
    }
  }

  // Format time MM:SS
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  // Get sort color background
  const getSortColorBg = (color: string): string => {
    switch (color) {
      case "green":
        return "bg-status-success-500"
      case "yellow":
        return "bg-status-warning-500"
      case "blue":
        return "bg-earth-500"
      case "red":
        return "bg-status-danger-500"
      default:
        return "bg-earth-500"
    }
  }

  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-earth-50 dark:bg-earth-900">
        <Loader2 className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-screen bg-earth-50 dark:bg-earth-900">
        <Loader2 className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin" />
      </div>
    )
  }

  return (
    <AdminShell title={t('fastBookDropProcess.fastBookDropProcessing')}>
        <div className="max-w-6xl mx-auto p-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <Zap className="w-8 h-8 text-status-warning-600" />
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('fastBookDropProcess.fastBookDropProcessing2')}</h1>
            </div>
            <button
              onClick={() => navigate("/staff/book-drop")}
              className="flex items-center gap-2 px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:bg-earth-600 dark:hover:bg-earth-600 rounded-lg transition"
            >
              <Home className="w-4 h-4" />
              Back to Management
            </button>
          </div>

          {!isSessionActive ? (
            // No active session
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
              <AlertCircle className="w-16 h-16 text-earth-600 mx-auto mb-4" />
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">No Active Session</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('fastBookDropProcess.startANewFastProcessing')}</p>
              <button
                onClick={handleStartSession}
                className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white font-semibold rounded-lg hover:bg-lsc-rose/90 transition"
              >
                <Play className="w-5 h-5" />
                Start Fast Processing Session
              </button>
            </div>
          ) : (
            <>
              {/* Session Header with Statistics */}
              <div className="grid grid-cols-5 gap-4 mb-8">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                  <div className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Total Scanned</div>
                  <div className="text-4xl font-bold text-lsc-dark dark:text-lsc-cream">{activeSession?.total_items || 0}</div>
                </div>
                <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-lg shadow p-4 border-l-4 border-status-success-500">
                  <div className="text-sm font-semibold text-status-success-700 dark:text-status-success-300">Shelve</div>
                  <div className="text-4xl font-bold text-status-success-600">{activeSession?.successful_checkins || 0}</div>
                </div>
                <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg shadow p-4 border-l-4 border-status-warning-500">
                  <div className="text-sm font-semibold text-status-warning-700 dark:text-status-warning-300">Holds</div>
                  <div className="text-4xl font-bold text-status-warning-600">{activeSession?.holds_trapped || 0}</div>
                </div>
                <div className="bg-earth-50 dark:bg-earth-800/20 rounded-lg shadow p-4 border-l-4 border-lsc-rose/50">
                  <div className="text-sm font-semibold text-lsc-rose dark:text-lsc-rose-light">Transit</div>
                  <div className="text-4xl font-bold text-lsc-rose dark:text-lsc-rose-light">{activeSession?.transits_created || 0}</div>
                </div>
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg shadow p-4 border-l-4 border-status-danger-500">
                  <div className="text-sm font-semibold text-status-danger-700 dark:text-status-danger-300">Exceptions</div>
                  <div className="text-4xl font-bold text-status-danger-600">{activeSession?.exceptions_count || 0}</div>
                </div>
              </div>

              {/* Main scanning interface */}
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden">
                <div className="p-8">
                  {/* Timer and controls */}
                  <div className="flex items-center justify-between mb-8">
                    <div className="text-center">
                      <div className="text-6xl font-mono font-bold text-lsc-dark dark:text-lsc-cream">{formatTime(elapsedSeconds)}</div>
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">Elapsed Time</div>
                    </div>
                    <button
                      onClick={() => setSoundEnabled(!soundEnabled)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
                        soundEnabled
                          ? "bg-lsc-rose text-white hover:bg-lsc-rose/90"
                          : "bg-earth-200 dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-300 dark:hover:bg-earth-500"
                      }`}
                    >
                      <Volume2 className="w-5 h-5" />
                      {soundEnabled ? "Sound On" : "Sound Off"}
                    </button>
                    <button
                      onClick={handleEndSession}
                      className="flex items-center gap-2 px-6 py-2 bg-status-danger-600 text-white font-semibold rounded-lg hover:bg-status-danger-700 transition"
                    >
                      <Square className="w-5 h-5" />
                      End Session
                    </button>
                  </div>

                  {/* Barcode input */}
                  <div className="mb-8">
                    <label className="block text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      Scan Barcode (Keep Scanning, Don't Stop)
                    </label>
                    <input
                      ref={barcodeInputRef}
                      type="text"
                      value={currentBarcode}
                      onChange={handleBarcodeInput}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault()
                          handleBarcodeScan(currentBarcode)
                          setCurrentBarcode("")
                        }
                      }}
                      placeholder={t('placeholder.fastBookDropProcess.readyToScan')}
                      className="w-full px-4 py-3 text-2xl font-mono border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose focus:outline-none"
                      autoFocus
                      disabled={isProcessing}
                    />
                  </div>

                  {/* Last result indicator */}
                  {lastResult && (
                    <div
                      className={`rounded-lg p-8 text-center transition-all ${getSortColorBg(
                        lastResult.sort_color
                      )} text-white shadow-lg`}
                    >
                      <div className="text-6xl font-bold mb-4">{lastResult.sort_color.toUpperCase()}</div>
                      <div className="text-2xl font-semibold mb-2">{lastResult.barcode}</div>
                      <div className="text-lg opacity-90">
                        {lastResult.sort_destination === "hold_shelf" && `📌 HOLD - ${lastResult.hold_patron_name}`}
                        {lastResult.sort_destination === "transit" && `🚚 TRANSIT - ${lastResult.destination_branch}`}
                        {lastResult.sort_destination === "reshelve" && "📚 SHELVE"}
                        {lastResult.sort_destination === "exception" && "⚠️ EXCEPTION"}
                      </div>
                      {lastResult.requires_damage_check && !damageCheckPending && (
                        <div className="mt-4 text-sm">{t('fastBookDropProcess.pleaseVerifyItemCondition')}</div>
                      )}
                    </div>
                  )}

                  {isProcessing && (
                    <div className="flex items-center justify-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Loader2 className="w-6 h-6 motion-safe:animate-spin" />
                      Processing...
                    </div>
                  )}
                </div>
              </div>

              {/* Damage check prompt */}
              {damageCheckPending && lastResult && (
                <ModalBackdrop title="Damage Check Required">
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-8 max-w-sm">
                    <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4">Damage Check Required</h3>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{lastResult.exception_message}</p>
                    <div className="flex gap-4">
                      <button
                        onClick={() => {
                          setDamageCheckPending(false)
                          setCurrentBarcode("")
                          setTimeout(() => barcodeInputRef.current?.focus(), 100)
                        }}
                        className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-semibold rounded-lg hover:bg-earth-300 dark:hover:bg-earth-500 transition"
                      >
                        Skip
                      </button>
                      <button
                        onClick={() => {
                          handleBarcodeScan(lastResult.barcode)
                          setDamageCheckPending(false)
                        }}
                        className="flex-1 px-4 py-2 bg-lsc-rose text-white font-semibold rounded-lg hover:bg-lsc-rose/90 transition"
                      >
                        Verify Damage
                      </button>
                    </div>
                  </div>
                </ModalBackdrop>
              )}
            </>
          )}

      </div>
    </AdminShell>
  )
}
