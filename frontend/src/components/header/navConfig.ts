/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Declarative navigation configuration for the desktop header.
 *
 * The previous implementation kept several `useMemo` blocks inside Layout.tsx
 * that interleaved feature-flag checks with translation calls. That made the
 * nav structure hard to reason about and impossible to test independently.
 *
 * `getNavConfig` is a pure function that takes the runtime dependencies
 * (`t`, `isFeatureEnabled`, `role`) and returns a fully-resolved list of
 * `NavGroup`s ready for the render layer. Group-/section-level `flag` and
 * `role` gates are honored here; the render layer simply iterates and draws.
 */
import {
  CreditCard,
  Truck,
  DoorOpen,
  Monitor,
  ShoppingCart,
  PhoneIcon,
  MessageCircle,
  Scale,
  Laptop,
  Gavel,
  MapPin,
  FileText,
  BookOpen,
  Compass,
  Bookmark,
  Sparkles,
  GraduationCap,
  Home,
  Feather,
  BookOpenCheck,
  ListChecks,
  Award,
  MessageCircleQuestion,
  Users,
  Calendar,
  BookMarked,
  LibraryBig,
} from 'lucide-react'

type IconComponent = React.ElementType

export interface NavItem {
  to: string
  label: string
  icon: IconComponent
  description?: string
  /**
   * Optional W3C aria-keyshortcuts value (space-separated keys per spec,
   * e.g. `"g c"`). Announced by screen readers; does NOT bind the shortcut
   * — the keydown handler in Layout.tsx remains the binding owner.
   *
   * Currently unused at the call site: the existing `g`-prefix chords
   * (`g c/h/p/r`) target `/staff/*` routes which are not yet part of the
   * patron nav config. Threaded through the render layer so populating
   * future items is a one-line change.
   */
  shortcut?: string
}

export interface NavSection {
  key: string
  heading: string
  items: NavItem[]
}

export interface NavGroup {
  key: string
  label: string
  icon: IconComponent
  align?: 'left' | 'right' | 'center'
  sections: NavSection[]
}

export interface GetNavConfigDeps {
  t: (key: string, fallback?: string) => string
  // Accept any narrower flag-key type; we treat flags as opaque strings here.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  isFeatureEnabled: (flag: any) => boolean
  role?: string | null | undefined
  isAuthenticated?: boolean | undefined
}

