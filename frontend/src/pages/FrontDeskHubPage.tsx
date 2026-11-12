/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react";
import {
  Zap,
  ArrowRightLeft, Users, Package, Wallet, FileText, Shield,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory, type HubItem } from "../components/navigation/NavigationHub";

import HubShortcutsRail from "../components/navigation/HubShortcutsRail";
import { logHubVisit } from "../components/navigation/hubVisits";
export default function FrontDeskHubPage() {
  const { t } = useTranslation();

  const categories = useMemo<HubCategory[]>(
    () => [
      {
        id: "circulation",
        title: t("frontDeskHub.categories.circulation"),
        icon: Zap,
        items: [
          { label: t("frontDeskHub.items.circulation.label"), to: "/staff/circulation", description: t("frontDeskHub.items.circulation.description"), icon: ArrowRightLeft },
          { label: t("frontDeskHub.items.fastCheckout.label"), to: "/staff/checkout/streamlined", description: t("frontDeskHub.items.fastCheckout.description"), icon: Zap },
          { label: t("frontDeskHub.items.patrons.label"), to: "/staff/patrons", description: t("frontDeskHub.items.patrons.description"), icon: Users },
          { label: t("frontDeskHub.items.holdsShelf.label"), to: "/staff/holds/shelf", description: t("frontDeskHub.items.holdsShelf.description"), icon: Package },
          { label: t("frontDeskHub.items.bookDrop.label"), to: "/staff/book-drop", description: t("frontDeskHub.items.bookDrop.description"), icon: ArrowRightLeft },
        ],
      },
      {
        id: "operations",
        title: t("frontDeskHub.categories.operations"),
        icon: Zap,
        items: [
          { label: t("frontDeskHub.items.cashDrawer.label"), to: "/staff/cash-drawer", description: t("frontDeskHub.items.cashDrawer.description"), icon: Wallet },
          { label: t("frontDeskHub.items.blog.label"), to: "/staff/blog", description: t("frontDeskHub.items.blog.description"), icon: FileText },
          { label: t("frontDeskHub.items.lostAndFound.label"), to: "/staff/found-items", description: t("frontDeskHub.items.lostAndFound.description"), icon: Package },
          { label: t("frontDeskHub.items.panicAlert.label"), to: "/staff/panic-alerts", description: t("frontDeskHub.items.panicAlert.description"), icon: Shield, featureFlag: "emergency_services_enabled" },
        ],
      },
    ],
    [t],
  );

  return (
    <NavigationHub
      title={t("frontDeskHub.title")}
      icon={<Zap className="w-7 h-7 text-lsc-rose" />}
      categories={categories}
      searchPlaceholder={t("frontDeskHub.searchPlaceholder")}
      itemNoun={{ singular: t("frontDeskHub.itemNounSingular"), plural: t("frontDeskHub.itemNounPlural") }}
      favorites={{ hubSlug: "front-desk-hub" }}
      persistExpansion
      showStatChips
      hubSlug="front-desk-hub"
      onItemClick={(item: HubItem) => logHubVisit("front-desk-hub", item.to)}
      beforeGrid={<HubShortcutsRail hubSlug="front-desk-hub" />}
    />
  );
}
