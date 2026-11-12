/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Loader2,
  Truck,
  ClipboardList,
  Package,
  BookHeart,
  ListPlus,
} from "lucide-react"
import toast from "react-hot-toast"
import { useAuth } from "../../contexts/AuthContext"
import {
  getMyApplications,
  getMyEnrollment,
  type HomeDeliveryApplication,
  type HomeDeliveryEnrollment,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import type { TabId } from "./types"
import { ApplyTab } from "./ApplicationForm"
import { EnrollmentTab } from "./EnrollmentManagement"
import { DeliveriesTab } from "./DeliverySchedule"
import { PreferencesTab } from "./ReadingPreferences"
import { RequestsTab } from "./ItemRequests"
import PageContainer from '@/components/layout/PageContainer'

export default function PatronHomeDeliveryPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [activeTab, setActiveTab] = useState<TabId>(() => {
    const tab = searchParams.get("tab")
    return (tab && ["apply", "enrollment", "deliveries", "preferences", "requests"].includes(tab))
      ? tab as TabId
      : "apply"
  })

  const [loading, setLoading] = useState(true)
  const [applications, setApplications] = useState<HomeDeliveryApplication[]>([])
  const [enrollment, setEnrollment] = useState<HomeDeliveryEnrollment | null>(null)

  const isEnrolled = enrollment !== null && (enrollment.status === "active" || enrollment.status === "paused")

  const handleTabChange = useCallback((tab: TabId) => {
    setActiveTab(tab)
    setSearchParams({ tab }, { replace: true })
  }, [setSearchParams])

  useEffect(() => {
    if (!isAuthenticated) return
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [apps, enr] = await Promise.all([
          getMyApplications().catch(() => [] as HomeDeliveryApplication[]),
          getMyEnrollment().catch(() => null),
        ])
        if (cancelled) return
        setApplications(apps)
        setEnrollment(enr)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [isAuthenticated])

  useEffect(() => {
    const tab = searchParams.get("tab")
    if (tab && ["apply", "enrollment", "deliveries", "preferences", "requests"].includes(tab)) {
      setActiveTab(tab as TabId)
    }
  }, [searchParams])

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-cream dark:bg-earth-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-sage" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-cream dark:bg-earth-900 flex items-center justify-center px-4">
        <div className="text-center">
          <Truck className="w-12 h-12 text-sage mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Home Delivery Service</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t("patronHomeDelivery.pleaseSignInToAccess")}</p>
        </div>
      </div>
    )
  }

  const tabs: { id: TabId; label: string; icon: React.ElementType; requiresEnrollment?: boolean }[] = [
    { id: "apply", label: "Apply", icon: ClipboardList },
    { id: "enrollment", label: "Enrollment", icon: Package, requiresEnrollment: true },
    { id: "deliveries", label: "Deliveries", icon: Truck, requiresEnrollment: true },
    { id: "preferences", label: "Preferences", icon: BookHeart, requiresEnrollment: true },
    { id: "requests", label: "Requests", icon: ListPlus, requiresEnrollment: true },
  ]

  return (
    <div className="min-h-screen bg-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Truck className="w-8 h-8 text-sage" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Home Delivery Service
            </h1>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Library materials delivered to your door. Apply, manage your enrollment, and track deliveries.
          </p>
        </div>

        {/* Tab Bar */}
        <nav className="flex gap-1 overflow-x-auto border-b border-sage/20 dark:border-earth-700 mb-6" role="tablist" aria-label={t('aria.index.homeDeliverySections')}>
          {tabs.map(tab => {
            const disabled = tab.requiresEnrollment && !isEnrolled
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-disabled={disabled}
                aria-controls={`panel-${tab.id}`}
                tabIndex={disabled ? -1 : activeTab === tab.id ? 0 : -1}
                title={disabled ? "Complete your application first" : undefined}
                onClick={() => !disabled && handleTabChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap min-h-[44px] transition-colors border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? "border-sage text-sage-700 dark:text-sage-300"
                    : disabled
                      ? "border-transparent text-lsc-dark/30 dark:text-lsc-cream/60 cursor-not-allowed"
                      : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-sage hover:border-sage/50"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>

        {/* Tab Panels */}
        <div id={`panel-${activeTab}`} role="tabpanel" aria-labelledby={activeTab}>
          {activeTab === "apply" && (
            <ApplyTab
              applications={applications}
              onApplicationCreated={(app) => {
                setApplications(prev => [app, ...prev])
                toast.success(t('toast.index.applicationSubmittedSuccessfully'))
              }}
              isEnrolled={isEnrolled}
              onGoToEnrollment={() => handleTabChange("enrollment")}
            />
          )}
          {activeTab === "enrollment" && isEnrolled && enrollment && (
            <EnrollmentTab
              enrollment={enrollment}
              onEnrollmentUpdated={setEnrollment}
            />
          )}
          {activeTab === "deliveries" && isEnrolled && (
            <DeliveriesTab />
          )}
          {activeTab === "preferences" && isEnrolled && enrollment && (
            <PreferencesTab enrollment={enrollment} />
          )}
          {activeTab === "requests" && isEnrolled && (
            <RequestsTab />
          )}
        </div>
      </PageContainer>
    </div>
  )
}
