/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { API_BASE as API_ROOT } from '@/api/types';
import { fetchApi } from '@/api/fetchApi';
import {
  Loader2, Radio, Tag, ShoppingCart, RotateCcw, Shield,
  AlertTriangle, RefreshCcw
} from "lucide-react"
import toast from "react-hot-toast"
import { useReconnectingWebSocket, type WebSocketMessage, type ConnectionState } from "../hooks/useReconnectingWebSocket"
import { useTranslation} from '@/i18n'
import { DashboardTab } from "../components/rfid/DashboardTab"
import { BatchOperationTab } from "../components/rfid/BatchOperationTab"
import { StaffTagsTab } from "../components/rfid/StaffTagsTab"
import { StaffSecurityTab } from "../components/rfid/StaffSecurityTab"
import { StaffReadersTab } from "../components/rfid/StaffReadersTab"
import { AddReaderModal } from "../components/rfid/AddReaderModal"
import { ProgramTagModal } from "../components/rfid/ProgramTagModal"
import { ResolveAlertModal } from "../components/rfid/ResolveAlertModal"
import { CONNECTION_STATUS_CONFIG } from "../components/rfid/staff-rfid-data"
import type {
  StaffRFIDReader,
  RFIDTag,
  SecurityAlert,
  DashboardStats,
  BatchResult,
  RFIDWebSocketEvent,
} from "../components/rfid/staff-rfid-types"

const API_BASE = `${API_ROOT}/rfid`

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: Radio },
  { id: "checkout", label: "Batch Checkout", icon: ShoppingCart },
  { id: "checkin", label: "Batch Checkin", icon: RotateCcw },
  { id: "tags", label: "Tags", icon: Tag },
  { id: "security", label: "Security", icon: Shield },
  { id: "readers", label: "Readers", icon: Radio },
]

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const host = window.location.host
  return `${protocol}//${host}${API_BASE}/ws`
}

async function apiFetch<T>(_token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  try {
    return (await fetchApi(`/rfid${endpoint}`, options)) as T
  } catch (err: unknown) {
    const e = err as { message?: string }
    throw new Error(e?.message || "Request failed")
  }
}

