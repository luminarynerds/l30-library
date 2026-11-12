/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { Loader2, Package, Clipboard, Search, Plus, Trash2, X, Check, QrCode, Clock, Download } from "lucide-react"
import toast from "react-hot-toast"
import { getItemCopyLifecycle, LifecycleTimeline as LifecycleTimelineType } from "../api/api"
import { LifecycleTimeline } from "../components/LifecycleTimeline"
import { fetchApi } from '@/lib/api-client'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ItemCopy { id: number; barcode: string; copy_number: number; condition: string; catalog_title: string | null; catalog_author: string | null; location: string | null; replacement_cost: number | null; is_available: boolean }
interface Audit { id: number; name: string; location_filter: string | null; started_at: string; completed_at: string | null; items_expected: number; items_found: number; items_missing: number; items_misplaced: number }

const TABS = [
  { id: "copies", label: "Item Copies", icon: Package },
  { id: "audits", label: "Audits", icon: Clipboard },
]

const CONDITIONS = ["new", "good", "fair", "poor", "damaged", "withdrawn"]
const CONDITION_COLORS: Record<string, string> = {
  new: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  good: "bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light",
  fair: "bg-lsc-cream dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light",
  poor: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
  damaged: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
  withdrawn: "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70",
}

const INVENTORY_CSV_COLUMNS = ["barcode", "catalog_title", "catalog_author", "copy_number", "condition", "location", "replacement_cost", "is_available"] as const

function escapeCsvField(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return '"' + value.replace(/"/g, '""') + '"'
  }
  return value
}

