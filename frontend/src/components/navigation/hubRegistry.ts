/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Cross-hub item registry.
 *
 * Aggregates every NavigationHub item from the 5 migrated hub pages
 * (Library, Collection, Front Desk, Board, Admin Settings) into a single
 * indexed view so the command palette can search across all hubs without
 * the user having to remember which hub a task lives in.
 *
 * Design choice: option (b) -- categories live here, not on each hub page.
 * The parallel hub-i18n branch has already refactored every hub page to
 * useMemo its categories inline with t() calls, which would have collided
 * with option (a)'s named-export refactor. Centralizing here is also a
 * cleaner long-term source of truth; a follow-up PR can refactor hub
 * pages to consume getHubCategories(hubSlug, ...).
 */
import type { OrganizationFeatures } from '../../contexts/OrganizationFeaturesContext'
import type { User } from '../../api/domains/auth/auth-api'

export type UserRole = User['role']

export interface HubItemEntry {
  /** Stable slug for the hub (used for grouping/dedup). */
  hubSlug: string
  /** User-facing hub label (e.g. "Library Hub"). */
  hubLabel: string
  /** Stable id of the category within the hub. */
  categoryId: string
  /** User-facing category title. */
  categoryTitle: string
  /** User-facing item label. */
  itemLabel: string
  /** Optional descriptive blurb. */
  itemDescription?: string
  /** Target route. */
  itemPath: string
  /** OrganizationFeatures flag the item is gated behind. */
  featureFlag?: keyof OrganizationFeatures
  /** Roles allowed to see this item; undefined => allowed for any staff role. */
  roleAllowList?: UserRole[]
}

interface RawItem {
  label: string
  description?: string
  to: string
  featureFlag?: keyof OrganizationFeatures
  roleAllowList?: UserRole[]
}

interface RawCategory {
  id: string
  title: string
  items: RawItem[]
}

interface RawHub {
  slug: string
  label: string
  categories: RawCategory[]
}

