/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useRef, useCallback } from "react"
import { BookOpen, Plus, Play, Pause, Square, CheckCircle, XCircle, AlertTriangle, ArrowUpDown, ScanLine, Loader2 } from "lucide-react"
import { AdminShell } from "../../components/shells/AdminShell"
import {
  listSessions,
  createSession,
  getSessionProgress,
  completeSession,
  pauseSession,
  resumeSession,
  cancelSession,
  scanItem,
  listSessionScans,
  type ShelfReadingSession,
  type ShelfReadingProgress,
  type ShelfReadingScan,
  type ShelfReadingStatus,
} from "../../api/shelf-reading-api"
import { listBranches, type Branch } from "../../api/branch-api"

// ==================== Sub-components ====================

function StatusBadge({ status }: { status: ShelfReadingStatus }) {
  const styles: Record<ShelfReadingStatus, string> = {
    in_progress: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300",
    paused: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
    completed: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
    cancelled: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  }
  const labels: Record<ShelfReadingStatus, string> = {
    in_progress: "In Progress",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

function ScanResultBadge({ result }: { result: string }) {
  if (result === "in_order") {
    return (
      <span className="inline-flex items-center gap-1 text-status-success-700 dark:text-status-success-400 text-sm">
        <CheckCircle className="w-4 h-4" /> In Order
      </span>
    )
  }
  if (result === "out_of_order") {
    return (
      <span className="inline-flex items-center gap-1 text-status-warning-700 dark:text-status-warning-400 text-sm">
        <ArrowUpDown className="w-4 h-4" /> Out of Order
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-status-danger-700 dark:text-status-danger-400 text-sm">
      <XCircle className="w-4 h-4" /> Wrong Shelf
    </span>
  )
}

function ProgressStats({ progress }: { progress: ShelfReadingProgress }) {
  const accuracy = progress.accuracy_percentage
  const accuracyColor = accuracy >= 90 ? "text-status-success-600 dark:text-status-success-400" : accuracy >= 70 ? "text-status-warning-600 dark:text-status-warning-400" : "text-status-danger-600 dark:text-status-danger-400"

  return (
    <div aria-live="polite" className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <p className="sr-only">
        {`${progress.total_items_scanned} items scanned, ${progress.items_in_order} in order, ${progress.items_out_of_order} out of order, ${accuracy.toFixed(1)}% accuracy.`}
      </p>
      <div className="bg-lsc-white dark:bg-earth-700 rounded-xl p-4 text-center">
        <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{progress.total_items_scanned}</div>
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Scanned</div>
      </div>
      <div className="bg-lsc-white dark:bg-earth-700 rounded-xl p-4 text-center">
        <div className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">{progress.items_in_order}</div>
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">In Order</div>
      </div>
      <div className="bg-lsc-white dark:bg-earth-700 rounded-xl p-4 text-center">
        <div className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{progress.items_out_of_order}</div>
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Out of Order</div>
      </div>
      <div className="bg-lsc-white dark:bg-earth-700 rounded-xl p-4 text-center">
        <div className={`text-2xl font-bold ${accuracyColor}`}>{accuracy.toFixed(1)}%</div>
        <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">Accuracy</div>
      </div>
    </div>
  )
}

// ==================== Main Page ====================

const StaffShelfReadingPage: React.FC = () => {
  // Session list state
  const [sessions, setSessions] = useState<ShelfReadingSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<ShelfReadingStatus | "">("")

  // Active session state
  const [activeSession, setActiveSession] = useState<ShelfReadingSession | null>(null)
  const [progress, setProgress] = useState<ShelfReadingProgress | null>(null)
  const [scans, setScans] = useState<ShelfReadingScan[]>([])
  const [barcode, setBarcode] = useState("")
  const [scanLoading, setScanLoading] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const [scanSuccess, setScanSuccess] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // New session form state
  const [showNewForm, setShowNewForm] = useState(false)
  const [branches, setBranches] = useState<Branch[]>([])
  const [newSession, setNewSession] = useState({
    name: "",
    branch_id: 0,
    location: "",
    call_number_start: "",
    call_number_end: "",
    description: "",
  })
  const [createError, setCreateError] = useState<string | null>(null)

  const [error, setError] = useState<string | null>(null)
  const barcodeRef = useRef<HTMLInputElement>(null)

  // Load sessions
  const loadSessions = useCallback(async () => {
    try {
      setSessionsLoading(true)
      const params: Record<string, unknown> = { per_page: 50 }
      if (statusFilter) params.status = statusFilter
      const data = await listSessions(params as Parameters<typeof listSessions>[0])
      setSessions(data.items)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load sessions")
    } finally {
      setSessionsLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { loadSessions() }, [loadSessions])

  // Load branches for the create form
  useEffect(() => {
    if (showNewForm && branches.length === 0) {
      listBranches().then((b) => setBranches(b)).catch(() => {})
    }
  }, [showNewForm, branches.length])

  // Load active session details
  const openSession = async (session: ShelfReadingSession) => {
    setActiveSession(session)
    setScanError(null)
    setScanSuccess(null)
    setBarcode("")
    try {
      const [prog, scanData] = await Promise.all([
        getSessionProgress(session.id),
        listSessionScans(session.id),
      ])
      setProgress(prog)
      setScans(scanData.items)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load session details")
    }
    setTimeout(() => barcodeRef.current?.focus(), 100)
  }

  // Refresh progress
  const refreshProgress = async (sessionId: number) => {
    try {
      const [prog, scanData] = await Promise.all([
        getSessionProgress(sessionId),
        listSessionScans(sessionId),
      ])
      setProgress(prog)
      setScans(scanData.items)
    } catch { /* swallow */ }
  }

  // Create session
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    if (!newSession.name || !newSession.branch_id || !newSession.location) {
      setCreateError("Name, branch, and location are required")
      return
    }
    try {
      const created = await createSession({
        name: newSession.name,
        branch_id: newSession.branch_id,
        location: newSession.location,
        call_number_start: newSession.call_number_start || undefined,
        call_number_end: newSession.call_number_end || undefined,
        description: newSession.description || undefined,
      })
      setShowNewForm(false)
      setNewSession({ name: "", branch_id: 0, location: "", call_number_start: "", call_number_end: "", description: "" })
      await loadSessions()
      openSession(created)
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create session")
    }
  }

  // Scan barcode
  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!activeSession || !barcode.trim()) return
    setScanLoading(true)
    setScanError(null)
    setScanSuccess(null)
    try {
      const scan = await scanItem(activeSession.id, barcode.trim())
      setBarcode("")
      barcodeRef.current?.focus()
      const resultLabel = scan.result === "in_order" ? "In order" : scan.result === "out_of_order" ? "Out of order" : "Wrong shelf"
      setScanSuccess(`${scan.catalog_title || scan.barcode} - ${resultLabel}`)
      await refreshProgress(activeSession.id)
    } catch (err: unknown) {
      setScanError(err instanceof Error ? err.message : "Scan failed")
      barcodeRef.current?.select()
    } finally {
      setScanLoading(false)
    }
  }

  // Session actions
  const handleSessionAction = async (action: "complete" | "pause" | "resume" | "cancel") => {
    if (!activeSession) return
    setActionLoading(true)
    try {
      const fns = { complete: completeSession, pause: pauseSession, resume: resumeSession, cancel: cancelSession }
      const updated = await fns[action](activeSession.id)
      setActiveSession(updated)
      await refreshProgress(updated.id)
      await loadSessions()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${action} session`)
    } finally {
      setActionLoading(false)
    }
  }

  // Back to list
  const backToList = () => {
    setActiveSession(null)
    setProgress(null)
    setScans([])
    setScanError(null)
    setScanSuccess(null)
  }

  // ==================== Active Session View ====================
  if (activeSession) {
    const isActive = activeSession.status === "in_progress"
    const isPaused = activeSession.status === "paused"
    const isDone = activeSession.status === "completed" || activeSession.status === "cancelled"

    return (
      <AdminShell
        title="Shelf Reading"
        subtitle={activeSession.name}
        icon={<BookOpen className="w-8 h-8 text-lsc-rose" />}
        actions={
          <button
            onClick={backToList}
            className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
          >
            Back to Sessions
          </button>
        }
      >
        {/* Session info bar */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 flex flex-wrap items-center gap-4 border border-lsc-border dark:border-earth-700">
          <StatusBadge status={activeSession.status} />
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {activeSession.branch_name} &middot; {activeSession.location}
          </span>
          {activeSession.call_number_start && (
            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Range: {activeSession.call_number_start}{activeSession.call_number_end ? ` - ${activeSession.call_number_end}` : ""}
            </span>
          )}
          <div className="flex-1" />
          {/* Action buttons */}
          {isActive && (
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => handleSessionAction("pause")} disabled={actionLoading} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300 hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50 transition-colors min-h-[44px]">
                <Pause className="w-4 h-4" /> Pause
              </button>
              <button onClick={() => handleSessionAction("complete")} disabled={actionLoading} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 transition-colors min-h-[44px]">
                <Square className="w-4 h-4" /> Complete
              </button>
              <button onClick={() => handleSessionAction("cancel")} disabled={actionLoading} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 transition-colors min-h-[44px]">
                <XCircle className="w-4 h-4" /> Cancel
              </button>
            </div>
          )}
          {isPaused && (
            <button onClick={() => handleSessionAction("resume")} disabled={actionLoading} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-xl bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300 hover:bg-status-info-200 dark:hover:bg-status-info-900/50 transition-colors min-h-[44px]">
              <Play className="w-4 h-4" /> Resume
            </button>
          )}
        </div>

        {/* Progress stats */}
        {progress && <ProgressStats progress={progress} />}

        {/* Barcode scan input */}
        {isActive && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <form onSubmit={handleScan} className="flex gap-3 items-end">
              <div className="flex-1">
                <label htmlFor="barcode-input" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Scan or enter barcode
                </label>
                <input
                  ref={barcodeRef}
                  id="barcode-input"
                  type="text"
                  value={barcode}
                  onChange={(e) => setBarcode(e.target.value)}
                  placeholder="Scan barcode..."
                  autoFocus
                  autoComplete="off"
                  className="w-full px-4 py-3 text-lg rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose min-h-[44px]"
                />
              </div>
              <button
                type="submit"
                disabled={scanLoading || !barcode.trim()}
                className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors min-h-[44px]"
              >
                {scanLoading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <ScanLine className="w-4 h-4" />}
                Scan
              </button>
            </form>

            <div aria-live="polite">
              {scanSuccess && (
                <div className="mt-3 p-3 rounded-xl bg-status-success-50 dark:bg-status-success-900/20 text-status-success-800 dark:text-status-success-300 text-sm flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 flex-shrink-0" /> {scanSuccess}
                </div>
              )}
            </div>
            <div role="alert">
              {scanError && (
                <div className="mt-3 p-3 rounded-xl bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-300 text-sm flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {scanError}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scan history */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700">
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
              Scan History ({scans.length})
            </h3>
          </div>
          {scans.length === 0 ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/50">
              {isDone ? "No items were scanned in this session." : "No items scanned yet. Start scanning barcodes above."}
            </div>
          ) : (
            <div className="divide-y divide-earth-200 dark:divide-earth-700 max-h-96 overflow-y-auto">
              {scans.map((scan) => (
                <div key={scan.id} className="px-4 py-3 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate">
                      {scan.catalog_title || "Unknown Title"}
                    </div>
                    <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 truncate">
                      {scan.catalog_author && <span>{scan.catalog_author} &middot; </span>}
                      {scan.barcode} &middot; {scan.scanned_call_number || "No call number"}
                    </div>
                  </div>
                  <ScanResultBadge result={scan.result} />
                </div>
              ))}
            </div>
          )}
        </div>
      </AdminShell>
    )
  }

  // ==================== Session List View ====================
  return (
    <AdminShell
      title="Shelf Reading"
      subtitle="Verify items are in correct call number order"
      icon={<BookOpen className="w-8 h-8 text-lsc-rose" />}
      loading={sessionsLoading && sessions.length === 0}
      error={error}
      actions={
        <button
          onClick={() => setShowNewForm(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors min-h-[44px]"
        >
          <Plus className="w-4 h-4" /> New Session
        </button>
      }
    >
      {/* New session form */}
      {showNewForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Start New Session</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="session-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Session Name *</label>
                <input id="session-name" type="text" required value={newSession.name} onChange={(e) => setNewSession((s) => ({ ...s, name: e.target.value }))} placeholder="e.g. Fiction A-F Check" className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream min-h-[44px]" />
              </div>
              <div>
                <label htmlFor="session-branch" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Branch *</label>
                <select id="session-branch" required value={newSession.branch_id} onChange={(e) => setNewSession((s) => ({ ...s, branch_id: Number(e.target.value) }))} className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream min-h-[44px]">
                  <option value={0}>Select branch...</option>
                  {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="session-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location / Area *</label>
                <input id="session-location" type="text" required value={newSession.location} onChange={(e) => setNewSession((s) => ({ ...s, location: e.target.value }))} placeholder="e.g. Adult Fiction, Shelf 3" className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream min-h-[44px]" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="cn-start" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Call # Start</label>
                  <input id="cn-start" type="text" value={newSession.call_number_start} onChange={(e) => setNewSession((s) => ({ ...s, call_number_start: e.target.value }))} placeholder="000" className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream min-h-[44px]" />
                </div>
                <div>
                  <label htmlFor="cn-end" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Call # End</label>
                  <input id="cn-end" type="text" value={newSession.call_number_end} onChange={(e) => setNewSession((s) => ({ ...s, call_number_end: e.target.value }))} placeholder="099" className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream min-h-[44px]" />
                </div>
              </div>
            </div>
            <div>
              <label htmlFor="session-desc" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</label>
              <textarea id="session-desc" rows={2} value={newSession.description} onChange={(e) => setNewSession((s) => ({ ...s, description: e.target.value }))} placeholder="Optional notes..." className="w-full px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
            </div>
            <div role="alert">
              {createError && (
                <div className="p-3 rounded-xl bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-800 dark:text-status-danger-300 text-sm">{createError}</div>
              )}
            </div>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setShowNewForm(false)} className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors min-h-[44px]">
                Cancel
              </button>
              <button type="submit" className="px-4 py-2 text-sm font-medium rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors min-h-[44px]">
                Start Session
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-3">
        <label htmlFor="status-filter" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Filter:</label>
        <select id="status-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as ShelfReadingStatus | "")} className="px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream min-h-[44px]">
          <option value="">All Sessions</option>
          <option value="in_progress">In Progress</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Session list */}
      {sessions.length === 0 && !sessionsLoading ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-12 text-center border border-lsc-border dark:border-earth-700">
          <BookOpen className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/30 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/60">
            {statusFilter ? "No sessions match this filter." : "No shelf reading sessions yet. Start one to begin verifying shelf order."}
          </p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="divide-y divide-earth-200 dark:divide-earth-700">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => openSession(session)}
                className="w-full text-left px-4 py-4 hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors min-h-[44px]"
              >
                <div className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{session.name}</span>
                      <StatusBadge status={session.status} />
                    </div>
                    <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                      {session.branch_name} &middot; {session.location}
                      {session.call_number_start && <span> &middot; {session.call_number_start}{session.call_number_end ? `-${session.call_number_end}` : ""}</span>}
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <div className="text-lsc-dark dark:text-lsc-cream">{session.total_items_scanned} scanned</div>
                    <div className="text-lsc-dark/70 dark:text-lsc-cream/60">{session.accuracy_percentage.toFixed(0)}% accuracy</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </AdminShell>
  )
}

export default StaffShelfReadingPage
