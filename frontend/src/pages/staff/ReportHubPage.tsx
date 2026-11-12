/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRightLeft, AlertTriangle, Wallet, DollarSign,
  Users, UserCheck, Package, Leaf,
  Truck, DoorOpen, Wrench,
  FileText, Building2, TrendingUp, BarChart3,
  PlayCircle, BookOpen, Activity, Layers,
  Shield, MapPin, ShieldCheck, Eye, Globe,
  Share2, LineChart, Layers3, GraduationCap,
  PieChart, ScrollText, Calendar, Sparkles, HeartHandshake, QrCode,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory } from "../../components/navigation/NavigationHub";
import ReportScheduleModal from "../../components/reports/ReportScheduleModal";
import { useAuth } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api-client";

// TODO(server-side-favorites cleanup): remove this localStorage key + the
// one-shot migration effect below once all clients have loaded the page at
// least once after the server-side favorites migration shipped (PR #770/771
// stack). Tracked as part of the dead-code sweep for hub favorites.
const LEGACY_STORAGE_KEY = "l30-report-hub-favorites";
const REPORT_HUB_SLUG = "report-hub";

// Role requirements for hub destinations gated more narrowly than the report
// hub itself (which any staff-area role can open). Mirrors the route guards in
// StaffRoutes/BoardRoutes so we never show a card that would just bounce the
// user to /account. Keyed by path without hash. Keep in sync with those routes.
const RESTRICTED_REPORT_PATHS: Record<string, string[]> = {
  "/staff/admin/compliance": ["admin", "director"],
  "/staff/admin/financial": ["admin", "director"],
  "/staff/admin/school-impact": ["admin", "director"],
  "/staff/admin/strategic/analytics": ["admin", "director"],
  "/staff/admin/website-analytics": ["admin", "director"],
  "/staff/admin/annual-reports": ["admin", "director", "staff"],
  "/staff/admin/treasurer": ["admin", "staff"],
  "/board/reports": ["admin", "staff"],
  "/board/reports/templates": ["admin", "staff"],
  "/board/reports/schedules": ["admin", "staff"],
};

async function migrateLegacyFavorites(): Promise<void> {
  if (typeof window === "undefined") return;
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
  } catch {
    return;
  }
  if (!raw) return;
  let paths: string[] = [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      paths = parsed.filter((p): p is string => typeof p === "string");
    }
  } catch {
    // Corrupt blob — drop it.
    try { window.localStorage.removeItem(LEGACY_STORAGE_KEY); } catch { /* ignore */ }
    return;
  }

  // POST each path. Endpoint is idempotent (PR #770), so failures are
  // independent and we don't need to dedupe locally. We only clear the
  // localStorage key after all POSTs settle so a partial-failure migration
  // can retry on the next page load.
  const results = await Promise.allSettled(
    paths.map((p) =>
      apiClient("/hub-favorites", {
        method: "POST",
        body: JSON.stringify({ hub_slug: REPORT_HUB_SLUG, item_path: p }),
      }),
    ),
  );
  const anyFailed = results.some((r) => r.status === "rejected");
  if (!anyFailed) {
    try { window.localStorage.removeItem(LEGACY_STORAGE_KEY); } catch { /* ignore */ }
  }
}

