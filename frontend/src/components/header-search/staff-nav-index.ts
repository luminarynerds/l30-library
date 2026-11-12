/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface StaffNavEntry {
  title: string
  description: string
  route: string
  keywords: string[]
  category: 'circulation' | 'patrons' | 'catalog' | 'admin' | 'reports' | 'tools' | 'programs'
}

export const staffNavIndex: StaffNavEntry[] = [
  // === Circulation ===
  {
    title: 'Circulation',
    description: 'Check out, check in, and manage materials',
    route: '/staff/circulation',
    keywords: ['checkout', 'checkin', 'check out', 'check in', 'barcode', 'scan', 'borrow', 'return'],
    category: 'circulation',
  },
  {
    title: 'Streamlined Checkout',
    description: 'Fast checkout mode for busy desks',
    route: '/staff/checkout/streamlined',
    keywords: ['fast checkout', 'quick checkout', 'streamlined', 'express'],
    category: 'circulation',
  },
  {
    title: 'Hold Shelf',
    description: 'Manage items waiting for patron pickup',
    route: '/staff/holds/shelf',
    keywords: ['holds', 'hold shelf', 'pickup', 'waiting', 'reserve'],
    category: 'circulation',
  },
  {
    title: 'Book Drop',
    description: 'Process returned items from the book drop',
    route: '/staff/book-drop',
    keywords: ['book drop', 'returns', 'drop box', 'after hours'],
    category: 'circulation',
  },
  {
    title: 'Fast Book Drop Processing',
    description: 'Rapid processing mode for book drop returns',
    route: '/staff/book-drop/fast-process',
    keywords: ['fast process', 'bulk returns', 'rapid', 'book drop'],
    category: 'circulation',
  },
  {
    title: 'Interlibrary Loan',
    description: 'Manage ILL requests and transit',
    route: '/staff/interlibrary-loan',
    keywords: ['ill', 'interlibrary', 'loan', 'transit', 'borrow from other library'],
    category: 'circulation',
  },
  {
    title: 'Lost & Damaged Items',
    description: 'Track and resolve lost or damaged materials',
    route: '/staff/lost-damaged',
    keywords: ['lost', 'damaged', 'missing', 'replacement', 'claim'],
    category: 'circulation',
  },

  // === Patrons ===
  {
    title: 'Patron Management',
    description: 'Search and manage patron accounts',
    route: '/staff/patrons',
    keywords: ['patron', 'patrons', 'user', 'account', 'member', 'card holder', 'library card'],
    category: 'patrons',
  },
  {
    title: 'Card Applications',
    description: 'Review and process new library card applications',
    route: '/staff/card-applications',
    keywords: ['card application', 'new card', 'register', 'sign up', 'application'],
    category: 'patrons',
  },
  {
    title: 'Patron Segmentation',
    description: 'View patron segments and demographics',
    route: '/staff/patron-segmentation',
    keywords: ['segment', 'demographics', 'groups', 'patron type', 'age group'],
    category: 'patrons',
  },

  // === Fines & Reading Minutes ===
  {
    title: 'Fine Management',
    description: 'View, waive, and manage patron fines and payments',
    route: '/staff/fines',
    keywords: ['fine', 'fines', 'fee', 'fees', 'overdue', 'payment', 'waive', 'waiver', 'charge', 'owed', 'balance', 'pay'],
    category: 'circulation',
  },
  {
    title: 'Reading Minutes (Read-for-Fines)',
    description: 'Manage reading minutes that replace fines for young readers',
    route: '/staff/patrons',
    keywords: ['reading minutes', 'read for fines', 'minutes', 'reading time', 'juvenile fines', 'kids fines', 'fine alternative', 'pay off fines with reading'],
    category: 'programs',
  },

  // === Cataloging ===
  {
    title: 'Cataloging',
    description: 'Create and edit catalog records',
    route: '/staff/cataloging',
    keywords: ['catalog', 'cataloging', 'marc', 'record', 'bibliographic', 'add item'],
    category: 'catalog',
  },
  {
    title: 'Export MARC',
    description: 'Download catalog records as MARC21 or MARCXML',
    route: '/staff/export-marc',
    keywords: ['export marc', 'marc export', 'marc', 'marc21', 'marcxml', 'download records', 'bibliographic export'],
    category: 'catalog',
  },
  {
    title: 'Manga Cataloging',
    description: 'Specialized cataloging for manga series',
    route: '/staff/manga-cataloging',
    keywords: ['manga', 'comic', 'graphic novel', 'series'],
    category: 'catalog',
  },
  {
    title: 'Inventory',
    description: 'Inventory management and shelf reading',
    route: '/staff/inventory',
    keywords: ['inventory', 'stock', 'shelf reading', 'count', 'weed', 'weeding'],
    category: 'catalog',
  },
  {
    title: 'RFID Management',
    description: 'RFID tag programming and management',
    route: '/staff/rfid',
    keywords: ['rfid', 'tag', 'chip', 'scan', 'program'],
    category: 'catalog',
  },

  // === Acquisitions ===
  {
    title: 'Acquisitions',
    description: 'Purchase orders, vendors, and fund management',
    route: '/staff/acquisition',
    keywords: ['acquisition', 'purchase', 'order', 'vendor', 'fund', 'budget', 'buy', 'spending'],
    category: 'catalog',
  },

  // === Programs & Events ===
  {
    title: 'Reading Programs',
    description: 'Manage summer reading and other reading challenges',
    route: '/staff/admin/reading-programs',
    keywords: ['reading program', 'summer reading', 'challenge', 'reading log', 'gamification', 'prizes', 'badges'],
    category: 'programs',
  },
  {
    title: 'Events Management',
    description: 'Create and manage library events and programs',
    route: '/staff/events',
    keywords: ['event', 'events', 'program', 'programs', 'class', 'workshop', 'storytime', 'calendar'],
    category: 'programs',
  },
  {
    title: 'Book Clubs',
    description: 'Manage library book clubs',
    route: '/staff/book-clubs',
    keywords: ['book club', 'book clubs', 'discussion', 'reading group'],
    category: 'programs',
  },
  {
    title: 'Outreach',
    description: 'Community outreach and partnerships',
    route: '/staff/outreach',
    keywords: ['outreach', 'community', 'partnership', 'visit', 'off-site'],
    category: 'programs',
  },

  // === Reports & Analytics ===
  {
    title: 'Reports',
    description: 'Circulation, collection, and usage reports',
    route: '/staff/reports',
    keywords: ['report', 'reports', 'statistics', 'stats', 'data', 'export', 'csv'],
    category: 'reports',
  },
  {
    title: 'Analytics Dashboard',
    description: 'Visual analytics and usage trends',
    route: '/staff/analytics',
    keywords: ['analytics', 'dashboard', 'trends', 'charts', 'usage', 'metrics'],
    category: 'reports',
  },
  {
    title: 'Financial Reports',
    description: 'Revenue, fines, and budget reports',
    route: '/staff/financial-reports',
    keywords: ['financial', 'revenue', 'budget', 'fines report', 'income', 'money'],
    category: 'reports',
  },
  {
    title: 'Audit Log',
    description: 'System-wide audit trail of staff actions',
    route: '/staff/audit-logs',
    keywords: ['audit', 'log', 'trail', 'history', 'who did what', 'actions'],
    category: 'reports',
  },

  // === Admin Settings ===
  {
    title: 'Circulation Policy',
    description: 'Borrowing rules, fines, patron types, and staff policies',
    route: '/staff/admin/circulation-policy',
    keywords: ['circulation policy', 'borrowing rules', 'loan period', 'fine policy', 'fine rate', 'fine free', 'overdue', 'renewal', 'patron type'],
    category: 'admin',
  },
  {
    title: 'Fine Policy Settings',
    description: 'Configure fine rates, caps, grace periods, and fine-free options',
    route: '/staff/admin/circulation-policy#financial',
    keywords: ['fine policy', 'fine rate', 'fine free', 'grace period', 'maximum fine', 'cap', 'overdue fine', 'daily fine', 'fine settings', 'fine configuration'],
    category: 'admin',
  },
  {
    title: 'Database Subscriptions',
    description: 'Manage online database subscriptions and access',
    route: '/staff/admin/databases',
    keywords: ['database', 'databases', 'subscription', 'ezproxy', 'vendor', 'ebsco', 'proquest', 'gale', 'ancestry'],
    category: 'admin',
  },
  {
    title: 'Settings Hub',
    description: 'All admin settings in one place',
    route: '/staff/admin/settings',
    keywords: ['settings', 'admin', 'configuration', 'config', 'setup', 'preferences'],
    category: 'admin',
  },
  {
    title: 'Content Translations',
    description: 'Spanish translations for rooms, tech help, legal topics, and discover shelves',
    route: '/staff/admin/content-translations',
    keywords: ['content translations', 'spanish', 'translate', 'i18n', 'language', 'localization'],
    category: 'admin',
  },
  {
    title: 'SIP2 Settings',
    description: 'Self-checkout machine and SIP2 server configuration',
    route: '/staff/admin/sip2',
    keywords: ['sip2', 'self checkout', 'self-check', 'kiosk', 'machine'],
    category: 'admin',
  },
  {
    title: 'Library Configuration',
    description: 'Branch settings, hours, contact info, branding',
    route: '/staff/admin/library-config',
    keywords: ['library', 'branch', 'hours', 'contact', 'branding', 'logo', 'name', 'address', 'phone'],
    category: 'admin',
  },
  {
    title: 'User Management',
    description: 'Manage staff accounts and permissions',
    route: '/staff/admin/users',
    keywords: ['users', 'staff', 'permissions', 'roles', 'admin', 'access', 'accounts'],
    category: 'admin',
  },

  // === Tools ===
  {
    title: 'Staff Knowledge Base',
    description: 'Policies, procedures, how-tos, and quick answers',
    route: '/staff/knowledge-base',
    keywords: ['knowledge', 'how to', 'policy', 'procedure', 'help', 'guide', 'tutorial', 'faq'],
    category: 'tools',
  },
  {
    title: 'Staff Dashboard',
    description: 'Overview of daily tasks and alerts',
    route: '/staff/dashboard',
    keywords: ['dashboard', 'home', 'overview', 'today', 'alerts', 'tasks'],
    category: 'tools',
  },
  {
    title: 'Print Management',
    description: 'Manage patron print jobs and printers',
    route: '/staff/print-management',
    keywords: ['print', 'printer', 'printing', 'copies', 'copier', 'paper'],
    category: 'tools',
  },
  {
    title: 'Computer Reservations',
    description: 'Manage public computer sessions and reservations',
    route: '/staff/computers',
    keywords: ['computer', 'reservation', 'pc', 'workstation', 'session', 'time limit'],
    category: 'tools',
  },
  {
    title: 'Room Bookings',
    description: 'Manage meeting room reservations',
    route: '/staff/rooms',
    keywords: ['room', 'meeting room', 'booking', 'reservation', 'space'],
    category: 'tools',
  },
  {
    title: 'Makerspace',
    description: 'Manage makerspace equipment and bookings',
    route: '/staff/makerspace',
    keywords: ['makerspace', 'maker', '3d printer', 'laser', 'equipment', 'tools'],
    category: 'tools',
  },
  {
    title: 'Streaming Management',
    description: 'Manage streaming content and licenses',
    route: '/staff/streaming',
    keywords: ['streaming', 'video', 'movie', 'film', 'kanopy', 'hoopla'],
    category: 'tools',
  },
  {
    title: 'Staff Picks',
    description: 'Manage staff recommendation lists',
    route: '/staff/picks',
    keywords: ['picks', 'recommendations', 'staff picks', 'curated', 'suggest'],
    category: 'tools',
  },
  {
    title: 'Home Page',
    description: 'Edit hero pick, shelves, and patron home-page chrome',
    route: '/staff/home-page',
    keywords: ['home', 'hero', 'shelves', 'landing', 'front page', 'page'],
    category: 'tools',
  },
  {
    title: 'Panic Alerts',
    description: 'Emergency alert and safety system',
    route: '/staff/panic-alerts',
    keywords: ['panic', 'emergency', 'alert', 'safety', 'security', 'help', 'sos'],
    category: 'tools',
  },
  {
    title: 'Training',
    description: 'Staff training courses and progress',
    route: '/staff/training',
    keywords: ['training', 'course', 'learning', 'professional development', 'onboarding'],
    category: 'tools',
  },
  {
    title: 'Strategic Planning',
    description: 'Library strategic plan and goals',
    route: '/staff/strategic',
    keywords: ['strategic', 'plan', 'goals', 'objectives', 'mission'],
    category: 'tools',
  },
  {
    title: 'Scheduling',
    description: 'Staff scheduling and shift management',
    route: '/staff/scheduling',
    keywords: ['schedule', 'shift', 'hours', 'coverage', 'swap', 'time off', 'calendar'],
    category: 'tools',
  },
  {
    title: 'Home Delivery',
    description: 'Manage homebound patron delivery service',
    route: '/staff/home-delivery',
    keywords: ['home delivery', 'homebound', 'delivery', 'shut-in', 'volunteer'],
    category: 'tools',
  },
  {
    title: 'Volunteers',
    description: 'Applications, roster, shifts, and hour logs',
    route: '/staff/volunteers',
    keywords: ['volunteers', 'volunteer', 'shifts', 'hours', 'roster', 'applications', 'hour log'],
    category: 'tools',
  },
]

