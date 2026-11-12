/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef, type KeyboardEvent } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "../../contexts/AuthContext"
import { AdminShell } from "../../components/shells/AdminShell"
import { Loader2, DollarSign, Users, Search, Package, Truck, Calendar, FileText, LayoutDashboard } from "lucide-react"
import toast from "react-hot-toast"
import AcquisitionReleasesTab from "../../components/acquisition/AcquisitionReleasesTab"
import { useTranslation} from "@/i18n"
import { getOrderTemplates } from "@/api/order-templates-api"
import { type Fund, type Vendor, type SelectionItem, type PurchaseOrder, type OrderTemplate, apiFetch, formatMoney, RELEASES_API } from "./types"
import DashboardTab from "./DashboardTab"
import FundsTab from "./FundsTab"
import VendorsTab from "./VendorsTab"
import SelectionTab from "./SelectionTab"
import OrdersTab from "./OrdersTab"
import ReceivingTab from "./ReceivingTab"
import TemplatesTab from "./TemplatesTab"

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "funds", label: "Funds", icon: DollarSign },
  { id: "vendors", label: "Vendors", icon: Users },
  { id: "selection", label: "Selection", icon: Search },
  { id: "orders", label: "Orders", icon: Package },
  { id: "receiving", label: "Receiving", icon: Truck },
  { id: "templates", label: "Templates", icon: FileText },
  { id: "releases", label: "Releases", icon: Calendar },
]

const TAB_IDS = TABS.map((t) => t.id)
const DEFAULT_TAB = "dashboard"

