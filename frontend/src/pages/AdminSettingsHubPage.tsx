/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react";
import {
  Settings,
  Cpu,
  BookOpen,
  Shield,
  BarChart3,
  Building2,
  Globe,
  Megaphone,
  Plug,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory, type HubItem } from "../components/navigation/NavigationHub";
import { useOrganizationFeatures, type OrganizationFeatures } from "../contexts/OrganizationFeaturesContext";

import HubShortcutsRail from "../components/navigation/HubShortcutsRail";
import { logHubVisit } from "../components/navigation/hubVisits";

// Admin settings whose route is gated behind an org feature flag (mirrors the
// RequireFeature wrappers in StaffRoutes.tsx). When a feature is off its route
// renders a "turned off" notice, so we hide the hub link to avoid sending staff
// to a dead end. Keep in sync with StaffRoutes.tsx.
const ADMIN_FEATURE_GATES: Record<string, keyof OrganizationFeatures> = {
  "/staff/admin/ai": "ai_tools_enabled",
  "/staff/admin/learning-paths": "learning_platform_enabled",
  "/staff/admin/courses": "learning_platform_enabled",
  "/staff/admin/sessions": "learning_platform_enabled",
  "/staff/admin/events": "events_enabled",
  "/staff/admin/reading-programs": "reading_programs_enabled",
  "/staff/admin/edi": "acquisition_enabled",
  "/staff/admin/acquisition": "acquisition_enabled",
  "/staff/admin/legal": "legal_services_enabled",
  "/staff/admin/compliance": "compliance_enabled",
  "/staff/admin/financial": "board_features_enabled",
  "/staff/admin/annual-reports": "board_features_enabled",
  "/staff/admin/board": "board_features_enabled",
  "/staff/admin/strategic": "board_features_enabled",
  "/staff/admin/treasurer": "financial_reports_enabled",
  "/staff/admin/home-delivery-settings": "home_delivery_enabled",
  "/staff/admin/migration-project": "migration_enabled",
  "/staff/admin/audiobooks": "streaming_enabled",
};

