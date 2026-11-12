/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { fetchApi } from '@/api/fetchApi';
import { Loader2, Wrench, FlaskConical, FlaskConicalOff } from "lucide-react"
import toast from "react-hot-toast"
import * as rfidSimulatorApi from "../api/rfid-simulator-api"
import { useTranslation} from '@/i18n'
import { TABS } from "../components/rfid/rfid-simulator-data"
import { OverviewTab } from "../components/rfid/OverviewTab"
import { ReadersTab } from "../components/rfid/ReadersTab"
import { TagsTab } from "../components/rfid/TagsTab"
import { SecurityTab } from "../components/rfid/SecurityTab"
import { AutoScanTab } from "../components/rfid/AutoScanTab"
import { ResultsTab } from "../components/rfid/ResultsTab"
import { CreateReaderModal } from "../components/rfid/CreateReaderModal"
import type { RFIDReader, RFIDSession } from "../components/rfid/types"

async function apiFetch<T>(_token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  // fetchApi attaches the Bearer token from tokenStore, so the token param
  // here is kept only to preserve the existing call-site signature.
  return fetchApi(`/rfid${endpoint}`, options);
}

export default function RFIDSimulatorPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("overview")
  const [isLoading, setIsLoading] = useState(false)
  // true when the simulator endpoints return 403 (production environments)
  const [simulatorBlocked, setSimulatorBlocked] = useState<boolean | null>(null)

  const [readers, setReaders] = useState<RFIDReader[]>([])
  const [sessions, setSessions] = useState<RFIDSession[]>([])

  const [showCreateReaderForm, setShowCreateReaderForm] = useState(false)
  const [createReaderForm, setCreateReaderForm] = useState({
    name: "Test Reader",
    reader_type: "circulation_desk" as rfidSimulatorApi.RFIDReaderType,
    location: "Test Location"
  })

  const [selectedSession, setSelectedSession] = useState<number>(0)
  const [tagSimForm, setTagSimForm] = useState({
    tag_id: "",
    signal_strength: -30,
    found_at_location: ""
  })

  const [batchForm, setBatchForm] = useState({
    count: 5,
    include_registered: true,
    include_unregistered: true,
    delay_ms: 200
  })

  const [selectedReader, setSelectedReader] = useState<number>(0)
  const [securityForm, setSecurityForm] = useState({
    tag_id: "",
    use_registered_tag: true
  })

  const [statusForm, setStatusForm] = useState({
    reader_id: 0,
    status: "online" as rfidSimulatorApi.RFIDReaderStatus,
    error_message: ""
  })

  const [autoScanForm, setAutoScanForm] = useState({
    interval_ms: 1000,
    include_registered: true,
    include_unregistered: false
  })
  const [autoScanStatus, setAutoScanStatus] = useState<rfidSimulatorApi.AutoScanStatus | null>(null)

  const [testTagsForm, setTestTagsForm] = useState({
    reader_id: 0,
    count: 10
  })

  const [scanResults, setScanResults] = useState<rfidSimulatorApi.TagReadResult[]>([])
  const [securityAlerts, setSecurityAlerts] = useState<rfidSimulatorApi.SecurityAlertResult[]>([])
  const [statusChanges, setStatusChanges] = useState<rfidSimulatorApi.ReaderStatusResult[]>([])
  const [createdTags, setCreatedTags] = useState<rfidSimulatorApi.TestTag[]>([])

  useEffect(() => {
    if (!authLoading && (!user || !['admin', 'super_admin'].includes(user.role))) {
      toast.error(t('rFIDSimulator.adminAccessRequiredForRfid'))
      navigate("/staff/rfid")
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authLoading, isAuthenticated, user, navigate])

  const loadData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const [readersData, sessionsData] = await Promise.all([
        apiFetch<{ items: RFIDReader[] }>(token, "/readers"),
        apiFetch<{ items: RFIDSession[] }>(token, "/sessions?is_active=true")
      ])
      setReaders(readersData.items)
      setSessions(sessionsData.items)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToLoadData'))
    } finally {
      setIsLoading(false)
    }
  }, [token, t])

  const loadAutoScanStatus = useCallback(async () => {
    if (!token) return
    try {
      const status = await rfidSimulatorApi.getAutoScanStatus(token)
      setAutoScanStatus(status)
      setSimulatorBlocked(false)
    } catch (_err) {
      // A 403 means the simulator endpoints are blocked in this environment (production)
      const is403 = typeof _err === 'object' && _err !== null && (_err as { status?: number }).status === 403
      setSimulatorBlocked(is403)
    }
  }, [token])

  useEffect(() => {
    if (token && isAuthenticated && user && ['admin', 'super_admin'].includes(user.role)) {
      loadData()
      loadAutoScanStatus()
    }
  }, [token, isAuthenticated, user, loadData, loadAutoScanStatus])

  const handleCreateReader = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.createSimulatedReader(token, createReaderForm)
      toast.success(t('toast.rFIDSimulator.createdReaderNameSerialnumber', { name: result.name, serialnumber: result.serial_number }))
      setShowCreateReaderForm(false)
      setCreateReaderForm({ name: "Test Reader", reader_type: "circulation_desk", location: "Test Location" })
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToCreateReader'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSimulateScan = async () => {
    if (!token || !selectedSession) {
      toast.error(t('rFIDSimulator.pleaseSelectAnActiveSession'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.simulateTagRead(token, {
        session_id: selectedSession,
        ...(tagSimForm.tag_id ? { tag_id: tagSimForm.tag_id } : {}),
        signal_strength: tagSimForm.signal_strength,
        ...(tagSimForm.found_at_location ? { found_at_location: tagSimForm.found_at_location } : {}),})
      setScanResults(prev => [result, ...prev].slice(0, 50))
      toast.success(t('toast.rFIDSimulator.tagScannedTagid', { tagid: result.item_title || result.tag_id }))
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToSimulateScan'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSimulateBatchScan = async () => {
    if (!token || !selectedSession) {
      toast.error(t('rFIDSimulator.pleaseSelectAnActiveSession2'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.simulateBatchRead(token, {
        session_id: selectedSession,
        ...batchForm
      })
      setScanResults(prev => [...result.scans, ...prev].slice(0, 100))
      toast.success(result.message)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToSimulateBatchScan'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSimulateSecurityAlert = async () => {
    if (!token || !selectedReader) {
      toast.error(t('rFIDSimulator.pleaseSelectAReader'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.simulateSecurityAlert(token, {
        reader_id: selectedReader,
        ...(securityForm.tag_id ? { tag_id: securityForm.tag_id } : {}),
        use_registered_tag: securityForm.use_registered_tag
      })
      setSecurityAlerts(prev => [result, ...prev].slice(0, 50))
      toast.success(t('toast.rFIDSimulator.securityAlertTriggeredAlerttype', { alerttype: result.alert_type }))
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToSimulateSecurityAlert'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleSimulateStatusChange = async () => {
    if (!token || !statusForm.reader_id) {
      toast.error(t('rFIDSimulator.pleaseSelectAReader2'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.simulateReaderStatus(token, {
        reader_id: statusForm.reader_id,
        status: statusForm.status,
        ...(statusForm.error_message ? { error_message: statusForm.error_message } : {}),})
      setStatusChanges(prev => [result, ...prev].slice(0, 50))
      toast.success(t('toast.rFIDSimulator.readerNamePreviousstatusNewstatus', { name: result.name, previousstatus: result.previous_status, newstatus: result.new_status }))
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToSimulateStatusChange'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleStartAutoScan = async () => {
    if (!token || !selectedSession) {
      toast.error(t('rFIDSimulator.pleaseSelectAnActiveSession3'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.startAutoScan(token, {
        session_id: selectedSession,
        ...autoScanForm
      })
      toast.success(result.message)
      loadAutoScanStatus()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToStartAutoscan'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopAutoScan = async (sessionId: number) => {
    if (!token) return
    try {
      await rfidSimulatorApi.stopAutoScan(token, sessionId)
      toast.success(t('toast.rFIDSimulator.autoscanStoppedForSessionSessionid', { sessionId: sessionId }))
      loadAutoScanStatus()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToStopAutoscan'))
    }
  }

  const handleStopAllAutoScans = async () => {
    if (!token) return
    try {
      await rfidSimulatorApi.stopAllAutoScans(token)
      toast.success(t('toast.rFIDSimulator.allAutoscansStopped'))
      loadAutoScanStatus()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToStopAutoscans'))
    }
  }

  const handleCreateTestTags = async () => {
    if (!token || !testTagsForm.reader_id) {
      toast.error(t('rFIDSimulator.pleaseSelectAReader3'))
      return
    }
    setIsLoading(true)
    try {
      const result = await rfidSimulatorApi.createTestTags(token, testTagsForm)
      setCreatedTags(prev => [...result.tags, ...prev].slice(0, 100))
      toast.success(result.message)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.rFIDSimulator.failedToCreateTestTags'))
    } finally {
      setIsLoading(false)
    }
  }

  if (authLoading || simulatorBlocked === null) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!user || !['admin', 'super_admin'].includes(user.role)) return <></>

  if (simulatorBlocked) {
    return (
      <AdminShell title="RFID Simulator">
        <div className="min-h-[60vh] flex items-center justify-center px-4 py-12">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-earth-100 dark:bg-earth-800">
              <FlaskConicalOff className="h-7 w-7 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            </div>
            <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
              RFID simulator is not available here
            </h1>
            <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70">
              The RFID simulator only runs in development environments. It is
              turned off in production to keep test data from affecting your
              live catalog. To use it, run the app locally or in a dev
              environment.
            </p>
          </div>
        </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="RFID Simulator">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
                <FlaskConical className="w-7 h-7 text-lsc-rose" />
                RFID Simulator
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('rFIDSimulator.testRfidFunctionalityWithoutPhysical')}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 text-sm font-medium rounded-full flex items-center gap-1">
                <Wrench className="w-4 h-4" />
                Dev/Test Mode
              </span>
            </div>
          </div>

          <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700 overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={"flex items-center gap-2 px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap " +
                  (activeTab === tab.id ? "border-earth-600 text-lsc-rose" : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70")}
              >
                <tab.icon className="w-4 h-4" />{tab.label}
              </button>
            ))}
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
            {isLoading && activeTab !== "results" ? (
              <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
            ) : activeTab === "overview" ? (
              <OverviewTab
                readers={readers}
                sessions={sessions}
                scanResults={scanResults}
                securityAlerts={securityAlerts}
                onCreateReader={() => { setShowCreateReaderForm(true); setActiveTab("readers") }}
                onGoToTags={() => setActiveTab("tags")}
                onGoToSecurity={() => setActiveTab("security")}
              />
            ) : activeTab === "readers" ? (
              <ReadersTab
                readers={readers}
                statusForm={statusForm}
                onSetStatusForm={setStatusForm}
                onShowCreateReader={() => setShowCreateReaderForm(true)}
                onSimulateStatusChange={handleSimulateStatusChange}
              />
            ) : activeTab === "tags" ? (
              <TagsTab
                readers={readers}
                sessions={sessions}
                selectedSession={selectedSession}
                onSelectSession={setSelectedSession}
                tagSimForm={tagSimForm}
                onSetTagSimForm={setTagSimForm}
                batchForm={batchForm}
                onSetBatchForm={setBatchForm}
                testTagsForm={testTagsForm}
                onSetTestTagsForm={setTestTagsForm}
                onSimulateScan={handleSimulateScan}
                onSimulateBatchScan={handleSimulateBatchScan}
                onCreateTestTags={handleCreateTestTags}
              />
            ) : activeTab === "security" ? (
              <SecurityTab
                readers={readers}
                selectedReader={selectedReader}
                onSelectReader={setSelectedReader}
                securityForm={securityForm}
                onSetSecurityForm={setSecurityForm}
                securityAlerts={securityAlerts}
                onSimulateSecurityAlert={handleSimulateSecurityAlert}
              />
            ) : activeTab === "autoscan" ? (
              <AutoScanTab
                sessions={sessions}
                selectedSession={selectedSession}
                onSelectSession={setSelectedSession}
                autoScanForm={autoScanForm}
                onSetAutoScanForm={setAutoScanForm}
                autoScanStatus={autoScanStatus}
                onStartAutoScan={handleStartAutoScan}
                onStopAutoScan={handleStopAutoScan}
                onStopAllAutoScans={handleStopAllAutoScans}
                onLoadAutoScanStatus={loadAutoScanStatus}
              />
            ) : activeTab === "results" ? (
              <ResultsTab
                scanResults={scanResults}
                statusChanges={statusChanges}
                createdTags={createdTags}
                onClearScanResults={() => setScanResults([])}
                onClearStatusChanges={() => setStatusChanges([])}
                onClearCreatedTags={() => setCreatedTags([])}
              />
            ) : null}

      {showCreateReaderForm && (
        <CreateReaderModal
          form={createReaderForm}
          onSetForm={setCreateReaderForm}
          onClose={() => setShowCreateReaderForm(false)}
          onSubmit={handleCreateReader}
        />
      )}
      </div>
    </AdminShell>
  )
}
