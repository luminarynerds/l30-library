/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react";
import {
  Library,
  BookPlus, ShoppingCart, Package, ScanLine, History, Newspaper,
  ListChecks, BookMarked, LayoutTemplate, ClipboardCheck, Leaf, Wrench,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory, type HubItem } from "../components/navigation/NavigationHub";
import HubShortcutsRail from "../components/navigation/HubShortcutsRail";
import { logHubVisit } from "../components/navigation/hubVisits";
import UnifiedCollectionSearch from "../components/collection/UnifiedCollectionSearch";

export default function CollectionHubPage() {
  const { t } = useTranslation();

  const categories = useMemo<HubCategory[]>(
    () => [
      {
        id: "catalog",
        title: t("collectionHub.categories.catalog"),
        icon: Library,
        items: [
          { label: t("collectionHub.items.cataloging.label"), to: "/staff/cataloging", description: t("collectionHub.items.cataloging.description"), icon: BookPlus },
          { label: t("collectionHub.items.acquisitions.label"), to: "/staff/acquisition", description: t("collectionHub.items.acquisitions.description"), icon: ShoppingCart, featureFlag: "acquisition_enabled" },
          { label: t("collectionHub.items.inventory.label"), to: "/staff/inventory", description: t("collectionHub.items.inventory.description"), icon: Package },
          { label: t("collectionHub.items.shelfReading.label"), to: "/staff/shelf-reading", description: t("collectionHub.items.shelfReading.description"), icon: ScanLine },
          { label: t("collectionHub.items.itemLifecycle.label"), to: "/staff/lifecycle", description: t("collectionHub.items.itemLifecycle.description"), icon: History },
          { label: t("collectionHub.items.serials.label"), to: "/staff/admin/serials", description: t("collectionHub.items.serials.description"), icon: Newspaper, featureFlag: "serials_enabled" },
        ],
      },
      {
        id: "management",
        title: t("collectionHub.categories.management"),
        icon: Library,
        items: [
          { label: t("collectionHub.items.staffPicks.label"), to: "/staff/picks", description: t("collectionHub.items.staffPicks.description"), icon: ListChecks },
          { label: t("collectionHub.items.readingLists.label"), to: "/staff/reading-lists", description: t("collectionHub.items.readingLists.description"), icon: BookMarked },
          { label: t("collectionHub.items.homePage.label"), to: "/staff/home-page", description: t("collectionHub.items.homePage.description"), icon: LayoutTemplate },
          { label: t("collectionHub.items.processingQueue.label"), to: "/staff/processing", description: t("collectionHub.items.processingQueue.description"), icon: ClipboardCheck, featureFlag: "processing_queue_enabled" },
          { label: t("collectionHub.items.weeding.label"), to: "/staff/weeding", description: t("collectionHub.items.weeding.description"), icon: Leaf },
          { label: t("collectionHub.items.repairQueue.label"), to: "/staff/repair-queue", description: t("collectionHub.items.repairQueue.description"), icon: Wrench },
        ],
      },
    ],
    [t],
  );

  return (
    <NavigationHub
      title={t("collectionHub.title")}
      icon={<Library className="w-7 h-7 text-lsc-rose" />}
      categories={categories}
      beforeGrid={
        <>
          <UnifiedCollectionSearch />
          <HubShortcutsRail hubSlug="collection-hub" />
        </>
      }
      favorites={{ hubSlug: "collection-hub" }}
      persistExpansion
      showStatChips
      hubSlug="collection-hub"
      onItemClick={(item: HubItem) => logHubVisit("collection-hub", item.to)}
    />
  );
}