export function searchStaffNav(query: string): StaffNavEntry[] {
  const q = query.toLowerCase().trim()
  if (q.length < 2) return []

  return staffNavIndex
    .map((entry) => {
      const haystack = [
        entry.title,
        entry.description,
        ...entry.keywords,
      ].join(' ').toLowerCase()

      // Exact keyword match gets highest score
      const exactKeyword = entry.keywords.some((k) => k.toLowerCase() === q)
      if (exactKeyword) return { entry, score: 1.0 }

      // Keyword starts-with
      const keywordPrefix = entry.keywords.some((k) => k.toLowerCase().startsWith(q))
      if (keywordPrefix) return { entry, score: 0.9 }

      // Title contains
      if (entry.title.toLowerCase().includes(q)) return { entry, score: 0.85 }

      // Any keyword contains
      const keywordContains = entry.keywords.some((k) => k.toLowerCase().includes(q))
      if (keywordContains) return { entry, score: 0.8 }

      // Description contains
      if (entry.description.toLowerCase().includes(q)) return { entry, score: 0.7 }

      // Multi-word: all tokens present somewhere in haystack
      const tokens = q.split(/\s+/)
      if (tokens.length > 1 && tokens.every((t) => haystack.includes(t))) {
        return { entry, score: 0.75 }
      }

      return { entry, score: 0 }
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((r) => r.entry)
}
