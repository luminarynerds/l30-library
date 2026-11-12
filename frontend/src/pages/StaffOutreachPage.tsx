/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Users, Loader2, Calendar, AlertTriangle,
  Building2, BarChart3, RefreshCw, CreditCard, DollarSign, Clock,
  FileText, Download, Bell, ClipboardList,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  bulkUpdatePartnerStatus,
  bulkCancelVisits,
  bulkExtendDueDates,
  bulkForfeitDeposits,
  getPartnersExportUrl,
  getVisitsExportUrl,
  getBulkCheckoutsExportUrl,
  getDepositsExportUrl,
  getInstitutionalCardsExportUrl,
  regenerateStatistics,
  getOverdueSummary,
  getDepositSummary,
  getPartnerEngagementAudit,
  listNotificationTemplates,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate,
  setDefaultTemplate,
  listNotificationLogs,
  getNotificationStats,
  PartnerStatus,
  BulkCheckoutStatus,
  DepositStatus,
  InstitutionalCardStatus,
  OutreachNotificationTemplate,
  NotificationType,
  NotificationChannel,
} from "../api/staff-outreach-api"
import { useTranslation, getCurrentLocale } from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'
import { OverviewTab } from '@/components/staff/outreach/OverviewTab'
import { PartnersTab } from '@/components/staff/outreach/PartnersTab'
import { CheckoutsTab } from '@/components/staff/outreach/CheckoutsTab'
import { DepositsTab } from '@/components/staff/outreach/DepositsTab'
import { TemplatesTab } from '@/components/staff/outreach/TemplatesTab'
import { ReportsTab } from '@/components/staff/outreach/ReportsTab'
import { BulkActionModal } from '@/components/staff/outreach/BulkActionModal'
import { TemplateModal } from '@/components/staff/outreach/TemplateModal'
import { ExportModal } from '@/components/staff/outreach/ExportModal'
import { ReportModal } from '@/components/staff/outreach/ReportModal'
import type { TabId, BulkActionType, TemplateFormState } from '@/components/staff/outreach/outreach-types'

const DEFAULT_TEMPLATE_FORM: TemplateFormState = {
  name: "",
  notification_type: "visit_reminder" as NotificationType,
  channel: "email" as NotificationChannel,
  subject: "",
  body: "",
  is_active: true,
  is_default: false,
}