function exportInventoryCsv(copies: ItemCopy[]) {
  const header = INVENTORY_CSV_COLUMNS.map(escapeCsvField).join(",")
  const rows = copies.map((copy) =>
    INVENTORY_CSV_COLUMNS.map((col) => {
      const val = copy[col as keyof ItemCopy]
      return escapeCsvField(val != null ? String(val) : "")
    }).join(",")
  )
  const csv = [header, ...rows].join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `inventory-export-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function StaffInventoryPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("copies")
  const [isLoading, setIsLoading] = useState(false)

  const [copies, setCopies] = useState<ItemCopy[]>([])
  const [conditionFilter, setConditionFilter] = useState("")
  const [locationFilter, setLocationFilter] = useState("")
  const [showCopyForm, setShowCopyForm] = useState(false)
  const [copyForm, setCopyForm] = useState({ catalog_item_id: 0, barcode: "", location: "", condition: "good", replacement_cost: 0 })

  const [audits, setAudits] = useState<Audit[]>([])
  const [showAuditForm, setShowAuditForm] = useState(false)
  const [auditForm, setAuditForm] = useState({ name: "", description: "", location_filter: "" })
  const [activeAudit, setActiveAudit] = useState<Audit | null>(null)
  const [scanBarcode, setScanBarcode] = useState("")
  const [scanLocation, setScanLocation] = useState("")

  const [selectedCopyId, setSelectedCopyId] = useState<number | null>(null)
  const [lifecycleData, setLifecycleData] = useState<LifecycleTimelineType | null>(null)
  const [loadingLifecycle, setLoadingLifecycle] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const loadData = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      if (activeTab === "copies") {
        const params: Record<string, string> = {}
        if (conditionFilter) params.condition = conditionFilter
        if (locationFilter) params.location = locationFilter
        const data = await fetchApi<{ items: ItemCopy[] }>('/inventory/copies', { params, token })
        setCopies(data.items)
      } else if (activeTab === "audits") {
        const data = await fetchApi<{ items: Audit[] }>('/inventory/audits', { token })
        setAudits(data.items)
      }
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    } finally {
      setIsLoading(false)
    }
  }, [token, activeTab, conditionFilter, locationFilter, t])

  useEffect(() => {
    if (token && isAuthenticated && user?.role !== "patron") loadData()
  }, [token, isAuthenticated, user, activeTab, loadData])

  const handleCreateCopy = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      await fetchApi('/inventory/copies', { method: 'POST', body: copyForm, token })
      toast.success(t('toast.staffInventory.copyCreated'))
      setShowCopyForm(false)
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleWithdraw = async (copyId: number) => {
    if (!token) return
    const reason = prompt("Reason for withdrawal:")
    if (!reason) return
    try {
      await fetchApi('/inventory/copies/' + copyId + '/withdraw', { method: 'POST', body: { reason }, token })
      toast.success(t('toast.inventoryManagement.itemWithdrawn'))
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleCreateAudit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    try {
      const audit = await fetchApi<Audit>('/inventory/audits', { method: 'POST', body: auditForm, token })
      toast.success(t('toast.inventoryManagement.auditStarted'))
      setShowAuditForm(false)
      setActiveAudit(audit)
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleScan = async () => {
    if (!token || !activeAudit || !scanBarcode.trim()) return
    try {
      await fetchApi('/inventory/audits/' + activeAudit.id + '/scan', {
        method: 'POST',
        body: { barcode: scanBarcode, found_at_location: scanLocation || null },
        token,
      })
      toast.success(t('toast.staffInventory.itemScanned'))
      setScanBarcode("")
      const updated = await fetchApi<Audit>('/inventory/audits/' + activeAudit.id, { token })
      setActiveAudit(updated)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.inventoryManagement.scanFailed'))
    }
  }

  const handleCompleteAudit = async () => {
    if (!token || !activeAudit) return
    try {
      await fetchApi('/inventory/audits/' + activeAudit.id + '/complete', { method: 'POST', token })
      toast.success(t('toast.inventoryManagement.auditCompleted'))
      setActiveAudit(null)
      loadData()
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.fundsTab.failed'))
    }
  }

  const handleViewLifecycle = async (copyId: number) => {
    if (!token) return
    setSelectedCopyId(copyId)
    setLoadingLifecycle(true)
    try {
      const data = await getItemCopyLifecycle(token, copyId)
      setLifecycleData(data)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.staffInventory.failedToLoadLifecycle'))
      setSelectedCopyId(null)
    } finally {
      setLoadingLifecycle(false)
    }
  }

  const handleExportCopies = () => {
    if (copies.length === 0) {
      toast.error("No copies to export")
      return
    }
    exportInventoryCsv(copies)
    toast.success(`Exported ${copies.length} copies`)
  }

  if (authLoading) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Inventory" subtitle={t('staffInventory.managePhysicalCopiesAndRun')} actions={<button onClick={() => navigate("/staff/inventory/scan")} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm"><QrCode aria-hidden="true" className="w-4 h-4" />Mobile Scan</button>}>

          <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700">
            {TABS.map((tab) => (<button key={tab.id} onClick={() => setActiveTab(tab.id)} className={"flex items-center gap-2 px-4 py-2 font-medium border-b-2 transition-colors " + (activeTab === tab.id ? "border-earth-600 text-lsc-rose" : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70")}><tab.icon className="w-4 h-4" />{tab.label}</button>))}
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
            {isLoading ? <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div> : activeTab === "copies" ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-4 items-center justify-between">
                  <div className="flex gap-2">
                    <select value={conditionFilter} onChange={(e) => { setConditionFilter(e.target.value); }} className="px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm">
                      <option value="">All Conditions</option>
                      {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                    <input type="text" value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)} placeholder={t('placeholder.lostDamagedReports.filterByLocation')} aria-label={t('aria.lostDamagedReports.filterByLocation')} className="px-3 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm w-48" />
                    <button onClick={loadData} className="px-3 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl text-sm flex items-center gap-1" aria-label={t('aria.staffInventory.searchInventory')}><Search aria-hidden="true" className="w-4 h-4" /></button>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={handleExportCopies} disabled={copies.length === 0} className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 rounded-xl transition-colors border border-lsc-border dark:border-earth-700"><Download aria-hidden="true" className="w-4 h-4" />Export CSV</button>
                    <button onClick={() => setShowCopyForm(true)} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium text-sm"><Plus aria-hidden="true" className="w-4 h-4" />Add Copy</button>
                  </div>
                </div>

                {copies.length === 0 ? <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No copies found</p> : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Barcode</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Title</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Copy #</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Condition</th>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Location</th>
                          <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                        {copies.map((copy) => (
                          <tr key={copy.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown">
                            <td className="px-4 py-3 font-mono text-sm text-lsc-dark dark:text-lsc-cream">{copy.barcode}</td>
                            <td className="px-4 py-3"><p className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={copy.catalog_title || "-"}>{copy.catalog_title || "-"}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{copy.catalog_author}</p></td>
                            <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70">{copy.copy_number}</td>
                            <td className="px-4 py-3"><span className={"px-2 py-0.5 text-xs font-medium rounded " + (CONDITION_COLORS[copy.condition] || "")}>{copy.condition}</span></td>
                            <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{copy.location || "-"}</td>
                            <td className="px-4 py-3 text-right flex gap-2 justify-end">
                              <button onClick={() => handleViewLifecycle(copy.id)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose rounded-xl" title="View Lifecycle" aria-label={`View lifecycle for ${copy.barcode}`}><Clock aria-hidden="true" className="w-4 h-4" /></button>
                              {copy.condition !== "withdrawn" && <button onClick={() => handleWithdraw(copy.id)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-status-danger-600 rounded-xl" title="Withdraw" aria-label={`Withdraw copy ${copy.barcode}`}><Trash2 aria-hidden="true" className="w-4 h-4" /></button>}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : activeTab === "audits" ? (
              <div className="space-y-4">
                {activeAudit ? (
                  <div className="space-y-6">
                    <div className="flex justify-between items-start">
                      <div>
                        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{activeAudit.name}</h2>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Location: {activeAudit.location_filter || "All"}</p>
                      </div>
                      <button onClick={handleCompleteAudit} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Check aria-hidden="true" className="w-4 h-4" />Complete Audit</button>
                    </div>

                    <div className="grid grid-cols-4 gap-4">
                      <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4 text-center"><p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{activeAudit.items_expected}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Expected</p></div>
                      <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-xl p-4 text-center"><p className="text-2xl font-bold text-status-success-600">{activeAudit.items_found}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Found</p></div>
                      <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4 text-center"><p className="text-2xl font-bold text-status-danger-600">{activeAudit.items_missing}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Missing</p></div>
                      <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-4 text-center"><p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{activeAudit.items_misplaced}</p><p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Misplaced</p></div>
                    </div>

                    <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 space-y-4">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"><QrCode aria-hidden="true" className="w-5 h-5" />Scan Item</h3>
                      <div className="flex gap-2">
                        <input type="text" value={scanBarcode} onChange={(e) => setScanBarcode(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleScan()} placeholder={t('staffInventory.scanOrEnterBarcode')} className="flex-1 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono" autoFocus />
                        <input type="text" value={scanLocation} onChange={(e) => setScanLocation(e.target.value)} placeholder={t('placeholder.staffInventory.foundAtLocation')} className="w-48 px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" />
                        <button onClick={handleScan} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium">Scan</button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex justify-between items-center">
                      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Inventory Audits</h2>
                      <button onClick={() => setShowAuditForm(true)} className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"><Plus aria-hidden="true" className="w-4 h-4" />New Audit</button>
                    </div>
                    {audits.length === 0 ? <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">No audits yet</p> : (
                      <div className="grid gap-4">
                        {audits.map((audit) => (
                          <div key={audit.id} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                            <div className="flex justify-between items-start">
                              <div>
                                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{audit.name}</h3>
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{audit.location_filter ? "Location: " + audit.location_filter : "Full inventory"}</p>
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(audit.started_at).toLocaleDateString()}</p>
                              </div>
                              {audit.completed_at ? (
                                <span className="px-2 py-1 text-xs font-medium bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded">Completed</span>
                              ) : (
                                <button onClick={() => setActiveAudit(audit)} className="px-3 py-1 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-xl">Resume</button>
                              )}
                            </div>
                            <div className="mt-3 grid grid-cols-4 gap-2 text-sm">
                              <div><span className="text-lsc-dark/70 dark:text-lsc-cream/70">Expected:</span> <span className="font-medium text-lsc-dark dark:text-lsc-cream">{audit.items_expected}</span></div>
                              <div><span className="text-lsc-dark/70 dark:text-lsc-cream/70">Found:</span> <span className="font-medium text-status-success-600 dark:text-status-success-400">{audit.items_found}</span></div>
                              <div><span className="text-lsc-dark/70 dark:text-lsc-cream/70">Missing:</span> <span className="font-medium text-status-danger-600 dark:text-status-danger-400">{audit.items_missing}</span></div>
                              <div><span className="text-lsc-dark/70 dark:text-lsc-cream/70">Misplaced:</span> <span className="font-medium text-lsc-rose dark:text-lsc-rose-light">{audit.items_misplaced}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ) : null}
          </div>

      {showCopyForm && <ModalBackdrop onClose={() => setShowCopyForm(false)} title="Add Item Copy"><div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md"><div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between"><h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Add Item Copy</h2><button onClick={() => setShowCopyForm(false)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl" aria-label={t('staffInventory.closeAddCopyForm')}><X aria-hidden="true" className="w-5 h-5" /></button></div><form onSubmit={handleCreateCopy} className="p-6 space-y-4"><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Catalog Item ID *</label><input type="number" value={copyForm.catalog_item_id || ""} onChange={(e) => setCopyForm({ ...copyForm, catalog_item_id: parseInt(e.target.value) })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required /></div><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('staffInventory.barcodeAutoGeneratedIfEmpty')}</label><input type="text" value={copyForm.barcode} onChange={(e) => setCopyForm({ ...copyForm, barcode: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono" /></div><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location</label><input type="text" value={copyForm.location} onChange={(e) => setCopyForm({ ...copyForm, location: e.target.value })} placeholder={t('placeholder.staffInventory.egAdultFictionA3')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Condition</label><select value={copyForm.condition} onChange={(e) => setCopyForm({ ...copyForm, condition: e.target.value })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream">{CONDITIONS.slice(0, 5).map((c) => <option key={c} value={c}>{c}</option>)}</select></div><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Replacement Cost</label><input type="number" step="0.01" value={copyForm.replacement_cost || ""} onChange={(e) => setCopyForm({ ...copyForm, replacement_cost: parseFloat(e.target.value) })} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div></div><div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700"><button type="button" onClick={() => setShowCopyForm(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium">Cancel</button><button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Check aria-hidden="true" className="w-4 h-4" />Create</button></div></form></div></ModalBackdrop>}

      {showAuditForm && <ModalBackdrop onClose={() => setShowAuditForm(false)} title="Start Inventory Audit"><div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md"><div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between"><h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Start Inventory Audit</h2><button onClick={() => setShowAuditForm(false)} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl" aria-label={t('aria.staffInventory.closeAuditForm')}><X aria-hidden="true" className="w-5 h-5" /></button></div><form onSubmit={handleCreateAudit} className="p-6 space-y-4"><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Audit Name *</label><input type="text" value={auditForm.name} onChange={(e) => setAuditForm({ ...auditForm, name: e.target.value })} placeholder={t('placeholder.staffInventory.egQ12026Full')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" required /></div><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</label><textarea value={auditForm.description} onChange={(e) => setAuditForm({ ...auditForm, description: e.target.value })} rows={2} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none" /></div><div><label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location Filter (optional)</label><input type="text" value={auditForm.location_filter} onChange={(e) => setAuditForm({ ...auditForm, location_filter: e.target.value })} placeholder={t('staffInventory.leaveEmptyForFullInventory')} className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream" /></div><div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700"><button type="button" onClick={() => setShowAuditForm(false)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium">Cancel</button><button type="submit" className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2"><Clipboard aria-hidden="true" className="w-4 h-4" />Start Audit</button></div></form></div></ModalBackdrop>}

      {selectedCopyId && <ModalBackdrop onClose={() => { setSelectedCopyId(null); setLifecycleData(null) }} title="Item Lifecycle History"><div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-3xl my-8"><div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between"><div><h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Item Lifecycle History</h2>{lifecycleData && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{lifecycleData.item_title} {lifecycleData.item_author && `by ${lifecycleData.item_author}`}</p>}<p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">Barcode: {lifecycleData?.item_copy_barcode}</p></div><button onClick={() => { setSelectedCopyId(null); setLifecycleData(null); }} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl" aria-label={t('aria.staffInventory.closeLifecycleHistory')}><X aria-hidden="true" className="w-5 h-5" /></button></div><div className="p-6 max-h-[70vh] overflow-y-auto">{loadingLifecycle ? <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div> : lifecycleData ? <LifecycleTimeline events={lifecycleData.events} /> : <p className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffInventory.noLifecycleDataAvailable')}</p>}</div></div></ModalBackdrop>}
    </AdminShell>
  )
}
