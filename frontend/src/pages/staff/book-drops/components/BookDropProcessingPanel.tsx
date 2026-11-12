/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Loader2, Activity, Square, Package, Play, History } from "lucide-react"
import { CheckInSession } from "@/api/book-drop-api"
import { useTranslation, getCurrentLocale } from '@/i18n'

interface BookDropProcessingPanelProps {
  currentSession: CheckInSession | null
  activeSessions: CheckInSession[]
  barcodeInput: string
  isProcessing: boolean
  onBarcodeChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
  onEndSession: () => void
  onSelectSession: () => void
  onStartSession: () => void
}

interface SessionInfoProps {
  session: CheckInSession
  onEndSession: () => void
  barcodeInput: string
  isProcessing: boolean
  onBarcodeChange: (value: string) => void
  onSubmit: (e: React.FormEvent) => void
}

const SessionInfo: React.FC<SessionInfoProps> = ({
  session,
  onEndSession,
  barcodeInput,
  isProcessing,
  onBarcodeChange,
  onSubmit,
}) => {
  const { t } = useTranslation()
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A"
    return new Date(dateStr).toLocaleString(getCurrentLocale(), {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-status-success-100 dark:bg-status-success-900/30">
            <Activity className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
          </div>
          <div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Session: {session.session_code}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {session.branch_location}
              {session.use_backdating && session.backdate_to && (
                <span className="ml-2 text-status-warning-600 dark:text-status-warning-400">
                  | Backdating to {formatDate(session.backdate_to)}
                </span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              {session.total_items}
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Items Processed</p>
          </div>
          <button
            onClick={onEndSession}
            className="flex items-center gap-2 px-4 py-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/30 rounded-xl transition-colors"
          >
            <Square className="w-4 h-4" />
            End Session
          </button>
        </div>
      </div>

      {/* Session Stats */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-status-success-600 dark:text-status-success-400">
            {session.successful_checkins}
          </p>
          <p className="text-xs text-status-success-700 dark:text-status-success-300">Successful</p>
        </div>
        <div className="bg-earth-50 dark:bg-earth-800/20 rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-lsc-rose dark:text-lsc-rose-light">
            {session.holds_trapped}
          </p>
          <p className="text-xs text-lsc-rose dark:text-lsc-rose-light">Holds</p>
        </div>
        <div className="bg-category-50 dark:bg-category-900/20 rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-category-600 dark:text-category-400">
            {session.transits_created}
          </p>
          <p className="text-xs text-category-700 dark:text-category-300">Transits</p>
        </div>
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg p-3 text-center">
          <p className="text-xl font-bold text-status-danger-600 dark:text-status-danger-400">
            {session.exceptions_count}
          </p>
          <p className="text-xs text-status-danger-700 dark:text-status-danger-300">Exceptions</p>
        </div>
      </div>

      {/* Barcode Input */}
      <form onSubmit={onSubmit} className="flex gap-3">
        <input
          type="text"
          value={barcodeInput}
          onChange={(e) => onBarcodeChange(e.target.value)}
          placeholder={t('bookDropProcessingPanel.scanOrEnterBarcode')}
          autoFocus
          className="flex-1 px-4 py-3 text-lg border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
        <button
          type="submit"
          disabled={isProcessing || !barcodeInput.trim()}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8m0 8l-6-4m6 4l6-4" />
            </svg>
          )}
          Check In
        </button>
      </form>
    </div>
  )
}

interface NoSessionProps {
  activeSessions: CheckInSession[]
  onStartSession: () => void
  onSelectSession: () => void
}

const NoSession: React.FC<NoSessionProps> = ({
  activeSessions,
  onStartSession,
  onSelectSession,
}) => {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-8 text-center">
      <Package className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        No Active Session
      </h3>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        Start a new session or select an active session to process returns
      </p>
      <div className="flex justify-center gap-3">
        <button
          onClick={onStartSession}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
        >
          <Play className="w-4 h-4" />
          Start New Session
        </button>
        {activeSessions.length > 0 && (
          <button
            onClick={onSelectSession}
            className="inline-flex items-center gap-2 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 transition-colors"
          >
            <History className="w-4 h-4" />
            View Active Sessions ({activeSessions.length})
          </button>
        )}
      </div>
    </div>
  )
}

export const BookDropProcessingPanel: React.FC<BookDropProcessingPanelProps> = ({
  currentSession,
  activeSessions,
  barcodeInput,
  isProcessing,
  onBarcodeChange,
  onSubmit,
  onEndSession,
  onSelectSession,
  onStartSession,
}) => {
  return currentSession ? (
    <SessionInfo
      session={currentSession}
      onEndSession={onEndSession}
      barcodeInput={barcodeInput}
      isProcessing={isProcessing}
      onBarcodeChange={onBarcodeChange}
      onSubmit={onSubmit}
    />
  ) : (
    <NoSession
      activeSessions={activeSessions}
      onStartSession={onStartSession}
      onSelectSession={onSelectSession}
    />
  )
}