// Mirrors the inline configs in the 5 hub pages. When the hub-i18n branch
// lands, the literal strings here become t() keys (e.g.
// libraryHub.categories.programs / libraryHub.items.events.label).
// Keep paths in sync with each *HubPage.tsx -- this list is the source of
// truth for the cross-hub command palette only; the per-hub render still
// reads its own inline categories until a follow-up consolidation.
const RAW_HUBS: RawHub[] = [
  {
    slug: 'library-hub',
    label: 'Programs',
    categories: [
      {
        id: 'programs',
        title: 'Programs',
        items: [
          { label: 'Events', to: '/staff/events', description: 'Browse and manage library events', featureFlag: 'events_enabled' },
          { label: 'Reading Programs', to: '/staff/admin/reading-programs', description: 'Reading challenges and tracking', featureFlag: 'reading_programs_enabled' },
          { label: 'Author AMAs', to: '/staff/admin/amas', description: 'Author Q&A sessions', featureFlag: 'ama_enabled' },
          { label: 'Book Clubs', to: '/staff/admin/book-clubs', description: 'Club management and scheduling', featureFlag: 'book_clubs_enabled' },
          { label: 'Storytime', to: '/staff/storytime', description: 'Storytime sessions and planning', featureFlag: 'storytime_enabled' },
          { label: 'Program Planning', to: '/staff/program-planning', description: 'Plan and coordinate programs', featureFlag: 'events_enabled' },
          { label: 'Partnership Tiers', to: '/staff/admin/partnership-tiers', description: 'Community partner levels', featureFlag: 'reading_programs_enabled' },
          { label: 'Reading Ambassadors', to: '/staff/admin/reading-ambassadors', description: 'Volunteer reader program', featureFlag: 'reading_programs_enabled' },
          { label: 'Reading Bundles', to: '/staff/admin/reading-bundles', description: 'Curated book bundles', featureFlag: 'reading_programs_enabled' },
          { label: 'Event Management', to: '/staff/admin/events', description: 'Admin event configuration', featureFlag: 'events_enabled' },
        ],
      },
      {
        id: 'services',
        title: 'Services',
        items: [
          { label: 'Home Delivery', to: '/staff/home-delivery', description: 'Homebound patron delivery service', featureFlag: 'home_delivery_enabled' },
          { label: 'Interlibrary Loan', to: '/staff/interlibrary-loan', description: 'Borrow and lend between libraries', featureFlag: 'ill_enabled' },
          { label: 'Makerspace', to: '/staff/makerspace', description: 'Equipment and workshop scheduling', featureFlag: 'makerspace_enabled' },
          { label: 'Rooms', to: '/staff/rooms', description: 'Meeting room reservations', featureFlag: 'meeting_rooms_enabled' },
          { label: 'Legal Help', to: '/staff/admin/legal', description: 'Legal aid clinics and resources', featureFlag: 'legal_services_enabled' },
          { label: 'Volunteers', to: '/staff/volunteers', description: 'Volunteer applications, roster, shifts, and hour logs', featureFlag: 'volunteers_enabled' },
        ],
      },
      {
        id: 'team',
        title: 'Team',
        items: [
          { label: 'Training', to: '/staff/training', description: 'Staff training modules', featureFlag: 'training_modules_enabled' },
          { label: 'My Goals', to: '/staff/strategic', description: 'Personal strategic goals', featureFlag: 'board_features_enabled' },
          { label: 'Message Board', to: '/staff/message-board', description: 'Internal staff communication', featureFlag: 'staff_wellness_enabled' },
          { label: 'Shift Swap', to: '/staff/shift-swap', description: 'Trade shifts with colleagues', featureFlag: 'staff_scheduling_enabled' },
        ],
      },
      {
        id: 'learning-platform',
        title: 'Learning Platform',
        items: [
          { label: 'Learning Paths', to: '/staff/admin/learning-paths', description: 'Guided learning sequences', featureFlag: 'learning_platform_enabled' },
          { label: 'Courses', to: '/staff/admin/courses', description: 'Course catalog management', featureFlag: 'learning_platform_enabled' },
          { label: 'Sessions', to: '/staff/admin/sessions', description: 'Schedule learning sessions', featureFlag: 'learning_platform_enabled' },
        ],
      },
    ],
  },
  {
    slug: 'collection-hub',
    label: 'Collection Hub',
    categories: [
      {
        id: 'catalog',
        title: 'Catalog',
        items: [
          { label: 'Cataloging', to: '/staff/cataloging', description: 'Create and edit bibliographic records' },
          { label: 'Acquisitions', to: '/staff/acquisition', description: 'Vendors, funds, and purchase orders', featureFlag: 'acquisition_enabled' },
          { label: 'Inventory', to: '/staff/inventory', description: 'Barcode scanning and inventory counts' },
          { label: 'Shelf Reading', to: '/staff/shelf-reading', description: 'Verify shelf order accuracy' },
          { label: 'Item Lifecycle', to: '/staff/lifecycle', description: 'Track items from acquisition to withdrawal' },
          { label: 'Serials', to: '/staff/admin/serials', description: 'Magazine and journal subscriptions', featureFlag: 'serials_enabled' },
        ],
      },
      {
        id: 'management',
        title: 'Management',
        items: [
          { label: 'Staff Picks', to: '/staff/picks', description: 'Curate staff recommendation displays' },
          { label: 'Reading Lists', to: '/staff/reading-lists', description: 'Themed reading lists for patrons' },
          { label: 'Home Page', to: '/staff/home-page', description: 'Hero pick and book shelves on the public home page', roleAllowList: ['admin', 'super_admin'] },
          { label: 'Processing Queue', to: '/staff/processing', description: 'New items awaiting processing', featureFlag: 'processing_queue_enabled' },
          { label: 'Weeding', to: '/staff/weeding', description: 'Collection maintenance and deselection' },
          { label: 'Repair Queue', to: '/staff/repair-queue', description: 'Damaged item triage with cost-benefit analysis' },
        ],
      },
    ],
  },
  {
    slug: 'front-desk-hub',
    label: 'Front Desk Hub',
    categories: [
      {
        id: 'circulation',
        title: 'Circulation',
        items: [
          { label: 'Circulation', to: '/staff/circulation', description: 'Check out, return, and renew items' },
          { label: 'Fast Checkout', to: '/staff/checkout/streamlined', description: 'Streamlined barcode-scan checkout' },
          { label: 'Patrons', to: '/staff/patrons', description: 'Look up and manage patron accounts' },
          { label: 'Holds Shelf', to: '/staff/holds/shelf', description: 'Items ready for patron pickup' },
          { label: 'Book Drop', to: '/staff/book-drop', description: 'Process returned items' },
        ],
      },
      {
        id: 'operations',
        title: 'Operations',
        items: [
          { label: 'Cash Drawer', to: '/staff/cash-drawer', description: 'Payment processing and reconciliation' },
          { label: 'Blog', to: '/staff/blog', description: 'Create and manage blog posts' },
          { label: 'Lost & Found', to: '/staff/found-items', description: 'Track found patron items' },
          { label: 'Panic Alert', to: '/staff/panic-alerts', description: 'Staff safety alert system', featureFlag: 'emergency_services_enabled' },
        ],
      },
    ],
  },
  {
    slug: 'board-hub',
    label: 'Board Hub',
    categories: [
      {
        id: 'public-governance',
        title: 'Public Governance',
        items: [
          { label: 'Members', to: '/board/members', description: 'Board member directory and bios' },
          { label: 'Meetings', to: '/board/meetings', description: 'Upcoming and past board meetings' },
          { label: 'Minutes', to: '/board/minutes', description: 'Approved meeting minutes' },
          { label: 'Motions', to: '/board/motions', description: 'Motions, votes, and resolutions' },
          { label: 'Committees', to: '/board/committees', description: 'Standing and ad hoc committees' },
          { label: 'Documents', to: '/board/documents', description: 'Policies, bylaws, and public documents' },
          { label: 'Public Comments', to: '/board/public-comments', description: 'Community feedback on board items' },
        ],
      },
      {
        id: 'administration',
        title: 'Administration',
        items: [
          { label: 'Board Management', to: '/staff/admin/board', description: 'Manage members, terms, and roles' },
          { label: 'Treasurer', to: '/staff/admin/board-treasurer', description: 'Treasury, fund oversight, and financial controls' },
          { label: 'Strategic Planning', to: '/staff/admin/strategic', description: 'Goals, initiatives, and progress tracking' },
          { label: 'Financial Reports', to: '/staff/admin/financial', description: 'Budget and financial data' },
          { label: 'Annual Reports', to: '/staff/admin/annual-reports', description: 'Yearly performance summaries' },
        ],
      },
      {
        id: 'reports',
        title: 'Reports',
        items: [
          { label: 'Report Generator', to: '/board/reports', description: 'Build custom board reports' },
          { label: 'Templates', to: '/board/reports/templates', description: 'Reusable report templates' },
          { label: 'Schedules', to: '/board/reports/schedules', description: 'Automated report delivery schedules' },
        ],
      },
    ],
  },
  {
    slug: 'admin-settings-hub',
    label: 'Settings Hub',
    categories: [
      {
        id: 'library-operations',
        title: 'Library Operations',
        items: [
          { label: 'Circulation & Policy', to: '/staff/admin/circulation-policy', description: 'Borrowing rules, fines, patron types, and staff policies' },
          { label: 'Library Configuration', to: '/staff/admin/library-config', description: 'Site settings, feature toggles, and community resources' },
          { label: 'User Management', to: '/staff/admin/users', description: 'Patron accounts and roles' },
          { label: 'Staff Management', to: '/staff/admin/staff', description: 'Staff accounts and permissions' },
        ],
      },
      {
        id: 'technology-ai',
        title: 'Technology & AI',
        items: [
          { label: 'AI Settings', to: '/staff/admin/ai', description: 'All AI features, models, and controls in one place' },
          { label: 'Search Engine', to: '/staff/admin/search-engine', description: 'Catalog search backend (PostgreSQL or Elasticsearch)' },
        ],
      },
      {
        id: 'outreach-communications',
        title: 'Outreach & Communications',
        items: [
          { label: 'Outreach Dashboard', to: '/staff/admin/outreach', description: 'Email, SMS, campaigns, and patron communication tools' },
          { label: 'Meta Tags', to: '/staff/admin/meta-tags', description: 'SEO and metadata settings' },
          { label: 'Social Sharing', to: '/staff/admin/social-sharing', description: 'Social media sharing config' },
          { label: 'Personalization', to: '/staff/admin/personalization', description: 'Patron experience customization' },
        ],
      },
      {
        id: 'content-programs',
        title: 'Content & Programs',
        items: [
          { label: 'Learning Paths', to: '/staff/admin/learning-paths', description: 'Guided learning sequences' },
          { label: 'Courses', to: '/staff/admin/courses', description: 'Course catalog management' },
          { label: 'Sessions', to: '/staff/admin/sessions', description: 'Schedule and manage learning sessions' },
          { label: 'Events', to: '/staff/admin/events', description: 'Create and manage library events' },
          { label: 'Databases', to: '/staff/admin/databases', description: 'Database subscriptions and access' },
          { label: 'Reading Programs', to: '/staff/admin/reading-programs', description: 'Reading challenges and tracking' },
          { label: 'EDI Settings', to: '/staff/admin/edi', description: 'Electronic data interchange' },
          { label: 'Legal Resources', to: '/staff/admin/legal', description: 'Legal aid clinics, providers, forms, and guides for patrons' },
          { label: 'Content Translations', to: '/staff/admin/content-translations', description: 'Spanish translations for rooms, tech help, legal topics, and discover shelves' },
        ],
      },
      {
        id: 'web-seo',
        title: 'Web & SEO',
        items: [
          { label: 'About Us Page', to: '/staff/admin/about', description: 'Public about page content' },
          { label: 'Link Health', to: '/staff/admin/link-health', description: 'Broken link detection' },
        ],
      },
      {
        id: 'compliance-legal',
        title: 'Compliance & Legal',
        items: [
          { label: 'Compliance Dashboard', to: '/staff/admin/compliance', description: 'All compliance requirements, deadlines, and action items in one place' },
          { label: 'Legal Resources', to: '/staff/admin/legal', description: 'Legal aid clinics, providers, forms, and guides for patrons' },
        ],
      },
      {
        id: 'analytics-reports',
        title: 'Analytics & Reports',
        items: [
          { label: 'Analytics Dashboard', to: '/staff/admin/analytics', description: 'Usage statistics, sharing, and trends' },
          { label: 'Financial Reports', to: '/staff/admin/financial', description: 'Budget and financial data' },
          { label: 'Annual Reports', to: '/staff/admin/annual-reports', description: 'Yearly performance reports' },
        ],
      },
      {
        id: 'board-finance',
        title: 'Board & Finance',
        items: [
          { label: 'Board Management', to: '/staff/admin/board', description: 'Board members and meetings' },
          { label: 'Strategic Planning', to: '/staff/admin/strategic', description: 'Strategic goals and initiatives' },
          { label: 'Treasury', to: '/staff/admin/treasurer', description: 'Treasury, fund management, and oversight' },
        ],
      },
      {
        id: 'system-monitoring',
        title: 'System & Monitoring',
        items: [
          { label: 'System Dashboard', to: '/staff/admin/system', description: 'Server health, cache, storage, and background jobs in one place' },
          { label: 'System Integrations', to: '/staff/admin/integrations', description: 'Status and test buttons for external services (email, SMS, payments, backups, etc.)' },
        ],
      },
      {
        id: 'integrations',
        title: 'Integrations',
        items: [
          { label: 'SIP2 Self-Checkout', to: '/staff/admin/sip2', description: 'Self-checkout kiosk protocol' },
          { label: 'Z39.50', to: '/staff/admin/z3950', description: 'Bibliographic record import protocol' },
          { label: 'EDI', to: '/staff/admin/edi', description: 'Electronic data interchange for vendors' },
          { label: 'Acquisitions', to: '/staff/admin/acquisition', description: 'Vendors, funds, purchase orders' },
          { label: 'Home Delivery', to: '/staff/admin/home-delivery-settings', description: 'Home delivery service config' },
          { label: 'Library Migration', to: '/staff/admin/migration-project', description: 'Migrate from another ILS' },
          { label: 'Audiobooks', to: '/staff/admin/audiobooks', description: 'Audiobook provider integration' },
        ],
      },
      {
        id: 'offboarding',
        title: 'Offboarding',
        items: [
          { label: 'Data Export', to: '/staff/admin/data-export', description: 'Download a portable archive of your library system - wipe can be requested after' },
        ],
      },
    ],
  },
]

