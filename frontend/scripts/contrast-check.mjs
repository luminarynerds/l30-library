// Verify WCAG contrast for the token pairs changed in the a11y batch (task 8:
// patron contrast fixes). Real hexes pulled from tailwind.config.js /
// src/index.css (--accent-rose-rgb light/dark theme values) as of 2026-07-02.
const hexToRgb = h => h.match(/\w\w/g).map(x => parseInt(x, 16))
const rgbToHex = ([r, g, b]) => [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('')
// Alpha-composite fg-with-alpha over bg, per-channel: result = alpha*fg + (1-alpha)*bg
const blend = (fgHex, bgHex, alpha) => {
  const fg = hexToRgb(fgHex), bg = hexToRgb(bgHex)
  return rgbToHex(fg.map((c, i) => alpha * c + (1 - alpha) * bg[i]))
}
const L = h => { const c = hexToRgb(h).map(v => v / 255).map(v => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] }
const ratio = (a, b) => { const [x, y] = [L(a), L(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05) }

// ---- Real token hexes (tailwind.config.js) ----
const T = {
  lscDark: '1e1a24',
  lscCream: 'f0ecf0',
  cardWhiteLight: 'ffffff',
  cardWhiteDark: '252030',
  cream50: 'faf8fa',
  earth300: 'b8b4bc',
  earth400: '9e9aa6',
  earth500: '6e6a76',
  earth600: '54505c',
  earth700: '3a3540',
  earth800: '2a2530',
  earth900: '1e1a24',
  warning50: 'fffbeb',
  warning600: 'd97706',
  warning700: 'b45309',
  warning800: '92400e',
  success400: '4ade80',
  success600: '15803d',
  success700: '166534',
  danger500: 'ef4444',
  danger600: 'dc2626',
  danger700: 'b91c1c',
  forest600: '6b9088',
  forest700: '5b8078',
  forest800: '4b7068',
  white: 'ffffff',
  // lsc-rose is a CSS var (--accent-rose-rgb), theme-dependent (src/index.css)
  lscRoseLight: '7a4040',   // .light --accent-rose-rgb: 122 64 64
  lscRoseDarkTheme: '8b5e5e', // :root (dark) --accent-rose-rgb: 139 94 94
  lscRoseDark: '5c2e2e',    // new token (tailwind.config.js)
  // ---- Task 9 additions (staff contrast pass) ----
  earth200: 'c0bcc8',
  success300: '86efac',
  success800: '14532d',
  danger300: 'fca5a5',
  danger400: 'f87171',
  danger800: '991b1b',
  forest900: '3b6058',
  lscGreen: '7ba098',
  // Tailwind default-palette hexes used only by AVATAR_COLORS (AdminUsersPage)
  // NB: "rose" here is Tailwind's default rose scale (avatar chip), distinct from the lsc-rose brand token.
  rose600: 'e11d48', rose700: 'be123c',
  pink600: 'db2777', pink700: 'be185d',
  fuchsia600: 'c026d3', fuchsia700: 'a21caf',
  category600: '9333ea', category700: '7e22ce',
  violet600: '7c3aed', violet700: '6d28d9',
  indigo600: '4f46e5', indigo700: '4338ca',
  sky700: '0369a1', sky800: '075985',
  cyan700: '0e7490', cyan800: '155e75',
  teal700: '0f766e', teal800: '115e59',
  emerald700: '047857', emerald800: '065f46',
  lime700: '4d7c0f', lime800: '3f6212',
}

const pairs = []
const add = (name, fg, bg, floor) => pairs.push([name, fg, bg, floor])

// --- CatalogItemPage.tsx:514 status-history date/actor spans, /50 -> /70 ---
add('CatalogItemPage status-history date+actor /70 on white (light)', blend(T.lscDark, T.cardWhiteLight, 0.7), T.cardWhiteLight, 4.5)
add('CatalogItemPage status-history date+actor /70 on card-dark (dark)', blend(T.lscCream, T.cardWhiteDark, 0.7), T.cardWhiteDark, 4.5)

// --- CatalogItemPage.tsx:674 unfilled star, earth-300 -> earth-500 (light) / earth-600 -> earth-400 (dark) ---
add('CatalogItemPage unfilled star earth-500 on white (light)', T.earth500, T.cardWhiteLight, 3)
add('CatalogItemPage unfilled star earth-400 on card-dark (dark)', T.earth400, T.cardWhiteDark, 3)

// --- CatalogSearchBar.tsx:327 / FormatTabs.tsx:148 availability dot -> status-success-700 ---
add('availability dot success-700 on white', T.success700, T.cardWhiteLight, 3)
add('CatalogSearchBar visible label success-700 on white (light)', T.success700, T.cardWhiteLight, 4.5)
add('CatalogSearchBar visible label success-400 on earth-800 (dark)', T.success400, T.earth800, 4.5)

// --- ItemOverview.tsx:157 warning-600 -> warning-700 on warning-50 ---
add('ItemOverview medium-complexity warning-700 on warning-50', T.warning700, T.warning50, 4.5)

// --- RelatedItems.tsx: remove opacity-75, solid text-lsc-dark/text-lsc-cream for "Checked out" ---
add('RelatedItems "Checked out" solid lsc-dark on white (light)', T.lscDark, T.cardWhiteLight, 4.5)
add('RelatedItems "Checked out" solid lsc-cream on earth-800 (dark)', T.lscCream, T.earth800, 4.5)

// --- ShelfNotes.tsx:163,201 /50 -> /70 on lsc-cream (light) / lsc-dark (dark) ---
add('ShelfNotes counter/author /70 on lsc-cream (light)', blend(T.lscDark, T.lscCream, 0.7), T.lscCream, 4.5)
add('ShelfNotes counter/author /70 on lsc-dark (dark)', blend(T.lscCream, T.lscDark, 0.7), T.lscDark, 4.5)

// --- lsc-rose-dark: new token, white text on it (used as bg-lsc-rose hover fill and SLIDE_COLORS bg) ---
add('white on lsc-rose-dark (new token)', T.white, T.lscRoseDark, 4.5)

// --- DiscoverPage.tsx forest-600 -> forest-800 badge, white text ---
// Target code (BADGE_CLASSES in the old inline-carousel DiscoverPage) was
// removed by the #1780 editorial front-door redesign -- availability badges
// now live in CatalogShelf.tsx (pre-existing, separately audited). Pair
// removed as dead; white-on-forest-800 stays covered by the
// "PatronAccountSettingsModal Save button" pair below (same hex values).

// --- DiscoverPage.tsx: FeaturedSlide hero-carousel author/description text
// (text-white/80 -> text-white, text-white/70 -> text-white/90) targeted
// SLIDE_COLORS backgrounds. The #1780 redesign removed the hero carousel
// entirely (no FeaturedSlide, no SLIDE_COLORS) -- both loops and the
// slideTeal/slidePurple/slideSage backgrounds they checked are gone as
// dead code. lsc-rose (light/dark theme) resurfaces below for the
// redesign's "Curated Picks" card, which reuses solid white-on-lsc-rose.
for (const [label, bg] of [
  ['lsc-rose (light theme)', T.lscRoseLight],
  ['lsc-rose (dark theme)', T.lscRoseDarkTheme],
]) {
  add(`DiscoverPage "Curated Picks" card body text-white (solid) on ${label}`, T.white, bg, 4.5)
}

// --- BookRequestPage.tsx:172 "Searching..." add dark:text-earth-400 (on dark:bg-earth-900) ---
add('BookRequestPage "Searching..." earth-400 on earth-900 (dark)', T.earth400, T.earth900, 4.5)

// --- BookRequestPage.tsx:194,252 warning-600 -> warning-700 buttons, white text (+ hover bumped to warning-800) ---
add('BookRequestPage submit button white on warning-700', T.white, T.warning700, 4.5)
add('BookRequestPage submit button hover white on warning-800', T.white, T.warning800, 4.5)

// --- BookRequestPage.tsx:246 danger-500 -> danger-700 on cream-50 ---
add('BookRequestPage add-library error danger-700 on cream-50', T.danger700, T.cream50, 4.5)

// --- EbookDetailPage.tsx:369,402 dark:text-earth-600 -> dark:text-earth-400 (on dark:bg-earth-900) ---
add('EbookDetailPage sign-in/buy-prompt earth-400 on earth-900 (dark)', T.earth400, T.earth900, 4.5)

// --- MyBooksPage.tsx:228 warning-600 -> warning-700 (light only, due-date text on white card) ---
add('MyBooksPage urgent due-date warning-700 on white (light)', T.warning700, T.cardWhiteLight, 4.5)

// --- MyBooksPage.tsx:240 add dark:text-earth-400 (indie downloads, on dark:bg-earth-800 card) ---
add('MyBooksPage indie downloads earth-400 on earth-800 (dark)', T.earth400, T.earth800, 4.5)

// ============================================================================
// Task 9: staff contrast pass (WCAG 1.4.3, 77 findings across
// "Staff / shared components & layout" + "Staff / pages")
// ============================================================================

// --- Motif A: text-lsc-dark/50(-ish) dark:text-lsc-cream/50(-ish) helper/meta
// text -> /70 both sides. Reused verbatim across 33 report entries (AddPatronModal,
// AdminAboutUsPage, AdminComputersPage x2, AdminCoursesPage placeholder,
// AdminMigrationWizardPage (dark add), StaffTeenVolunteersPage x2, StaffTransitPage x2,
// StaffVolunteerManagementPage x3, CollectionDashboardPage x4, MobileAuditPage,
// RepairQueuePage x11 (dark-only), BatchCheckinSection x3, CirculationAnalyticsTab x4,
// PatronSearchSection, QuickMessagePanel, PatronProfileTab, PatronTagsSection x3,
// MarketingRemindersTab (dark-only), ProgramPlansTab x3 (dark-only),
// SuccessMetricsTab (dark-only), StaffRoomsPage (dark-only), ReservationCalendar x2
// (dark-only), ReservationList (dark-only), RoomList x2 (dark-only),
// RoomStatsPanel x4 (dark-only), StaffComicCatalogingPage x6 (dark-only),
// StaffComputersPage x2 (dark-only), ActivityFeed x2).
// lsc-dark/70-on-white pair already exists above (CatalogItemPage, task 8) -- reused, not
// re-added. lsc-dark/70-on-lsc-cream and lsc-cream/70-on-lsc-dark also already exist
// above (ShelfNotes, task 8) -- reused for PatronProfileTab/PatronTagsSection cream cards.
add('Task 9 helper-text lsc-cream/70 on earth-800 (dark card, most common bg)', blend(T.lscCream, T.earth800, 0.7), T.earth800, 4.5)
add('Task 9 helper-text lsc-cream/70 on earth-900 (dark page bg -- CollectionDashboardPage)', blend(T.lscCream, T.earth900, 0.7), T.earth900, 4.5)
add('Task 9 helper-text lsc-cream/70 on earth-700 (dark row bg -- ProgramPlansTab)', blend(T.lscCream, T.earth700, 0.7), T.earth700, 4.5)

// --- Motif B: filled bg-status-warning-500/600 + text-white buttons -> bg-status-warning-700
// (hover -800 where a hover shade exists). Reused across BulkPatronOperations "Waive Fines",
// RoutePrep "Depart", StaffOverrideBookingModal "Create Override", and the priority-2/3
// buttons in BulkItemOperations. white-on-warning-700/800 pairs already exist above
// (BookRequestPage, task 8) -- reused, not re-added.
// HoldTrapCard used bg-amber-600/700 (Tailwind default "amber"), hex-identical to
// status-warning-600/700 -- same pair, reused conceptually (amber-700 === #b45309).
add('Task 9 amber-800 (HoldTrapCard hover) white text, hex === status-warning-800', T.white, T.warning800, 4.5)

// --- One-off: BulkItemOperations priority-1 button bg-status-danger-500 -> -600, white text ---
add('BulkItemOperations priority-1 white on danger-600', T.white, T.danger600, 4.5)

// --- One-off family: text-status-warning-600 (plain text, not a button) -> -700 on white/near-white
// (FocusTimeApprovalDashboard, SendNotificationModal, StaffFineManagementPage, UserTable
// "(Locked)", ExpiringHoldsView, PatronHoldsTab:162, PatronCheckoutsTab:185,
// StaffDownloadMonitorPage scoreColor) ---
add('Task 9 warning-700 text on white (warning-text family)', T.warning700, T.cardWhiteLight, 4.5)
// PatronOnboardingStatus sits on bg-lsc-cream specifically -- warning-700 only reaches 4.30
// there (fails), so bumped one shade darker to warning-800, per the forest-800 precedent.
add('PatronOnboardingStatus "Skipped" warning-800 on lsc-cream (deviation: -700 failed at 4.30)', T.warning800, T.lscCream, 4.5)

// --- One-off family: text-status-danger-500 (plain text / required-field asterisk) -> -600
// (ResolveExceptionModal, SessionModal, AdminEDISettingsPage, BookDropDetail x3,
// StaffWorkflowsPage delete-workflow trigger, PatronCheckoutsTab:180, PatronHoldsTab:167) ---
add('Task 9 danger-600 text on white (danger-text/asterisk family)', T.danger600, T.cardWhiteLight, 4.5)

// --- PatronHoldsTab.tsx:175 cancellation reason: drop /80 opacity, solid -700/dark:-300 ---
add('PatronHoldsTab cancellation reason danger-700 on white (light)', T.danger700, T.cardWhiteLight, 4.5)
add('PatronHoldsTab cancellation reason danger-300 on earth-800 (dark)', T.danger300, T.earth800, 4.5)

// --- StaffDownloadMonitorPage.tsx:373 scoreColor(): success-500 -> success-600 on white ---
add('StaffDownloadMonitorPage score success-600 on white', T.success600, T.cardWhiteLight, 3)

// --- StaffLocalAuthoritiesPage.tsx:82 STATUS_CLASSES.active: bg-lsc-green -> bg-status-success-700 ---
add('StaffLocalAuthoritiesPage active badge white on success-700', T.white, T.success700, 4.5)

// --- earth-500/600 dark-mode legibility family: dark:text-earth-500/600 -> lighter shade
// (AcquisitionManagementPage x3 -> earth-300, AdminReadingListsPage add earth-400,
// ReportAuditLogPage -> earth-400, StaffProcessingQueuePage -> earth-400,
// PullListView "+slot" -> earth-200) ---
add('Task 9 earth-300 on earth-800 (dark) -- AcquisitionManagementPage badge', T.earth300, T.earth800, 4.5)
add('Task 9 earth-300 on earth-900 (dark) -- AcquisitionManagementPage rows/cards', T.earth300, T.earth900, 4.5)
add('Task 9 earth-400 on earth-900 (dark) -- AdminReadingListsPage/ReportAuditLogPage', T.earth400, T.earth900, 4.5)
add('Task 9 earth-400 on earth-800 (dark) -- ReportAuditLogPage/StaffProcessingQueuePage', T.earth400, T.earth800, 4.5)
add('PullListView "+slot" earth-200 on earth-800 (dark)', T.earth200, T.earth800, 4.5)

// --- hold-shelf/constants.ts getUrgencyColor(): add dark: variants for the >3-day
// (success-600) and expired (danger-600) branches; warning-600 (1-3 day) already passed ---
add('PullListView/hold-shelf success-400 on earth-800 (dark)', T.success400, T.earth800, 4.5)
add('PullListView/hold-shelf danger-400 on earth-800 (dark)', T.danger400, T.earth800, 4.5)

// --- BatchCheckinSection.tsx:372 drop /70 opacity modifier on tinted stat labels ---
add('BatchCheckinSection Errors label danger-700 solid on danger-50 tint', T.danger700, 'fef2f2', 4.5)
add('BatchCheckinSection Returned label success-600 solid on success-50 tint', T.success600, 'f0fdf4', 4.5)

// --- PatronAccountSettingsModal.tsx:125 "active" badge: text-lsc-green -> theme-split text ---
add('PatronAccountSettingsModal active badge forest-800 on lsc-green/10 tint (light)', T.forest800, blend(T.lscGreen, T.cardWhiteLight, 0.10), 4.5)
add('PatronAccountSettingsModal active badge success-300 on lsc-green/20 tint over earth-800 (dark)', T.success300, blend(T.lscGreen, T.earth800, 0.20), 4.5)

// --- PatronAccountSettingsModal.tsx:234 Save button: bg-lsc-green -> bg-forest-800/900 ---
add('PatronAccountSettingsModal Save button white on forest-800', T.white, T.forest800, 4.5)
add('PatronAccountSettingsModal Save button hover white on forest-900', T.white, T.forest900, 4.5)

// --- ProgramPlansTab.tsx:336 Budget Variance: add dark: variants, bump light to -700 ---
add('ProgramPlansTab budget-variance danger-700 on earth-50 (light)', T.danger700, 'f0ecf0', 4.5)
add('ProgramPlansTab budget-variance success-700 on earth-50 (light)', T.success700, 'f0ecf0', 4.5)
add('ProgramPlansTab budget-variance danger-300 on earth-700 (dark)', T.danger300, T.earth700, 4.5)
add('ProgramPlansTab budget-variance success-300 on earth-700 (dark)', T.success300, T.earth700, 4.5)

// --- SuccessMetricsTab.tsx:268 attendance-rate %: add dark: variants, bump light to -700 ---
add('SuccessMetricsTab attendance success-700 on white (light)', T.success700, T.cardWhiteLight, 4.5)
add('SuccessMetricsTab attendance warning-700 on white (light) -- dup of warning-text family', T.warning700, T.cardWhiteLight, 4.5)
add('SuccessMetricsTab attendance danger-700 on white (light) -- dup of danger-text family', T.danger700, T.cardWhiteLight, 4.5)
add('SuccessMetricsTab attendance success-300 on earth-800 (dark)', T.success300, T.earth800, 4.5)
add('SuccessMetricsTab attendance warning-300 on earth-800 (dark)', 'fcd34d', T.earth800, 4.5)
add('SuccessMetricsTab attendance danger-300 on earth-800 (dark) -- dup of PatronHoldsTab pair', T.danger300, T.earth800, 4.5)

// --- ReadyToTrySection.tsx:28 / StaffImpactSection.tsx:25,33: text-lsc-white -> text-white
// on bg-lsc-rose (lsc-white resolves to --card-white, near-black in dark mode -- wrong token).
// white-on-lsc-rose (light/dark theme) pairs already exist above (DiscoverPage, task 8) --
// reused, not re-added. ---

// --- LibraryCardPrintModal.tsx:37 raw inline CSS .header color: #e67e22 -> #92400e (warning-800) ---
add('LibraryCardPrintModal header #92400e on white (raw print-preview CSS)', '92400e', T.cardWhiteLight, 4.5)

// --- AdminUsersPage/UserAvatar.tsx: AVATAR_COLORS swatches, per-hue minimal
// correction (fix round 1: replaces uniform -700/dark:-800 rescale). Only the
// primary (lighter, light-theme) shade of each chosen pair is checked here --
// it's the tighter constraint; the darker dark-theme shade always clears more
// contrast. 9 hues hold at -600 (already >=4.5:1); sky/cyan/teal/emerald/lime/
// warning need -700. 16-entry array (2 status-warning duplicates); dedupe by hex. ---
for (const [label, hex] of [
  ['rose-600', T.rose600],
  ['pink-600', T.pink600],
  ['fuchsia-600', T.fuchsia600],
  ['category-600', T.category600],
  ['violet-600', T.violet600],
  ['indigo-600', T.indigo600],
  ['earth-600 (avatar)', T.earth600],
  ['sky-700', T.sky700],
  ['cyan-700', T.cyan700],
  ['teal-700', T.teal700],
  ['emerald-700', T.emerald700],
  ['success-600 (avatar)', T.success600],
  ['lime-700', T.lime700],
  ['warning-700 (avatar) -- dup of warning-text family', T.warning700],
  ['warning-700 (avatar) -- dup of warning-text family', T.warning700],
  ['danger-600 (avatar)', T.danger600],
]) {
  add(`UserAvatar white initials on ${label}`, T.white, hex, 4.5)
}

let fail = 0
for (const [name, fg, bg, floor] of pairs) {
  const r = ratio(fg, bg)
  const ok = r >= floor
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}: ${r.toFixed(2)}:1 (needs ${floor}:1)`)
  if (!ok) fail++
}
console.log(`\n${pairs.length - fail}/${pairs.length} passed`)
process.exit(fail ? 1 : 0)
