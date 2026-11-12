/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react";
import {
  Heart,
  Calendar,
  BookMarked,
  MessageSquare,
  BookOpen,
  ClipboardCheck,
  Handshake,
  Award,
  Home,
  ArrowRightLeft,
  Package,
  DoorOpen,
  Scale,
  GraduationCap,
  Target,
  ScrollText,
  Clock,
  Users,
  Building2,
} from "lucide-react";
import { useTranslation } from "@/i18n";
import NavigationHub, { type HubCategory, type HubItem } from "../components/navigation/NavigationHub";
import HubStatusStrip from "../components/navigation/HubStatusStrip";
import HubShortcutsRail from "../components/navigation/HubShortcutsRail";
import { logHubVisit } from "../components/navigation/hubVisits";

export default function LibraryHubPage() {
  const { t } = useTranslation();

  const categories = useMemo<HubCategory[]>(
    () => [
      {
        id: "programs",
        title: t("libraryHub.categories.programs"),
        icon: Heart,
        items: [
          { label: t("libraryHub.items.events.label"), to: "/staff/events", description: t("libraryHub.items.events.description"), icon: Calendar, featureFlag: "events_enabled" },
          { label: t("libraryHub.items.readingPrograms.label"), to: "/staff/admin/reading-programs", description: t("libraryHub.items.readingPrograms.description"), icon: BookMarked, featureFlag: "reading_programs_enabled" },
          { label: t("libraryHub.items.authorAmas.label"), to: "/staff/admin/amas", description: t("libraryHub.items.authorAmas.description"), icon: MessageSquare, featureFlag: "ama_enabled" },
          { label: t("libraryHub.items.bookClubs.label"), to: "/staff/admin/book-clubs", description: t("libraryHub.items.bookClubs.description"), icon: BookOpen, featureFlag: "book_clubs_enabled" },
          { label: t("libraryHub.items.storytime.label"), to: "/staff/storytime", description: t("libraryHub.items.storytime.description"), icon: BookOpen, featureFlag: "storytime_enabled" },
          { label: t("libraryHub.items.programPlanning.label"), to: "/staff/program-planning", description: t("libraryHub.items.programPlanning.description"), icon: ClipboardCheck, featureFlag: "events_enabled" },
          { label: t("libraryHub.items.partnershipTiers.label"), to: "/staff/admin/partnership-tiers", description: t("libraryHub.items.partnershipTiers.description"), icon: Handshake, featureFlag: "reading_programs_enabled" },
          { label: t("libraryHub.items.readingAmbassadors.label"), to: "/staff/admin/reading-ambassadors", description: t("libraryHub.items.readingAmbassadors.description"), icon: Award, featureFlag: "reading_programs_enabled" },
          { label: t("libraryHub.items.readingBundles.label"), to: "/staff/admin/reading-bundles", description: t("libraryHub.items.readingBundles.description"), icon: BookOpen, featureFlag: "reading_programs_enabled" },
          { label: t("libraryHub.items.eventManagement.label"), to: "/staff/admin/events", description: t("libraryHub.items.eventManagement.description"), icon: Calendar, featureFlag: "events_enabled" },
        ],
      },
      {
        id: "services",
        title: t("libraryHub.categories.services"),
        icon: Heart,
        items: [
          { label: t("libraryHub.items.homeDelivery.label"), to: "/staff/home-delivery", description: t("libraryHub.items.homeDelivery.description"), icon: Home, featureFlag: "home_delivery_enabled" },
          { label: t("libraryHub.items.interlibraryLoan.label"), to: "/staff/interlibrary-loan", description: t("libraryHub.items.interlibraryLoan.description"), icon: ArrowRightLeft, featureFlag: "ill_enabled" },
          { label: t("libraryHub.items.makerspace.label"), to: "/staff/makerspace", description: t("libraryHub.items.makerspace.description"), icon: Package, featureFlag: "makerspace_enabled" },
          { label: t("libraryHub.items.rooms.label"), to: "/staff/rooms", description: t("libraryHub.items.rooms.description"), icon: DoorOpen, featureFlag: "meeting_rooms_enabled" },
          { label: t("libraryHub.items.legalHelp.label"), to: "/staff/admin/legal", description: t("libraryHub.items.legalHelp.description"), icon: Scale, featureFlag: "legal_services_enabled" },
          { label: t("libraryHub.items.volunteers.label"), to: "/staff/volunteers", description: t("libraryHub.items.volunteers.description"), icon: Users, featureFlag: "volunteers_enabled" },
          { label: t("libraryHub.items.branchClosures.label"), to: "/staff/branch-closures", description: t("libraryHub.items.branchClosures.description"), icon: Building2 },
        ],
      },
      {
        id: "team",
        title: t("libraryHub.categories.team"),
        icon: Heart,
        items: [
          { label: t("libraryHub.items.training.label"), to: "/staff/training", description: t("libraryHub.items.training.description"), icon: GraduationCap, featureFlag: "training_modules_enabled" },
          { label: t("libraryHub.items.myGoals.label"), to: "/staff/strategic", description: t("libraryHub.items.myGoals.description"), icon: Target, featureFlag: "board_features_enabled" },
          { label: t("libraryHub.items.messageBoard.label"), to: "/staff/message-board", description: t("libraryHub.items.messageBoard.description"), icon: ScrollText, featureFlag: "staff_wellness_enabled" },
          { label: t("libraryHub.items.shiftSwap.label"), to: "/staff/shift-swap", description: t("libraryHub.items.shiftSwap.description"), icon: Clock, featureFlag: "staff_scheduling_enabled" },
        ],
      },
      {
        id: "learning-platform",
        title: t("libraryHub.categories.learningPlatform"),
        icon: Heart,
        items: [
          { label: t("libraryHub.items.learningPaths.label"), to: "/staff/admin/learning-paths", description: t("libraryHub.items.learningPaths.description"), icon: GraduationCap, featureFlag: "learning_platform_enabled" },
          { label: t("libraryHub.items.courses.label"), to: "/staff/admin/courses", description: t("libraryHub.items.courses.description"), icon: BookOpen, featureFlag: "learning_platform_enabled" },
          { label: t("libraryHub.items.sessions.label"), to: "/staff/admin/sessions", description: t("libraryHub.items.sessions.description"), icon: Clock, featureFlag: "learning_platform_enabled" },
        ],
      },
    ],
    [t],
  );

  return (
    <NavigationHub
      title={t("libraryHub.title")}
      icon={<Heart className="w-7 h-7 text-lsc-rose" />}
      categories={categories}
      searchPlaceholder={t("libraryHub.searchPlaceholder")}
      favorites={{ hubSlug: "library-hub" }}
      persistExpansion
      showStatChips
      hubSlug="library-hub"
      onItemClick={(item: HubItem) => logHubVisit("library-hub", item.to)}
      beforeGrid={
        <>
          <HubStatusStrip hubSlug="library-hub" className="mb-2" />
          <HubShortcutsRail hubSlug="library-hub" />
        </>
      }
    />
  );
}