export default function StaffOutreachPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>("overview")
  const [searchQuery, setSearchQuery] = useState("")

  const [partnerStatusFilter, setPartnerStatusFilter] = useState<PartnerStatus | "">("")
  const [checkoutStatusFilter, setCheckoutStatusFilter] = useState<BulkCheckoutStatus | "">("")
  const [depositStatusFilter, setDepositStatusFilter] = useState<DepositStatus | "">("")
  const [cardStatusFilter] = useState<InstitutionalCardStatus | "">("")

  const [showBulkActionModal, setShowBulkActionModal] = useState(false)
  const [showTemplateModal, setShowTemplateModal] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)

  const [selectedPartners, setSelectedPartners] = useState<number[]>([])
  const [selectedVisits, setSelectedVisits] = useState<number[]>([])
  const [selectedCheckouts, setSelectedCheckouts] = useState<number[]>([])
  const [selectedDeposits, setSelectedDeposits] = useState<number[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<OutreachNotificationTemplate | null>(null)

  const [bulkActionType, setBulkActionType] = useState<BulkActionType>("partner_status")
  const [newPartnerStatus, setNewPartnerStatus] = useState<PartnerStatus>("active")
  const [cancellationReason, setCancellationReason] = useState("")
  const [extensionDays, setExtensionDays] = useState(14)
  const [forfeitReason, setForfeitReason] = useState("")
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const [templateForm, setTemplateForm] = useState<TemplateFormState>(DEFAULT_TEMPLATE_FORM)
  const [reportStartDate, setReportStartDate] = useState("")
  const [reportEndDate, setReportEndDate] = useState("")

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  const { data: overdueSummary, isLoading: overdueLoading, refetch: refetchOverdue } = useQuery({
    queryKey: ["outreach-overdue-summary"],
    queryFn: getOverdueSummary,
    enabled: !!token,
  })

  const { data: depositSummary, isLoading: depositSummaryLoading, refetch: refetchDepositSummary } = useQuery({
    queryKey: ["outreach-deposit-summary"],
    queryFn: getDepositSummary,
    enabled: !!token,
  })

  const { data: engagementAudit, isLoading: engagementLoading, refetch: refetchEngagement } = useQuery({
    queryKey: ["outreach-engagement-audit"],
    queryFn: () => getPartnerEngagementAudit(12),
    enabled: !!token && (activeTab === "overview" || activeTab === "reports"),
  })

  const { data: templatesData, isLoading: templatesLoading, refetch: refetchTemplates } = useQuery({
    queryKey: ["outreach-notification-templates"],
    queryFn: () => listNotificationTemplates({ limit: 100 }),
    enabled: !!token && activeTab === "templates",
  })

  const { data: notificationStats } = useQuery({
    queryKey: ["outreach-notification-stats"],
    queryFn: () => getNotificationStats(),
    enabled: !!token && activeTab === "templates",
  })

  useQuery({
    queryKey: ["outreach-notification-logs"],
    queryFn: () => listNotificationLogs({ limit: 50 }),
    enabled: !!token && activeTab === "templates",
  })

  const bulkPartnerStatusMutation = useMutation({
    mutationFn: ({ ids, status }: { ids: number[]; status: PartnerStatus }) =>
      bulkUpdatePartnerStatus(ids, status),
    onSuccess: (data) => {
      toast.success(t('toast.staffOutreach.updatedUpdatedcountPartnersToNewstatus', { updatedcount: data.updated_count, newstatus: data.new_status }))
      setShowBulkActionModal(false)
      setSelectedPartners([])
      refetchEngagement()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const bulkCancelVisitsMutation = useMutation({
    mutationFn: ({ ids, reason }: { ids: number[]; reason: string }) =>
      bulkCancelVisits(ids, reason),
    onSuccess: (data) => {
      toast.success(`Cancelled ${data.cancelled_count} visit(s)`)
      setShowBulkActionModal(false)
      setSelectedVisits([])
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const bulkExtendMutation = useMutation({
    mutationFn: ({ ids, days }: { ids: number[]; days: number }) =>
      bulkExtendDueDates(ids, days),
    onSuccess: (data) => {
      toast.success(`Extended ${data.extended_count} checkout(s) by ${data.extension_days} days`)
      setShowBulkActionModal(false)
      setSelectedCheckouts([])
      refetchOverdue()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const bulkForfeitMutation = useMutation({
    mutationFn: ({ ids, reason }: { ids: number[]; reason: string }) =>
      bulkForfeitDeposits(ids, reason),
    onSuccess: (data) => {
      toast.success(`Forfeited ${data.forfeited_count} deposit(s) totaling $${data.total_amount_forfeited.toFixed(2)}`)
      setShowBulkActionModal(false)
      setSelectedDeposits([])
      refetchDepositSummary()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const createTemplateMutation = useMutation({
    mutationFn: createNotificationTemplate,
    onSuccess: () => {
      toast.success(t('toast.adminBanTracker.templateCreated'))
      setShowTemplateModal(false)
      setTemplateForm(DEFAULT_TEMPLATE_FORM)
      refetchTemplates()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const updateTemplateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof updateNotificationTemplate>[1] }) =>
      updateNotificationTemplate(id, data),
    onSuccess: () => {
      toast.success(t('toast.adminBanTracker.templateUpdated'))
      setShowTemplateModal(false)
      setSelectedTemplate(null)
      refetchTemplates()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const deleteTemplateMutation = useMutation({
    mutationFn: deleteNotificationTemplate,
    onSuccess: () => {
      toast.success(t('toast.adminBanTracker.templateDeleted'))
      refetchTemplates()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const setDefaultTemplateMutation = useMutation({
    mutationFn: setDefaultTemplate,
    onSuccess: () => {
      toast.success(t('staffOutreach.setAsDefaultTemplate'))
      refetchTemplates()
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const regenerateStatsMutation = useMutation({
    mutationFn: ({ start, end }: { start: string; end: string }) =>
      regenerateStatistics(start, end),
    onSuccess: () => {
      toast.success(t('toast.staffOutreach.statisticsRegenerated'))
      setShowReportModal(false)
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleRefresh = () => {
    refetchOverdue()
    refetchDepositSummary()
    refetchEngagement()
    if (activeTab === "templates") refetchTemplates()
  }

  const handleBulkAction = () => {
    switch (bulkActionType) {
      case "partner_status":
        if (selectedPartners.length === 0) { toast.error(t('staffOutreach.selectAtLeastOnePartner')); return }
        bulkPartnerStatusMutation.mutate({ ids: selectedPartners, status: newPartnerStatus })
        break
      case "cancel_visits":
        if (selectedVisits.length === 0) { toast.error(t('staffOutreach.selectAtLeastOneVisit')); return }
        if (!cancellationReason.trim()) { toast.error(t('staffOutreach.pleaseProvideACancellationReason')); return }
        bulkCancelVisitsMutation.mutate({ ids: selectedVisits, reason: cancellationReason })
        break
      case "extend_due":
        if (selectedCheckouts.length === 0) { toast.error(t('staffOutreach.selectAtLeastOneCheckout')); return }
        bulkExtendMutation.mutate({ ids: selectedCheckouts, days: extensionDays })
        break
      case "forfeit_deposits":
        if (selectedDeposits.length === 0) { toast.error(t('staffOutreach.selectAtLeastOneDeposit')); return }
        if (!forfeitReason.trim()) { toast.error(t('staffOutreach.pleaseProvideAReasonFor')); return }
        bulkForfeitMutation.mutate({ ids: selectedDeposits, reason: forfeitReason })
        break
    }
  }

  const handleExport = (type: string) => {
    let url = ""
    switch (type) {
      case "partners": url = getPartnersExportUrl({ ...(partnerStatusFilter && { status: partnerStatusFilter }) }); break
      case "visits": url = getVisitsExportUrl({}); break
      case "checkouts": url = getBulkCheckoutsExportUrl({ ...(checkoutStatusFilter && { status: checkoutStatusFilter }) }); break
      case "deposits": url = getDepositsExportUrl({ ...(depositStatusFilter && { status: depositStatusFilter }) }); break
      case "cards": url = getInstitutionalCardsExportUrl({ ...(cardStatusFilter && { status: cardStatusFilter }) }); break
    }
    if (url) {
      window.open(url, "_blank", "noopener,noreferrer")
      toast.success(t('toast.staffOutreach.exportingType', { type }))
    }
    setShowExportModal(false)
  }

  const handleSaveTemplate = () => {
    if (!templateForm.name.trim() || !templateForm.body.trim()) {
      toast.error(t('staffOutreach.nameAndBodyAreRequired'))
      return
    }
    if (selectedTemplate) {
      updateTemplateMutation.mutate({ id: selectedTemplate.id, data: templateForm })
    } else {
      createTemplateMutation.mutate(templateForm)
    }
  }

  const handleEditTemplate = (template: OutreachNotificationTemplate) => {
    setSelectedTemplate(template)
    setTemplateForm({
      name: template.name,
      notification_type: template.notification_type,
      channel: template.channel,
      subject: template.subject || "",
      body: template.body,
      is_active: template.is_active,
      is_default: template.is_default,
    })
    setShowTemplateModal(true)
  }

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount)

  const tabs: { id: TabId; label: string; icon: React.ReactNode; badge?: number }[] = [
    { id: "overview", label: "Overview", icon: <BarChart3 className="w-4 h-4" /> },
    { id: "partners", label: "Partners", icon: <Building2 className="w-4 h-4" /> },
    { id: "visits", label: "Visits", icon: <Calendar className="w-4 h-4" /> },
    { id: "checkouts", label: "Bulk Checkouts", icon: <ClipboardList className="w-4 h-4" />, ...(overdueSummary?.total_overdue_checkouts && { badge: overdueSummary.total_overdue_checkouts }) },
    { id: "deposits", label: "Deposits", icon: <DollarSign className="w-4 h-4" /> },
    { id: "cards", label: "Inst. Cards", icon: <CreditCard className="w-4 h-4" /> },
    { id: "templates", label: "Notifications", icon: <Bell className="w-4 h-4" /> },
    { id: "reports", label: "Reports", icon: <FileText className="w-4 h-4" /> },
  ]

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Outreach Management">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
            <Users className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Outreach Management
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Manage partners, visits, checkouts, and deposits
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowExportModal(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
          >
            <Download className="w-4 h-4" /> Export
          </button>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </div>

      {!overdueLoading && !depositSummaryLoading && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: <Building2 className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />, value: engagementAudit?.total_partners || 0, label: 'Active Partners' },
            { icon: <AlertTriangle className="w-8 h-8 text-status-danger-500" />, value: overdueSummary?.total_overdue_checkouts || 0, label: 'Overdue Checkouts' },
            { icon: <DollarSign className="w-8 h-8 text-status-success-500" />, value: formatCurrency(depositSummary?.total_amount_held || 0), label: 'Deposits Held' },
            { icon: <Clock className="w-8 h-8 text-status-warning-500" />, value: (depositSummary?.expiring_within_30_days?.length || 0) + (depositSummary?.expired_deposits?.length || 0), label: 'Deposits Expiring' },
          ].map((stat, i) => (
            <div key={i} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3">
                {stat.icon}
                <div>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{stat.label}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="border-b border-lsc-border dark:border-earth-700">
        <nav className="flex gap-4 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-lsc-rose text-lsc-rose dark:text-lsc-rose-light"
                  : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
              }`}
            >
              {tab.icon}
              <span className="font-medium">{tab.label}</span>
              {tab.badge !== undefined && tab.badge > 0 && (
                <span className="px-2 py-0.5 text-xs bg-status-danger-500 text-white rounded-full">{tab.badge}</span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === "overview" && (
        <OverviewTab
          overdueSummary={overdueSummary}
          depositSummary={depositSummary}
          engagementAudit={engagementAudit}
          formatDate={formatDate}
          formatCurrency={formatCurrency}
          onViewCheckouts={() => setActiveTab("checkouts")}
        />
      )}

      {activeTab === "partners" && (
        <PartnersTab
          engagementAudit={engagementAudit}
          engagementLoading={engagementLoading}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          partnerStatusFilter={partnerStatusFilter}
          setPartnerStatusFilter={setPartnerStatusFilter}
          selectedPartners={selectedPartners}
          setSelectedPartners={setSelectedPartners}
          onBulkUpdate={() => { setBulkActionType("partner_status"); setShowBulkActionModal(true) }}
          formatDate={formatDate}
        />
      )}

      {activeTab === "checkouts" && (
        <CheckoutsTab
          overdueSummary={overdueSummary}
          overdueLoading={overdueLoading}
          checkoutStatusFilter={checkoutStatusFilter}
          setCheckoutStatusFilter={setCheckoutStatusFilter}
          selectedCheckouts={selectedCheckouts}
          setSelectedCheckouts={setSelectedCheckouts}
          onExtendDue={() => { setBulkActionType("extend_due"); setShowBulkActionModal(true) }}
          formatDate={formatDate}
        />
      )}

      {activeTab === "deposits" && (
        <DepositsTab
          depositSummary={depositSummary}
          depositStatusFilter={depositStatusFilter}
          setDepositStatusFilter={setDepositStatusFilter}
          selectedDeposits={selectedDeposits}
          setSelectedDeposits={setSelectedDeposits}
          onForfeit={() => { setBulkActionType("forfeit_deposits"); setShowBulkActionModal(true) }}
          formatCurrency={formatCurrency}
        />
      )}

      {activeTab === "templates" && (
        <TemplatesTab
          templatesData={templatesData}
          templatesLoading={templatesLoading}
          notificationStats={notificationStats}
          onNew={() => { setSelectedTemplate(null); setTemplateForm(DEFAULT_TEMPLATE_FORM); setShowTemplateModal(true) }}
          onEdit={handleEditTemplate}
          onDelete={(id) => { setPendingAction(() => () => deleteTemplateMutation.mutate(id)); setConfirmOpen(true) }}
          onSetDefault={(id) => setDefaultTemplateMutation.mutate(id)}
        />
      )}

      {activeTab === "reports" && (
        <ReportsTab
          onRegenerateStats={() => setShowReportModal(true)}
          onExport={handleExport}
        />
      )}

      {showBulkActionModal && (
        <BulkActionModal
          bulkActionType={bulkActionType}
          selectedPartners={selectedPartners}
          selectedVisits={selectedVisits}
          selectedCheckouts={selectedCheckouts}
          selectedDeposits={selectedDeposits}
          newPartnerStatus={newPartnerStatus}
          setNewPartnerStatus={setNewPartnerStatus}
          cancellationReason={cancellationReason}
          setCancellationReason={setCancellationReason}
          extensionDays={extensionDays}
          setExtensionDays={setExtensionDays}
          forfeitReason={forfeitReason}
          setForfeitReason={setForfeitReason}
          isPending={
            bulkPartnerStatusMutation.isPending ||
            bulkCancelVisitsMutation.isPending ||
            bulkExtendMutation.isPending ||
            bulkForfeitMutation.isPending
          }
          onConfirm={handleBulkAction}
          onClose={() => setShowBulkActionModal(false)}
        />
      )}

      {showTemplateModal && (
        <TemplateModal
          selectedTemplate={selectedTemplate}
          templateForm={templateForm}
          setTemplateForm={setTemplateForm}
          isPending={createTemplateMutation.isPending || updateTemplateMutation.isPending}
          onSave={handleSaveTemplate}
          onClose={() => setShowTemplateModal(false)}
        />
      )}

      {showExportModal && (
        <ExportModal onExport={handleExport} onClose={() => setShowExportModal(false)} />
      )}

      {showReportModal && (
        <ReportModal
          reportStartDate={reportStartDate}
          setReportStartDate={setReportStartDate}
          reportEndDate={reportEndDate}
          setReportEndDate={setReportEndDate}
          isPending={regenerateStatsMutation.isPending}
          onGenerate={() => {
            if (!reportStartDate || !reportEndDate) {
              toast.error(t('staffOutreach.pleaseSelectBothDates'))
              return
            }
            regenerateStatsMutation.mutate({ start: reportStartDate, end: reportEndDate })
          }}
          onClose={() => setShowReportModal(false)}
        />
      )}

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete template?"
        message="Are you sure you want to delete this notification template?"
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </AdminShell>
  )
}