export default function AdminSettingsHubPage() {
  const { t } = useTranslation();
  const { isFeatureEnabled } = useOrganizationFeatures();

  const categories = useMemo<HubCategory[]>(
    () => {
      const all: HubCategory[] = [
      {
        id: "library-operations",
        title: t("adminSettingsHub.categories.libraryOperations"),
        icon: Building2,
        items: [
          { label: t("adminSettingsHub.items.circulationPolicy.label"), to: "/staff/admin/circulation-policy", description: t("adminSettingsHub.items.circulationPolicy.description") },
          { label: t("adminSettingsHub.items.libraryConfiguration.label"), to: "/staff/admin/library-config", description: t("adminSettingsHub.items.libraryConfiguration.description") },
          { label: t("adminSettingsHub.items.userManagement.label"), to: "/staff/admin/users", description: t("adminSettingsHub.items.userManagement.description") },
          { label: t("adminSettingsHub.items.staffManagement.label"), to: "/staff/admin/staff", description: t("adminSettingsHub.items.staffManagement.description") },
        ],
      },
      {
        id: "technology-ai",
        title: t("adminSettingsHub.categories.technologyAi"),
        icon: Cpu,
        items: [
          { label: t("adminSettingsHub.items.aiSettings.label"), to: "/staff/admin/ai", description: t("adminSettingsHub.items.aiSettings.description") },
          { label: t("adminSettingsHub.items.searchEngine.label"), to: "/staff/admin/search-engine", description: t("adminSettingsHub.items.searchEngine.description") },
        ],
      },
      {
        id: "outreach-communications",
        title: t("adminSettingsHub.categories.outreachCommunications"),
        icon: Megaphone,
        items: [
          { label: t("adminSettingsHub.items.outreachDashboard.label"), to: "/staff/admin/outreach", description: t("adminSettingsHub.items.outreachDashboard.description") },
          { label: t("adminSettingsHub.items.metaTags.label"), to: "/staff/admin/meta-tags", description: t("adminSettingsHub.items.metaTags.description") },
          { label: t("adminSettingsHub.items.socialSharing.label"), to: "/staff/admin/social-sharing", description: t("adminSettingsHub.items.socialSharing.description") },
          { label: t("adminSettingsHub.items.personalization.label"), to: "/staff/admin/personalization", description: t("adminSettingsHub.items.personalization.description") },
        ],
      },
      {
        id: "content-programs",
        title: t("adminSettingsHub.categories.contentPrograms"),
        icon: BookOpen,
        items: [
          { label: t("adminSettingsHub.items.learningPaths.label"), to: "/staff/admin/learning-paths", description: t("adminSettingsHub.items.learningPaths.description") },
          { label: t("adminSettingsHub.items.courses.label"), to: "/staff/admin/courses", description: t("adminSettingsHub.items.courses.description") },
          { label: t("adminSettingsHub.items.sessions.label"), to: "/staff/admin/sessions", description: t("adminSettingsHub.items.sessions.description") },
          { label: t("adminSettingsHub.items.events.label"), to: "/staff/admin/events", description: t("adminSettingsHub.items.events.description") },
          { label: t("adminSettingsHub.items.databases.label"), to: "/staff/admin/databases", description: t("adminSettingsHub.items.databases.description") },
          { label: t("adminSettingsHub.items.readingPrograms.label"), to: "/staff/admin/reading-programs", description: t("adminSettingsHub.items.readingPrograms.description") },
          { label: t("adminSettingsHub.items.ediSettings.label"), to: "/staff/admin/edi", description: t("adminSettingsHub.items.ediSettings.description") },
          { label: t("adminSettingsHub.items.legalResources.label"), to: "/staff/admin/legal", description: t("adminSettingsHub.items.legalResources.description") },
        ],
      },
      {
        id: "web-seo",
        title: t("adminSettingsHub.categories.webSeo"),
        icon: Globe,
        items: [
          { label: t("adminSettingsHub.items.aboutUsPage.label"), to: "/staff/admin/about", description: t("adminSettingsHub.items.aboutUsPage.description") },
          { label: t("adminSettingsHub.items.linkHealth.label"), to: "/staff/admin/link-health", description: t("adminSettingsHub.items.linkHealth.description") },
        ],
      },
      {
        id: "compliance-legal",
        title: t("adminSettingsHub.categories.complianceLegal"),
        icon: Shield,
        items: [
          { label: t("adminSettingsHub.items.complianceDashboard.label"), to: "/staff/admin/compliance", description: t("adminSettingsHub.items.complianceDashboard.description") },
          { label: t("adminSettingsHub.items.legalResources.label"), to: "/staff/admin/legal", description: t("adminSettingsHub.items.legalResources.description") },
        ],
      },
      {
        id: "analytics-reports",
        title: t("adminSettingsHub.categories.analyticsReports"),
        icon: BarChart3,
        items: [
          { label: t("adminSettingsHub.items.analyticsDashboard.label"), to: "/staff/admin/analytics", description: t("adminSettingsHub.items.analyticsDashboard.description") },
          { label: t("adminSettingsHub.items.financialReports.label"), to: "/staff/admin/financial", description: t("adminSettingsHub.items.financialReports.description") },
          { label: t("adminSettingsHub.items.annualReports.label"), to: "/staff/admin/annual-reports", description: t("adminSettingsHub.items.annualReports.description") },
        ],
      },
      {
        id: "board-finance",
        title: t("adminSettingsHub.categories.boardFinance"),
        icon: Settings,
        items: [
          { label: t("adminSettingsHub.items.boardManagement.label"), to: "/staff/admin/board", description: t("adminSettingsHub.items.boardManagement.description") },
          { label: t("adminSettingsHub.items.strategicPlanning.label"), to: "/staff/admin/strategic", description: t("adminSettingsHub.items.strategicPlanning.description") },
          { label: t("adminSettingsHub.items.treasury.label"), to: "/staff/admin/treasurer", description: t("adminSettingsHub.items.treasury.description") },
        ],
      },
      {
        id: "system-monitoring",
        title: t("adminSettingsHub.categories.systemMonitoring"),
        icon: Cpu,
        items: [
          { label: t("adminSettingsHub.items.systemDashboard.label"), to: "/staff/admin/system", description: t("adminSettingsHub.items.systemDashboard.description") },
          { label: t("adminSettingsHub.items.systemIntegrations.label"), to: "/staff/admin/integrations", description: t("adminSettingsHub.items.systemIntegrations.description") },
        ],
      },
      {
        id: "integrations",
        title: t("adminSettingsHub.categories.integrations"),
        icon: Plug,
        items: [
          { label: t("adminSettingsHub.items.sip2.label"), to: "/staff/admin/sip2", description: t("adminSettingsHub.items.sip2.description") },
          { label: t("adminSettingsHub.items.z3950.label"), to: "/staff/admin/z3950", description: t("adminSettingsHub.items.z3950.description") },
          { label: t("adminSettingsHub.items.edi.label"), to: "/staff/admin/edi", description: t("adminSettingsHub.items.edi.description") },
          { label: t("adminSettingsHub.items.acquisitions.label"), to: "/staff/admin/acquisition", description: t("adminSettingsHub.items.acquisitions.description") },
          { label: t("adminSettingsHub.items.homeDelivery.label"), to: "/staff/admin/home-delivery-settings", description: t("adminSettingsHub.items.homeDelivery.description") },
          { label: t("adminSettingsHub.items.libraryMigration.label"), to: "/staff/admin/migration-project", description: t("adminSettingsHub.items.libraryMigration.description") },
          { label: t("adminSettingsHub.items.audiobooks.label"), to: "/staff/admin/audiobooks", description: t("adminSettingsHub.items.audiobooks.description") },
        ],
      },
      {
        id: "offboarding",
        title: t("adminSettingsHub.categories.offboarding"),
        icon: Shield,
        items: [
          { label: t("adminSettingsHub.items.dataExport.label"), to: "/staff/admin/data-export", description: t("adminSettingsHub.items.dataExport.description") },
        ],
      },
      ];
      // Hide links whose feature flag is off so staff don't hit a dead end;
      // drop any category left empty. isFeatureEnabled returns true while
      // features are still loading, so nothing flickers out then back in.
      return all
        .map((category) => ({
          ...category,
          items: category.items.filter((item) => {
            const gate = ADMIN_FEATURE_GATES[item.to];
            return !gate || isFeatureEnabled(gate);
          }),
        }))
        .filter((category) => category.items.length > 0);
    },
    [t, isFeatureEnabled],
  );

  return (
    <NavigationHub
      title={t("adminSettingsHub.title")}
      icon={<Settings className="w-7 h-7 text-lsc-rose" />}
      categories={categories}
      searchPlaceholder={t("placeholder.adminSettingsHub.searchSettings")}
      columns={3}
      itemNoun={{ singular: t("adminSettingsHub.itemNounSingular"), plural: t("adminSettingsHub.itemNounPlural") }}
      favorites={{ hubSlug: "admin-settings-hub" }}
      persistExpansion
      showStatChips
      hubSlug="admin-settings-hub"
      onItemClick={(item: HubItem) => logHubVisit("admin-settings-hub", item.to)}
      beforeGrid={<HubShortcutsRail hubSlug="admin-settings-hub" />}
    />
  );
}