export default function ReportHubPage() {
  const { t } = useTranslation();
  const { isAuthenticated, user } = useAuth();
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);

  // One-shot localStorage -> server migration on mount (authenticated only).
  useEffect(() => {
    if (!isAuthenticated) return;
    void migrateLegacyFavorites();
  }, [isAuthenticated]);

  const categories = useMemo<HubCategory[]>(
    () => [
      {
        id: "circulation",
        title: t("reportHub.categories.circulation"),
        icon: ArrowRightLeft,
        items: [
          { label: t("reportHub.items.circulationReports.label"), to: "/staff/reports", description: t("reportHub.items.circulationReports.description"), icon: ArrowRightLeft, keywords: ["checkout", "return", "transaction"] },
          { label: t("reportHub.items.overdueLostDamaged.label"), to: "/staff/reports/lost-damaged", description: t("reportHub.items.overdueLostDamaged.description"), icon: AlertTriangle, keywords: ["overdue", "lost", "damaged", "missing"] },
          { label: t("reportHub.items.streamingReports.label"), to: "/staff/streaming/reports", description: t("reportHub.items.streamingReports.description"), icon: PlayCircle, keywords: ["streaming", "digital", "media"] },
          { label: t("reportHub.items.unifiedReports.label"), to: "/staff/reports/unified", description: t("reportHub.items.unifiedReports.description"), icon: Layers, keywords: ["unified", "combined", "consolidated"] },
        ],
      },
      {
        id: "financial",
        title: t("reportHub.categories.financial"),
        icon: Wallet,
        items: [
          { label: t("reportHub.items.financialReports.label"), to: "/staff/admin/financial", description: t("reportHub.items.financialReports.description"), icon: Wallet, keywords: ["budget", "revenue", "expense", "money"] },
          { label: t("reportHub.items.fineManagement.label"), to: "/staff/fines", description: t("reportHub.items.fineManagement.description"), icon: DollarSign, keywords: ["fine", "fee", "waiver", "payment"] },
          { label: t("reportHub.items.treasurerDashboard.label"), to: "/staff/admin/treasurer", description: t("reportHub.items.treasurerDashboard.description"), icon: DollarSign, keywords: ["treasurer", "cash", "reconciliation"] },
        ],
      },
      {
        id: "patrons",
        title: t("reportHub.categories.patrons"),
        icon: Users,
        items: [
          { label: t("reportHub.items.patronSegmentation.label"), to: "/staff/patron-segmentation", description: t("reportHub.items.patronSegmentation.description"), icon: Users, keywords: ["patron", "demographic", "segment"] },
          { label: t("reportHub.items.usageStatistics.label"), to: "/staff/usage-statistics", description: t("reportHub.items.usageStatistics.description"), icon: Activity, keywords: ["usage", "activity", "engagement"] },
          { label: t("reportHub.items.journeyAnalytics.label"), to: "/staff/admin/analytics/journeys", description: t("reportHub.items.journeyAnalytics.description"), icon: UserCheck, keywords: ["journey", "funnel", "touchpoint"] },
          { label: t("reportHub.items.cohortAnalysis.label"), to: "/staff/analytics/cohorts", description: t("reportHub.items.cohortAnalysis.description"), icon: PieChart, keywords: ["cohort", "retention", "lifecycle"] },
          { label: t("reportHub.items.sharingAnalytics.label"), to: "/staff/admin/analytics/sharing", description: t("reportHub.items.sharingAnalytics.description"), icon: Share2, keywords: ["sharing", "social", "referral"] },
          { label: t("reportHub.items.predictiveAnalytics.label"), to: "/staff/admin/analytics/predictive", description: t("reportHub.items.predictiveAnalytics.description"), icon: Sparkles, keywords: ["predictive", "forecast", "ml", "model"] },
        ],
      },
      {
        id: "collection",
        title: t("reportHub.categories.collection"),
        icon: Package,
        items: [
          { label: t("reportHub.items.inventoryReports.label"), to: "/staff/inventory-management", description: t("reportHub.items.inventoryReports.description"), icon: Package, keywords: ["inventory", "count", "barcode"] },
          { label: t("reportHub.items.weedingAnalysis.label"), to: "/staff/weeding", description: t("reportHub.items.weedingAnalysis.description"), icon: Leaf, keywords: ["weed", "deselect", "withdraw"] },
          { label: t("reportHub.items.collectionAnalytics.label"), to: "/staff/collection-analytics", description: t("reportHub.items.collectionAnalytics.description"), icon: LineChart, keywords: ["collection", "turnover", "format"] },
          { label: t("reportHub.items.collectionDashboard.label"), to: "/staff/collection-dashboard", description: t("reportHub.items.collectionDashboard.description"), icon: Layers3, keywords: ["collection", "health", "overview"] },
        ],
      },
      {
        id: "operations",
        title: t("reportHub.categories.operations"),
        icon: Wrench,
        items: [
          { label: t("reportHub.items.homeDeliveryReports.label"), to: "/staff/home-delivery/reports", description: t("reportHub.items.homeDeliveryReports.description"), icon: Truck, keywords: ["delivery", "homebound", "route", "volunteer"] },
          { label: t("reportHub.items.roomReservationReports.label"), to: "/staff/reports/rooms", description: t("reportHub.items.roomReservationReports.description"), icon: DoorOpen, keywords: ["room", "reservation", "booking", "meeting"] },
          { label: t("reportHub.items.customReportBuilder.label"), to: "/staff/custom-reports", description: t("reportHub.items.customReportBuilder.description"), icon: Layers, keywords: ["custom", "ad-hoc", "builder"] },
          { label: t("reportHub.items.reportAuditLog.label"), to: "/staff/reports/audit-log", description: t("reportHub.items.reportAuditLog.description"), icon: ScrollText, keywords: ["audit", "log", "history", "export"] },
        ],
      },
      {
        id: "compliance",
        title: t("reportHub.categories.compliance"),
        icon: Shield,
        items: [
          { label: t("reportHub.items.complianceDashboard.label"), to: "/staff/admin/compliance", description: t("reportHub.items.complianceDashboard.description"), icon: ShieldCheck, keywords: ["compliance", "audit", "violation", "policy"] },
          { label: t("reportHub.items.stateCompliance.label"), to: "/staff/admin/compliance#state", description: t("reportHub.items.stateCompliance.description"), icon: MapPin, keywords: ["state", "library", "deadline", "report", "annual survey"] },
          { label: t("reportHub.items.cipaCompliance.label"), to: "/staff/admin/compliance#cipa", description: t("reportHub.items.cipaCompliance.description"), icon: Eye, keywords: ["cipa", "filter", "internet", "child"] },
          { label: t("reportHub.items.publicRecords.label"), to: "/staff/admin/compliance#public-records", description: t("reportHub.items.publicRecords.description"), icon: FileText, keywords: ["public records", "foia", "disclosure"] },
          { label: t("reportHub.items.annualReports.label"), to: "/staff/admin/annual-reports", description: t("reportHub.items.annualReports.description"), icon: FileText, keywords: ["annual", "yearly", "summary", "state"] },
        ],
      },
      {
        id: "board",
        title: t("reportHub.categories.board"),
        icon: Building2,
        items: [
          { label: t("reportHub.items.boardReports.label"), to: "/board/reports", description: t("reportHub.items.boardReports.description"), icon: Building2, keywords: ["board", "governance", "trustee"] },
          { label: t("reportHub.items.boardReportTemplates.label"), to: "/board/reports/templates", description: t("reportHub.items.boardReportTemplates.description"), icon: FileText, keywords: ["board", "template", "report"] },
          { label: t("reportHub.items.boardReportSchedules.label"), to: "/board/reports/schedules", description: t("reportHub.items.boardReportSchedules.description"), icon: Calendar, keywords: ["board", "schedule", "automated"] },
        ],
      },
      {
        id: "strategic",
        title: t("reportHub.categories.strategic"),
        icon: TrendingUp,
        items: [
          { label: t("reportHub.items.strategicAnalytics.label"), to: "/staff/admin/strategic/analytics", description: t("reportHub.items.strategicAnalytics.description"), icon: TrendingUp, keywords: ["strategic", "kpi", "goal", "plan"] },
          { label: t("reportHub.items.analyticsDashboard.label"), to: "/staff/admin/analytics", description: t("reportHub.items.analyticsDashboard.description"), icon: BarChart3, keywords: ["analytics", "dashboard", "overview"] },
          { label: t("reportHub.items.staffAnalytics.label"), to: "/staff/analytics", description: t("reportHub.items.staffAnalytics.description"), icon: Activity, keywords: ["staff", "performance", "workload"] },
          { label: t("reportHub.items.schoolImpact.label"), to: "/staff/admin/school-impact", description: t("reportHub.items.schoolImpact.description"), icon: BookOpen, keywords: ["school", "impact", "literacy", "education"] },
          { label: t("reportHub.items.learningAnalytics.label"), to: "/learn/analytics", description: t("reportHub.items.learningAnalytics.description"), icon: GraduationCap, keywords: ["learning", "course", "literacy", "completion"] },
          { label: t("reportHub.items.websiteAnalytics.label"), to: "/staff/admin/website-analytics", description: t("reportHub.items.websiteAnalytics.description"), icon: Globe, keywords: ["website", "traffic", "seo", "public"] },
          { label: t("reportHub.items.qrPosterScans.label"), to: "/staff/qr-scans", description: t("reportHub.items.qrPosterScans.description"), icon: QrCode, keywords: ["qr", "poster", "scan", "sticker", "tracking", "physical"] },
          { label: t("reportHub.items.communityOutcomes.label"), to: "/staff/admin/community-outcomes", description: t("reportHub.items.communityOutcomes.description"), icon: HeartHandshake, keywords: ["community", "outcomes", "impact", "trends"] },
        ],
      },
    ],
    [t],
  );

  // Hide cards the current role can't open (they would bounce to /account).
  // Mirrors RequireAuth's role logic; categories with no remaining items drop.
  const visibleCategories = useMemo<HubCategory[]>(() => {
    const userRole = (user?.role || "patron").toLowerCase();
    const canAccess = (to: string): boolean => {
      const required = RESTRICTED_REPORT_PATHS[to.split("#")[0] ?? to];
      if (!required) return true;
      if (userRole === "super_admin") return true;
      return required.some((role) =>
        role === "board_member" ? !!user?.is_board_member : userRole === role,
      );
    };
    return categories
      .map((cat) => ({ ...cat, items: cat.items.filter((item) => canAccess(item.to)) }))
      .filter((cat) => cat.items.length > 0);
  }, [categories, user]);

  return (
    <>
      <NavigationHub
        title={t("reportHub.title")}
        icon={<BarChart3 className="w-7 h-7 text-lsc-rose" />}
        categories={visibleCategories}
        searchPlaceholder={t("reportHub.searchPlaceholder")}
        itemNoun={{
          singular: t("reportHub.itemNounSingular"),
          plural: t("reportHub.itemNounPlural"),
        }}
        favorites={{ hubSlug: REPORT_HUB_SLUG }}
        persistExpansion
        headerAction={
          <button
            type="button"
            onClick={() => setScheduleModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
          >
            <Calendar className="w-4 h-4" />
            {t("reportHub.scheduleReport")}
          </button>
        }
      />
      <ReportScheduleModal
        isOpen={scheduleModalOpen}
        onClose={() => setScheduleModalOpen(false)}
      />
    </>
  );
}