export function getNavConfig({
  t,
  isFeatureEnabled,
  role,
  isAuthenticated,
}: GetNavConfigDeps): NavGroup[] {
  const groups: NavGroup[] = []

  // 1. Services — what can the library do for me?
  const servicesSections: NavSection[] = [
    {
      key: 'library-services',
      heading: t('navigation.libraryServices'),
      items: [
        ...(isFeatureEnabled('front_desk_enabled') ? [{ to: '/get-started', label: t('navigation.getALibraryCard'), icon: CreditCard, description: t('navigation.getALibraryCardDesc') }] : []),
        ...(isFeatureEnabled('home_delivery_enabled') ? [{ to: '/home-delivery', label: t('navigation.homeDelivery'), icon: Truck, description: t('navigation.homeDeliveryDesc') }] : []),
        ...(isFeatureEnabled('meeting_rooms_enabled') ? [{ to: '/rooms', label: t('navigation.reserveARoom'), icon: DoorOpen, description: t('navigation.reserveARoomDesc') }] : []),
        ...(isFeatureEnabled('tech_services_enabled') ? [{ to: '/computers', label: t('navigation.reserveAComputer', 'Reserve a Computer'), icon: Monitor, description: t('navigation.reserveAComputerDesc', 'Book a session on a public-use computer') }] : []),
        { to: '/suggest-purchase', label: t('navigation.suggestPurchase'), icon: ShoppingCart, description: t('navigation.suggestPurchaseDesc') },
      ],
    },
    {
      key: 'help-and-support',
      heading: t('navigation.helpAndSupport'),
      items: [
        { to: '/contact', label: t('navigation.contactUs'), icon: PhoneIcon, description: t('navigation.contactUsDesc') },
        { to: '/get-help', label: t('navigation.getHelp'), icon: MessageCircle, description: t('components.layout.chatEmailOrCallFor') },
        ...(isFeatureEnabled('legal_services_enabled') ? [{ to: '/legal', label: t('navigation.legalHelp', 'Legal Help'), icon: Scale, description: t('navigation.legalHelpDesc', 'Free legal resources, forms, and aid connections') }] : []),
        { to: '/tech', label: t('navigation.techSupport'), icon: Laptop, description: t('navigation.techSupportDesc') },
      ],
    },
    {
      key: 'in-the-building',
      heading: t('navigation.inTheBuilding', 'In the building'),
      items: [
        ...(isFeatureEnabled('board_features_enabled') ? [{ to: '/board/meetings', label: t('navigation.boardAndGovernance'), icon: Gavel, description: t('navigation.boardAndGovernanceDesc') }] : []),
        { to: '/branches', label: t('navigation.hoursAndLocations'), icon: MapPin, description: t('navigation.hoursAndLocationsDesc') },
      ],
    },
  ]
  const filteredServices = servicesSections.filter(s => s.items.length > 0)
  if (filteredServices.length > 0) {
    groups.push({
      key: 'services',
      label: t('navigation.services'),
      icon: Compass,
      align: 'left',
      sections: filteredServices,
    })
  }

  // 2. Explore — browse, discover, learn
  const exploreSections: NavSection[] = [
    {
      key: 'read-and-discover',
      heading: t('navigation.exploreReadAndDiscover'),
      items: [
        ...(isFeatureEnabled('community_features_enabled') ? [{ to: '/blog', label: t('navigation.blog', 'Blog'), icon: FileText, description: t('navigation.blogDesc', 'Insights on library technology and digital literacy') }] : []),
        ...(isFeatureEnabled('book_clubs_enabled') ? [{ to: '/book-clubs', label: t('navigation.bookClubs'), icon: BookOpen, description: t('navigation.bookClubsDesc') }] : []),
        ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/digital', label: t('navigation.digitalResources'), icon: Monitor, description: t('navigation.digitalResourcesDesc') }] : []),
        ...(isFeatureEnabled('collection_management_enabled') ? [{ to: '/discover', label: t('navigation.discover', 'Discover'), icon: Compass, description: t('navigation.discoverDesc', 'Staff picks, new arrivals, and what your neighbors are reading') }] : []),
        { to: '/picks', label: t('navigation.curatedPicks', 'Curated picks'), icon: Sparkles, description: t('navigation.curatedPicksDesc', 'The newest staff-curated reading recommendations') },
        { to: '/coming-soon', label: t('navigation.comingSoon', 'Coming Soon'), icon: Calendar, description: t('navigation.comingSoonDesc', 'Forthcoming titles arriving at the library') },
        ...(isFeatureEnabled('reading_programs_enabled') ? [{ to: '/programs', label: t('navigation.readingPrograms'), icon: Bookmark, description: t('navigation.readingProgramsDesc') }] : []),
        { to: '/catalog/partner-search', label: t('navigation.partnerSearch', 'Partner libraries'), icon: LibraryBig, description: t('navigation.partnerSearchDesc', 'Search Library of Congress and partner collections when our catalog comes up short') },
      ],
    },
    {
      key: 'learn-and-create',
      heading: t('navigation.exploreLearnAndCreate'),
      items: [
        ...(isFeatureEnabled('ai_tools_enabled') ? [{ to: '/ai', label: t('navigation.aiTools'), icon: Sparkles, description: t('navigation.aiToolsDesc') }] : []),
        ...(isFeatureEnabled('banned_books_tracking_enabled') ? [{ to: '/banned-books', label: t('navigation.intellectualFreedom'), icon: Scale, description: t('navigation.intellectualFreedomDesc') }] : []),
        ...(isFeatureEnabled('learning_platform_enabled') ? [{ to: '/learn', label: t('navigation.learningAndClasses'), icon: GraduationCap, description: t('navigation.learningAndClassesDesc') }] : []),
        ...(isFeatureEnabled('indie_platform_enabled') ? [{ to: '/indie', label: t('navigation.localAuthors'), icon: Feather, description: t('navigation.localAuthorsDesc') }] : []),
      ],
    },
  ]
  const filteredExplore = exploreSections.filter(s => s.items.length > 0)
  if (filteredExplore.length > 0) {
    groups.push({
      key: 'explore',
      label: t('navigation.explore'),
      icon: BookMarked,
      align: 'center',
      sections: filteredExplore,
    })
  }

  // 3. For Teachers — patron-side teacher portal, auth + feature gated
  const showTeacherNav = Boolean(isAuthenticated) && isFeatureEnabled('for_teachers_enabled')
  if (showTeacherNav) {
    groups.push({
      key: 'teachers',
      label: t('navigation.forTeachers'),
      icon: GraduationCap,
      align: 'center',
      sections: [
        {
          key: 'for-teachers',
          heading: t('navigation.forTeachers'),
          items: [
            { to: '/teacher', label: t('navigation.teacherHome'), icon: Home, description: t('navigation.teacherHomeDesc') },
            { to: '/teacher/reading-dashboard', label: t('navigation.teacherReadingDashboard'), icon: BookOpenCheck, description: t('navigation.teacherReadingDashboardDesc') },
            { to: '/teacher/reading-lists', label: t('navigation.teacherReadingLists'), icon: ListChecks, description: t('navigation.teacherReadingListsDesc') },
            { to: '/teacher/professional-development', label: t('navigation.professionalDevelopment'), icon: Award, description: t('navigation.professionalDevelopmentDesc') },
            { to: '/teacher/library-consultations', label: t('navigation.librarianConsultations'), icon: MessageCircleQuestion, description: t('navigation.librarianConsultationsDesc') },
            { to: '/teacher/family-challenges', label: t('navigation.familyReadingChallenges'), icon: Users, description: t('navigation.familyReadingChallengesDesc') },
            { to: '/teacher/library-visits', label: t('navigation.libraryVisitScheduling'), icon: Calendar, description: t('navigation.libraryVisitSchedulingDesc') },
          ],
        },
      ],
    })
  }

  // `role` is reserved for future role-gated groups (e.g. staff-only entries).
  // Currently no group is role-gated at this layer; keep the param wired so
  // additions don't require a signature change.
  void role

  return groups
}