export default function StaffRFIDPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("dashboard")
  const [isLoading, setIsLoading] = useState(false)

  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null)
  const [readers, setReaders] = useState<StaffRFIDReader[]>([])
  const [showReaderForm, setShowReaderForm] = useState(false)
  const [readerForm, setReaderForm] = useState({
    name: "", serial_number: "", location: "", reader_type: "circulation_desk",
    protocol: "sip2", ip_address: "", port: 0
  })
  const [tags, setTags] = useState<RFIDTag[]>([])
  const [showProgramForm, setShowProgramForm] = useState(false)
  const [programForm, setProgramForm] = useState({ item_barcode: "", reader_id: 0 })
  const [selectedReader, setSelectedReader] = useState<number>(0)
  const [patronId, setPatronId] = useState<string>("")
  const [tagInput, setTagInput] = useState("")
  const [scannedTags, setScannedTags] = useState<string[]>([])
  const [checkoutResults, setCheckoutResults] = useState<BatchResult[]>([])
  const [checkinResults, setCheckinResults] = useState<BatchResult[]>([])
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [showResolveModal, setShowResolveModal] = useState<number | null>(null)
  const [resolveNotes, setResolveNotes] = useState("")

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const loadDashboard = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await apiFetch<DashboardStats>(token, "/dashboard")
      setDashboardStats(data)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.acquisition.failedToLoadDashboard'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const loadReaders = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await apiFetch<{ items: StaffRFIDReader[] }>(token, "/readers")
      setReaders(data.items)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const loadTags = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await apiFetch<{ items: RFIDTag[] }>(token, "/tags")
      setTags(data.items)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const loadAlerts = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await apiFetch<{ items: SecurityAlert[] }>(token, "/security/alerts?is_resolved=false")
      setAlerts(data.items)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    const event = message as unknown as RFIDWebSocketEvent

    switch (event.event_type) {
      case "scan":
        if (activeTab === "dashboard") loadDashboard()
        toast.success(`Tag scanned: ${event.item_title || event.tag_id}`, { duration: 4000 })
        break
      case "security_alert":
        toast.error(`Security Alert: ${event.alert_type.replace(/_/g, " ")} at ${event.reader_location || "Unknown"}`, { duration: 5000 })
        if (activeTab === "security") loadAlerts()
        if (activeTab === "dashboard") loadDashboard()
        break
      case "session_status":
        if (activeTab === "dashboard") loadDashboard()
        break
      case "reader_status":
        if (event.status === "offline") toast.error(`Reader offline: ${event.reader_name}`, { duration: 5000 })
        else if (event.status === "online") toast.success(`Reader online: ${event.reader_name}`, { duration: 5000 })
        if (activeTab === "readers") loadReaders()
        if (activeTab === "dashboard") loadDashboard()
        break
      case "batch_progress":
        break
      default:
        break
    }
  }, [activeTab, loadDashboard, loadAlerts, loadReaders])

  const {
    connectionState,
    reconnectAttempts,
    reconnect,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    isConnected: _isConnected,
    lastError: wsError,
  } = useReconnectingWebSocket({
    url: getWebSocketUrl(),
    enabled: isAuthenticated && user?.role !== "patron",
    subscriptions: ["all"],
    onMessage: handleWebSocketMessage,
    onStateChange: () => {},
    initialReconnectDelay: 1000,
    maxReconnectDelay: 30000,
    pingInterval: 30000,
    pongTimeout: 5000,
  })

  useEffect(() => {
    if (token && isAuthenticated && user?.role !== "patron") {
      if (activeTab === "dashboard") loadDashboard()
      else if (activeTab === "readers") loadReaders()
      else if (activeTab === "tags") loadTags()
      else if (activeTab === "security") loadAlerts()
      else if (activeTab === "checkout" || activeTab === "checkin") loadReaders()
    }
  }, [token, isAuthenticated, user, activeTab, loadDashboard, loadReaders, loadTags, loadAlerts])

  const handleCreateReader = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      await apiFetch(token, "/readers", { method: "POST", body: JSON.stringify(readerForm) })
      toast.success(t('toast.staffRFID.readerRegistered'))
      setShowReaderForm(false)
      setReaderForm({ name: "", serial_number: "", location: "", reader_type: "circulation_desk", protocol: "sip2", ip_address: "", port: 0 })
      loadReaders()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleProgramTag = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      const result = await apiFetch<{ success: boolean; message: string; tag_id?: string }>(
        token, "/tags/program",
        { method: "POST", body: JSON.stringify({ ...programForm, include_item_data: true }) }
      )
      if (result.success) {
        toast.success(result.message)
        setShowProgramForm(false)
        setProgramForm({ item_barcode: "", reader_id: 0 })
        loadTags()
      } else {
        toast.error(result.message)
      }
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleAddTag = () => {
    if (!tagInput.trim()) return
    const newTag = tagInput.trim().toUpperCase()
    if (!scannedTags.includes(newTag)) setScannedTags([...scannedTags, newTag])
    setTagInput("")
  }

  const handleBatchCheckout = async () => {
    if (!token || !selectedReader || !patronId || scannedTags.length === 0) {
      toast.error(t('staffRFID.pleaseSelectAReaderEnter'))
      return
    }
    setIsLoading(true)
    try {
      const result = await apiFetch<{ results: BatchResult[] }>(token, "/batch-checkout", {
        method: "POST",
        body: JSON.stringify({ reader_id: selectedReader, patron_id: parseInt(patronId), tag_ids: scannedTags })
      })
      setCheckoutResults(result.results)
      toast.success(t('toast.staffRFID.checkoutCompleteLengthlengthSuccessful', { length: result.results.length }))
      setScannedTags([])
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.checkoutFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleBatchCheckin = async () => {
    if (!token || !selectedReader || scannedTags.length === 0) {
      toast.error(t('staffRFID.pleaseSelectAReaderAnd'))
      return
    }
    setIsLoading(true)
    try {
      const result = await apiFetch<{ results: BatchResult[] }>(token, "/batch-checkin", {
        method: "POST",
        body: JSON.stringify({ reader_id: selectedReader, tag_ids: scannedTags })
      })
      setCheckinResults(result.results)
      toast.success(t('toast.staffRFID.checkinCompleteLengthlengthSuccessful', { length: result.results.length }))
      setScannedTags([])
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.staffRFID.checkinFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleResolveAlert = async () => {
    if (!token || !showResolveModal || !resolveNotes.trim()) return
    try {
      await apiFetch(token, `/security/alerts/${showResolveModal}/resolve`, {
        method: "POST",
        body: JSON.stringify({ resolution_notes: resolveNotes })
      })
      toast.success(t('toast.adminLinkHealth.alertResolved'))
      setShowResolveModal(null)
      setResolveNotes("")
      loadAlerts()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const toggleTagSecurity = async (tagId: string, currentBit: boolean) => {
    if (!token) return
    try {
      await apiFetch(token, `/tags/${tagId}/security?security_bit=${!currentBit}`, { method: "POST" })
      toast.success(currentBit ? t('toast.staffRFID.tagDesensitized') : t('toast.staffRFID.tagSecured'))
      loadTags()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  if (authLoading) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!user || user.role === "patron") return <></>

  const wsConfig = CONNECTION_STATUS_CONFIG[connectionState as ConnectionState]
  const StatusIcon = wsConfig.icon

  return (
    <AdminShell title="RFID Operations">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
            <Radio className="w-7 h-7 text-lsc-rose" />
            RFID Operations
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffRFID.manageRfidReadersTagsAnd')}</p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${wsConfig.bgColor}`}>
            <StatusIcon
              className={`w-4 h-4 ${wsConfig.color} ${connectionState === "reconnecting" || connectionState === "connecting" ? "motion-safe:animate-spin" : ""}`}
            />
            <span className={`text-sm font-medium ${wsConfig.color}`}>
              {wsConfig.label}
              {connectionState === "reconnecting" && reconnectAttempts > 0 && (
                <span className="ml-1">({reconnectAttempts})</span>
              )}
            </span>
          </div>

          {(connectionState === "disconnected" || connectionState === "reconnecting") && (
            <button
              onClick={reconnect}
              className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-full text-sm font-medium transition-colors"
              title={t('staffRFID.reconnectToRealTimeUpdates')}
            >
              <RefreshCcw className="w-4 h-4" />
              Reconnect
            </button>
          )}

          {wsError && connectionState === "disconnected" && (
            <div className="flex items-center gap-1 text-xs text-status-danger-600" title={wsError}>
              <AlertTriangle className="w-3 h-3" />
              <span className="hidden sm:inline max-w-32 truncate">{wsError}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setCheckoutResults([]); setCheckinResults([]); }}
            className={"flex items-center gap-2 px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap " +
              (activeTab === tab.id ? "border-earth-600 text-lsc-rose" : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70")}
          >
            <tab.icon className="w-4 h-4" />{tab.label}
          </button>
        ))}
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
        {isLoading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
        ) : activeTab === "dashboard" && dashboardStats ? (
          <DashboardTab dashboardStats={dashboardStats} />
        ) : (activeTab === "checkout" || activeTab === "checkin") ? (
          <BatchOperationTab
            activeTab={activeTab as "checkout" | "checkin"}
            readers={readers}
            selectedReader={selectedReader}
            setSelectedReader={setSelectedReader}
            patronId={patronId}
            setPatronId={setPatronId}
            tagInput={tagInput}
            setTagInput={setTagInput}
            scannedTags={scannedTags}
            onAddTag={handleAddTag}
            onRemoveTag={(tag) => setScannedTags(scannedTags.filter(t => t !== tag))}
            onClearAll={() => { setScannedTags([]); setCheckoutResults([]); setCheckinResults([]); }}
            onProcess={activeTab === "checkout" ? handleBatchCheckout : handleBatchCheckin}
            results={activeTab === "checkout" ? checkoutResults : checkinResults}
          />
        ) : activeTab === "tags" ? (
          <StaffTagsTab
            tags={tags}
            onProgramNew={() => setShowProgramForm(true)}
            onToggleSecurity={toggleTagSecurity}
          />
        ) : activeTab === "security" ? (
          <StaffSecurityTab
            alerts={alerts}
            onRefresh={loadAlerts}
            onResolve={(alertId) => setShowResolveModal(alertId)}
          />
        ) : activeTab === "readers" ? (
          <StaffReadersTab
            readers={readers}
            onAddReader={() => setShowReaderForm(true)}
          />
        ) : null}
      </div>

      {showReaderForm && (
        <AddReaderModal
          form={readerForm}
          onChange={setReaderForm}
          onSubmit={handleCreateReader}
          onClose={() => setShowReaderForm(false)}
        />
      )}

      {showProgramForm && (
        <ProgramTagModal
          form={programForm}
          onChange={setProgramForm}
          readers={readers}
          onSubmit={handleProgramTag}
          onClose={() => setShowProgramForm(false)}
        />
      )}

      {showResolveModal && (
        <ResolveAlertModal
          resolveNotes={resolveNotes}
          setResolveNotes={setResolveNotes}
          onResolve={handleResolveAlert}
          onClose={() => { setShowResolveModal(null); setResolveNotes(""); }}
        />
      )}
    </AdminShell>
  )
}