export interface BuildHubRegistryOptions {
  /** Hide items whose featureFlag is not enabled. When omitted, no flag filtering. */
  isFeatureEnabled?: (flag: keyof OrganizationFeatures) => boolean
  /** Hide items whose roleAllowList excludes this role. When omitted, no role filtering. */
  role?: UserRole
}

export function buildHubRegistry(opts: BuildHubRegistryOptions = {}): HubItemEntry[] {
  const { isFeatureEnabled, role } = opts
  const out: HubItemEntry[] = []
  for (const hub of RAW_HUBS) {
    for (const cat of hub.categories) {
      for (const item of cat.items) {
        if (isFeatureEnabled && item.featureFlag && !isFeatureEnabled(item.featureFlag)) continue
        if (role && item.roleAllowList && !item.roleAllowList.includes(role)) continue
        out.push({
          hubSlug: hub.slug,
          hubLabel: hub.label,
          categoryId: cat.id,
          categoryTitle: cat.title,
          itemLabel: item.label,
          ...(item.description !== undefined ? { itemDescription: item.description } : {}),
          itemPath: item.to,
          ...(item.featureFlag !== undefined ? { featureFlag: item.featureFlag } : {}),
          ...(item.roleAllowList !== undefined ? { roleAllowList: item.roleAllowList } : {}),
        })
      }
    }
  }
  return out
}

// ---------- fuzzy scoring (no external dep) ----------

export function scoreHubEntry(query: string, entry: HubItemEntry): number {
  const q = query.trim().toLowerCase()
  if (!q) return 0
  const label = entry.itemLabel.toLowerCase()
  const desc = (entry.itemDescription ?? '').toLowerCase()
  const hub = entry.hubLabel.toLowerCase()
  const cat = entry.categoryTitle.toLowerCase()
  const corpus = `${label} ${desc} ${hub} ${cat}`

  const tokens = q.split(/\s+/).filter(Boolean)
  let total = 0
  for (const tok of tokens) {
    const idx = corpus.indexOf(tok)
    if (idx === -1) return 0
    let s = tok.length
    // word-start in any field
    const wordStartRe = new RegExp(`(^|\\s)${tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`)
    if (wordStartRe.test(corpus)) s += 5
    // label hits beat description / hub / category hits
    if (label.includes(tok)) s += 10
    if (label === tok || label.startsWith(tok + ' ')) s += 25
    total += s
  }
  return total
}