export default function StaffAcquisitionPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const rawTab = searchParams.get("tab")
  const activeTab = rawTab && TAB_IDS.includes(rawTab) ? rawTab : DEFAULT_TAB
  const setActiveTab = useCallback((tab: string) => {
    setSearchParams({ tab }, { replace: false })
  }, [setSearchParams])

  // Normalize URL on mount: write ?tab=dashboard when missing/invalid (replace, no history entry).
  useEffect(() => {
    if (rawTab !== activeTab) {
      setSearchParams({ tab: activeTab }, { replace: true })
    }
  }, [rawTab, activeTab, setSearchParams])

  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const onTablistKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const idx = TAB_IDS.indexOf(activeTab)
    if (idx < 0) return
    let nextIdx: number | null = null
    if (e.key === "ArrowRight") nextIdx = (idx + 1) % TAB_IDS.length
    else if (e.key === "ArrowLeft") nextIdx = (idx - 1 + TAB_IDS.length) % TAB_IDS.length
    else if (e.key === "Home") nextIdx = 0
    else if (e.key === "End") nextIdx = TAB_IDS.length - 1
    if (nextIdx === null) return
    e.preventDefault()
    const nextId = TAB_IDS[nextIdx]
    if (!nextId) return
    setActiveTab(nextId)
    // Move focus to the newly active tab (auto-activation pattern).
    requestAnimationFrame(() => {
      tabRefs.current[nextId]?.focus()
    })
  }

  // Per-tab document title; restore prior title on unmount.
  useEffect(() => {
    const prevTitle = document.title
    const label = TABS.find((tab) => tab.id === activeTab)?.label ?? "Acquisitions"
    document.title = `${label} — Acquisitions — L30`
    return () => {
      document.title = prevTitle
    }
  }, [activeTab])

  const [isLoading, setIsLoading] = useState(false)
  const [funds, setFunds] = useState<Fund[]>([])
  const [vendors, setVendors] = useState<Vendor[]>([])
  const [selectionItems, setSelectionItems] = useState<SelectionItem[]>([])
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [templates, setTemplates] = useState<OrderTemplate[]>([])

  const [showSaveAsTemplate, setShowSaveAsTemplate] = useState(false)
  const [saveTemplatePOId, setSaveTemplatePOId] = useState<number>(0)
  const [saveTemplateForm, setSaveTemplateForm] = useState({ name: "", description: "", is_shared: false })

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
      if (activeTab === "dashboard") {
        // Dashboard fetches its own data
      } else if (activeTab === "funds") {
        const data = await apiFetch<{ items: Fund[] }>(token, "/funds")
        setFunds(data.items)
      } else if (activeTab === "vendors") {
        const data = await apiFetch<{ items: Vendor[] }>(token, "/vendors")
        setVendors(data.items)
      } else if (activeTab === "selection") {
        const data = await apiFetch<{ items: SelectionItem[] }>(token, "/selection-list")
        setSelectionItems(data.items)
      } else if (activeTab === "orders") {
        const [ordersData, vendorsData, fundsData] = await Promise.all([
          apiFetch<{ items: PurchaseOrder[] }>(token, "/purchase-orders"),
          apiFetch<{ items: Vendor[] }>(token, "/vendors"),
          apiFetch<{ items: Fund[] }>(token, "/funds"),
        ])
        setOrders(ordersData.items)
        setVendors(vendorsData.items)
        setFunds(fundsData.items)
      } else if (activeTab === "receiving") {
        const [ordersData, vendorsData, fundsData] = await Promise.all([
          apiFetch<{ items: PurchaseOrder[] }>(token, "/purchase-orders"),
          apiFetch<{ items: Vendor[] }>(token, "/vendors"),
          apiFetch<{ items: Fund[] }>(token, "/funds"),
        ])
        setOrders(ordersData.items)
        setVendors(vendorsData.items)
        setFunds(fundsData.items)
      } else if (activeTab === "templates") {
        const [templatesData, vendorsData, fundsData] = await Promise.all([
          getOrderTemplates(),
          apiFetch<{ items: Vendor[] }>(token, "/vendors"),
          apiFetch<{ items: Fund[] }>(token, "/funds"),
        ])
        setTemplates(templatesData)
        setVendors(vendorsData.items)
        setFunds(fundsData.items)
      } else if (activeTab === "releases") {
        const [vendorsData, fundsData] = await Promise.all([
          apiFetch<{ items: Vendor[] }>(token, "/vendors"),
          apiFetch<{ items: Fund[] }>(token, "/funds"),
        ])
        setVendors(vendorsData.items)
        setFunds(fundsData.items)
      }
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.index.unableToLoadDataPlease'))
    } finally {
      setIsLoading(false)
    }
  }, [token, activeTab, t])

  useEffect(() => {
    if (token && isAuthenticated && user?.role !== "patron") loadData()
  }, [token, isAuthenticated, user, activeTab, loadData])

  const handleCreatePOFromReleases = async (selectedIds: string[], vendorId: number, fundId: number) => {
    if (!token) return
    try {
      const data = await apiFetch<{ po_number: string; items_added: number }>(
        token,
        RELEASES_API + "/librarian/create-po",
        { method: "POST", body: JSON.stringify({ tracker_book_ids: selectedIds, vendor_id: vendorId, fund_id: fundId }) }
      )
      toast.success(t('toast.templatesTab.poPonumberCreatedWithItemsadded', { ponumber: data.po_number, itemsadded: data.items_added }))
      loadData()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.index.failedToCreatePurchaseOrder'))
      throw err
    }
  }

  const openSaveAsTemplate = (poId: number) => {
    setSaveTemplatePOId(poId)
    setSaveTemplateForm({ name: "", description: "", is_shared: false })
    setShowSaveAsTemplate(true)
  }

  if (authLoading) return <div className="flex items-center justify-center min-h-[400px]"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div>
  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Acquisitions" subtitle={t('staffAcquisition.manageFundsVendorsAndPurchase')}>
          <div role="tablist" aria-label="Acquisition sections" onKeyDown={onTablistKeyDown} className="flex gap-2 border-b border-lsc-border dark:border-earth-700 overflow-x-auto">
            {TABS.map((tab) => (<button key={tab.id} ref={(el) => { tabRefs.current[tab.id] = el }} role="tab" id={`acq-tab-${tab.id}`} aria-selected={activeTab === tab.id} aria-controls={`acq-panel-${tab.id}`} tabIndex={activeTab === tab.id ? 0 : -1} onClick={() => setActiveTab(tab.id)} className={"flex items-center gap-2 px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap " + (activeTab === tab.id ? "border-earth-600 text-lsc-rose" : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70")}><tab.icon aria-hidden="true" className="w-4 h-4" />{tab.label}</button>))}
          </div>
          <div role="tabpanel" id={`acq-panel-${activeTab}`} aria-labelledby={`acq-tab-${activeTab}`} tabIndex={-1} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6">
            {isLoading ? <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" /></div> : activeTab === "dashboard" ? (
              <DashboardTab token={token || ""} onNavigateTab={(tab: string) => setActiveTab(tab)} />
            ) : activeTab === "funds" ? (
              <FundsTab token={token || ""} funds={funds} loadData={loadData} />
            ) : activeTab === "vendors" ? (
              <VendorsTab token={token || ""} vendors={vendors} loadData={loadData} />
            ) : activeTab === "selection" ? (
              <SelectionTab token={token || ""} selectionItems={selectionItems} vendors={vendors} funds={funds} loadData={loadData} setActiveTab={setActiveTab} />
            ) : activeTab === "orders" ? (
              <OrdersTab token={token || ""} funds={funds} vendors={vendors} orders={orders} user={user} loadData={loadData} onSaveAsTemplate={openSaveAsTemplate} />
            ) : activeTab === "receiving" ? (
              <ReceivingTab token={token || ""} vendors={vendors} funds={funds} orders={orders} loadData={loadData} />
            ) : activeTab === "templates" ? (
              <TemplatesTab token={token || ""} funds={funds} vendors={vendors} templates={templates} loadData={loadData} setActiveTab={setActiveTab} showSaveAsTemplate={showSaveAsTemplate} setShowSaveAsTemplate={setShowSaveAsTemplate} saveTemplatePOId={saveTemplatePOId} saveTemplateForm={saveTemplateForm} setSaveTemplateForm={setSaveTemplateForm} />
            ) : activeTab === "releases" ? (
              <AcquisitionReleasesTab
                token={token || ""}
                vendors={vendors.map(v => ({ id: v.id, name: v.name }))}
                funds={funds.map(f => ({ id: f.id, name: f.name, available_amount: f.available_amount }))}
                onCreatePO={handleCreatePOFromReleases}
                onSwitchToOrders={() => { setActiveTab("orders"); loadData() }}
                formatMoney={formatMoney}
              />
            ) : null}
      </div>
    </AdminShell>
  )
}
