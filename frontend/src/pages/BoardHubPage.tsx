/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react";
import {
  Building2,
  Users,
  Calendar,
  ScrollText,
  Gavel,
  FileText,
  MessageSquare,
  Wallet,
  Target,
  ClipboardCheck,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory, type HubItem } from "../components/navigation/NavigationHub";

import HubShortcutsRail from "../components/navigation/HubShortcutsRail";
import { logHubVisit } from "../components/navigation/hubVisits";
export default function BoardHubPage() {
  const { t } = useTranslation();

  const categories = useMemo<HubCategory[]>(
    () => [
      {
        id: "public-governance",
        title: t("boardHub.categories.publicGovernance"),
        icon: Building2,
        items: [
          { label: t("boardHub.items.members.label"), to: "/board/members", description: t("boardHub.items.members.description"), icon: Users },
          { label: t("boardHub.items.meetings.label"), to: "/board/meetings", description: t("boardHub.items.meetings.description"), icon: Calendar },
          { label: t("boardHub.items.minutes.label"), to: "/board/minutes", description: t("boardHub.items.minutes.description"), icon: ScrollText },
          { label: t("boardHub.items.motions.label"), to: "/board/motions", description: t("boardHub.items.motions.description"), icon: Gavel },
          { label: t("boardHub.items.committees.label"), to: "/board/committees", description: t("boardHub.items.committees.description"), icon: Building2 },
          { label: t("boardHub.items.documents.label"), to: "/board/documents", description: t("boardHub.items.documents.description"), icon: FileText },
          { label: t("boardHub.items.publicComments.label"), to: "/board/public-comments", description: t("boardHub.items.publicComments.description"), icon: MessageSquare },
        ],
      },
      {
        id: "administration",
        title: t("boardHub.categories.administration"),
        icon: Building2,
        items: [
          { label: t("boardHub.items.boardManagement.label"), to: "/staff/admin/board", description: t("boardHub.items.boardManagement.description"), icon: Building2 },
          { label: t("boardHub.items.treasurer.label"), to: "/staff/admin/board-treasurer", description: t("boardHub.items.treasurer.description"), icon: Wallet },
          { label: t("boardHub.items.strategicPlanning.label"), to: "/staff/admin/strategic", description: t("boardHub.items.strategicPlanning.description"), icon: Target },
          { label: t("boardHub.items.financialReports.label"), to: "/staff/admin/financial", description: t("boardHub.items.financialReports.description"), icon: FileText },
          { label: t("boardHub.items.annualReports.label"), to: "/staff/admin/annual-reports", description: t("boardHub.items.annualReports.description"), icon: FileText },
        ],
      },
      {
        id: "reports",
        title: t("boardHub.categories.reports"),
        icon: Building2,
        items: [
          { label: t("boardHub.items.reportGenerator.label"), to: "/board/reports", description: t("boardHub.items.reportGenerator.description"), icon: ClipboardCheck },
          { label: t("boardHub.items.templates.label"), to: "/board/reports/templates", description: t("boardHub.items.templates.description"), icon: FileText },
          { label: t("boardHub.items.schedules.label"), to: "/board/reports/schedules", description: t("boardHub.items.schedules.description"), icon: Calendar },
        ],
      },
    ],
    [t],
  );

  return (
    <NavigationHub
      title={t("boardHub.title")}
      icon={<Building2 className="w-7 h-7 text-lsc-rose" />}
      categories={categories}
      searchPlaceholder={t("boardHub.searchPlaceholder")}
      columns={3}
      favorites={{ hubSlug: "board-hub" }}
      persistExpansion
      showStatChips
      hubSlug="board-hub"
      onItemClick={(item: HubItem) => logHubVisit("board-hub", item.to)}
      beforeGrid={<HubShortcutsRail hubSlug="board-hub" />}
    />
  );
}
