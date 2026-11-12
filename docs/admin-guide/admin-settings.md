# Admin Settings

Pages under the sidebar "Admin" group. These are the system-level controls
typically reserved for `admin` and `director` roles. Touching these can
affect every patron and staff member, so most are gated by `AdminAuth` and
several require a feature flag to even appear in the sidebar.

---

### Settings Hub (`/staff/admin/settings`)
The landing page for system administration. Aggregates links to every admin
surface grouped by domain (system, library config, AI, compliance,
integrations, etc.). Use this as your map when you're not sure which deep
admin page you need. Safe to visit — it's read-only navigation.
See also: [System](#system-monitoring-staffadminsystem), [Library Configuration](#library-configuration-staffadminlibrary-config).

### Admin Dashboard (`/staff/admin` and `/staff/admin/dashboard`)
Top-level admin overview with health badges, recent audit events, and
operational widgets. First place to check when "is the system OK?" comes
up. Pulls from `/api/v1/health/ready` and `/api/v1/audit/admin`. Read-only,
safe to refresh as often as you like.

### System Monitoring (`/staff/admin/system`)
Live system health: API status, scheduler, monitoring, cache, virus scan,
storage, security. The `/staff/admin/cache`, `/staff/admin/virus-scan`,
`/staff/admin/system-health`, `/staff/admin/monitoring`,
`/staff/admin/scheduler`, `/staff/admin/security`, `/staff/admin/storage`,
and `/staff/admin/api-status` routes all redirect here with a hash anchor.
Cache flushes and virus-scan kicks can briefly impact performance — do them
off-peak.

### Library Configuration (`/staff/admin/library-config`)
Branding, contact info, site settings, features, and meta tags rolled into
one config dashboard. `/staff/admin/features`, `/staff/admin/site-settings`
redirect here. Changes propagate to the patron-facing site immediately, so
review your edits before saving.
See also: [Branding & Contact](#branding--contact-staffadminbranding), [Feature Flags](#feature-flags-stafffeature-flags).

### Circulation & Policy (`/staff/admin/circulation-policy`)
Single dashboard for circulation rules, patron settings, staff settings,
system limits, material costs, and financial config. Most legacy routes
(`/admin/circulation-rules`, `/admin/system-limits`,
`/admin/material-costs`, `/admin/patron-settings`,
`/admin/staff-settings`, `/admin/financial-config`) redirect here. Changes
take effect at the next checkout — confirm with a test transaction before
you call it done.

### Outreach & Communications (`/staff/admin/outreach`)
Hub for SMS, email notifications, email marketing, and event marketing
settings. Several legacy routes (`/admin/sms`, `/admin/email-notifications`,
`/admin/email-marketing`, `/admin/event-marketing`) redirect here with hash
anchors. Test sends before enabling broadly — opt-out compliance lives in
the same screen.

### Integrations (`/staff/admin/integrations`)
Test and monitor connections to email, SMS, payment, and storage providers.
Use this when something downstream is failing and you need to know if the
provider handshake works. Each card has a "test" button; failures are
logged but don't auto-page anyone.

### Personalization (`/staff/admin/personalization`)
Configure the recommendation/personalization engine: weights, cold-start
behavior, and per-cohort overrides. AdminAuth required. Changes affect
patron homepage and discovery surfaces within a few minutes (cache TTL).

### User Management (`/staff/admin/users`)
Manage system users, roles, and access permissions. AdminAuth required.
This is the canonical place to add staff accounts, change roles, or
deactivate departed users. Role changes take effect on the user's next
login — force a logout via support if it's urgent.

### Staff Management (`/staff/admin/staff`)
Staff directory with role + employment details for HR-style operations
(separate from auth-level User Management). AdminAuth required.
See also: [User Management](#user-management-staffadminusers), [Pay Rates](#pay-rates-staffadminpay-rates), [Timesheets](#timesheets-staffadmintimesheets).

### Timesheets (`/staff/admin/timesheets`)
Per-staff timesheet editor. AdminAuth required. Used for corrections to
shift clock-in/out records before payroll runs. Edits are audit-logged.

### Pay Rates (`/staff/admin/pay-rates`)
Set hourly or salary rates per staff member, by role, or by date range.
Drives the Fair Scheduling payroll page. AdminAuth required. Changes
apply only to shifts on or after the effective date you set.

### Attendance (`/staff/admin/attendance`)
Event attendance tracking. Records who showed up to programs, used for
both grant reporting and state annuals. Requires `events_enabled`. Walk-in
patrons can be added after the fact.

### Compliance (`/staff/admin/compliance`)
Unified compliance dashboard: CIPA, state compliance, law enforcement
requests, ban tracker, public records. Legacy routes
(`/admin/unified-compliance`, `/admin/cipa`, `/admin/state-compliance`,
`/admin/law-enforcement`, `/admin/ban-tracker`, `/admin/public-records`)
all redirect here with hash anchors. AdminAuth + `compliance_enabled`
required. Every action on this page is audit-logged.

### Legal Resource Admin (`/staff/admin/legal`)
Manage legal clinics, providers, forms, guides, and legal aid service
listings shown to patrons. Requires `legal_services_enabled`.

### Analytics (`/staff/admin/analytics`)
Comprehensive metrics dashboard: checkouts, active patrons, format
distribution, growth. Pulls from the analytics aggregation pipeline.
Heavier load — avoid open-tabbing on a slow connection.

### Strategic Analytics (`/staff/admin/strategic/analytics`)
Board-facing strategic metrics tied to the active strategic plan. Requires
`board_features_enabled` + AdminAuth. Shows progress against goals; used
to populate board meeting packets.
See also: [Strategic Administration](#strategic-administration-staffadminstrategic).

### Strategic Administration (`/staff/admin/strategic`)
Create and manage the library's strategic plan: goals, initiatives,
metrics. AdminAuth + `board_features_enabled`. The plan here drives the
Strategic Analytics dashboard.

### Journey Analytics (`/staff/admin/analytics/journeys`)
Patron journey funnels (signup → first checkout → repeat visit, etc.).
Requires `outreach_enabled`. Useful for outreach targeting; data lags a day.

### Predictive Analytics (`/staff/admin/analytics/predictive`)
Forward-looking analytics: churn risk, demand forecast for popular titles.
Read-only outputs from a backend model — don't treat predictions as gospel.

### Sharing Analytics (`/staff/admin/analytics/sharing`)
Which titles/programs/pages are being shared externally and through which
channel. Inputs into the marketing strategy.

### Website Analytics (`/staff/admin/website-analytics`)
Pageviews, active visitors, top pages, referrers. AdminAuth required.
Lightweight built-in analytics, not a replacement for GA/Plausible.

### Computers (`/staff/admin/computers`)
Configure managed public-access computers: stations, sessions, time
limits, print quotas. Distinct from `/staff/computers` which is the
operational view used by front desk.
See also: [Computers (operational)](library.md#computers-staffcomputers).

### Consortium (`/staff/admin/consortium`)
Manage consortium memberships, ILL partners, and reciprocal borrowing
settings. AdminAuth + `outreach_enabled`. Don't disable an active partner
without coordinating — open ILL requests will hard-fail.

### AI Settings (`/staff/admin/ai`)
Master AI configuration: provider keys, model selection, per-feature
toggles (recommendations, semantic search, summarization). Requires
`ai_tools_enabled`. The `/admin/ai/agents`, `/admin/ai/training`,
`/admin/recommendations`, `/admin/semantic-search` routes redirect here
with hash anchors. Cost-sensitive — review token budgets before flipping
features on.

### Support (`/staff/support/tickets`)
Tickets submitted from guided walkthroughs and patron support requests.
Triage queue for staff. Requires `ai_tools_enabled`.

### Feature Flags (`/staff/feature-flags`)
Toggle per-organization feature flags (events, AI tools, training,
makerspace, etc.). The single source of truth for what's enabled in the
sidebar. Flipping a flag off hides the sidebar entry immediately but does
not delete any data behind it — safe to toggle to scope down a deployment.
See also: feature-flag-add-checklist in dev notes.

### Releases Management (`/staff/admin/releases`)
Track upcoming/recent product releases and changelogs surfaced in-app.
Requires `acquisition_enabled` (yes, oddly — historical wiring).
Read-only for most workflows; admins occasionally pin a release banner.

### Branding & Contact (`/staff/admin/branding`)
Library name, logo, primary color, hours of operation, phone, address —
the canonical brand surface. AdminAuth required. Changes flow to header,
footer, emails, and printed receipts.

### EDI Settings (`/staff/admin/edi`)
EDI vendor connection config for acquisitions (X12 ordering, invoice
ingest). AdminAuth + `acquisition_enabled`. Use "Test Connection" before
saving — bad creds break overnight order runs silently.

### SIP2 Settings (`/staff/admin/sip2`)
Self-checkout kiosk SIP2 server config: port, capacity, allowed clients.
AdminAuth + `sip2_rfid_enabled`. Restart kiosks after changes.

### Z39.50 Sources (`/staff/admin/z3950`)
Configure Z39.50 cataloging targets (LOC, OCLC, etc.) used by the
Cataloging page for record import. AdminAuth required.

### Search Engine Settings (`/staff/admin/search-engine`)
Choose search backend (built-in vs external), tune relevance, manage
synonyms and stopwords. AdminAuth required. Re-indexes can take minutes;
expect briefly stale results.

### Home Delivery Settings (`/staff/admin/home-delivery-settings`)
Service area, eligibility, scheduling windows for home delivery.
AdminAuth + `home_delivery_enabled`. Operational delivery management
lives at `/staff/home-delivery`.

### Mood Categories (`/staff/admin/mood-categories`)
Curate the mood taxonomy used in catalog discovery (cozy, intense,
hopeful, etc.). AdminAuth. Renaming a category re-maps existing items
automatically; deleting one strips the tag from items.

### Meta Tags (`/staff/admin/meta-tags`)
Per-page SEO/OG meta tag overrides for the public site. AdminAuth.
Empty values fall back to defaults configured in Branding.

### Social Sharing (`/staff/admin/social-sharing`)
Enable/disable social sharing features and per-network customization
(Facebook/Twitter/Bluesky/Mastodon share buttons). AdminAuth.

### Link Health Monitoring (`/staff/admin/link-health`)
Crawls and tracks external links across the site (resource lists,
catalog enrichment, blog posts). Surfaces broken links for cleanup.
"Clean up old data" purges historical scan records.

### Migration Wizard (`/staff/admin/migration`)
Bulk import data from Sirsi, Koha, or CSV sources. AdminAuth +
`migration_enabled`. Multi-phase: items, patrons, circulation history.
Each phase is reversible until the next phase is started.

### Migration Project (`/staff/admin/migration-project`)
Long-running migration project view with phase rollback and audit trail.
AdminAuth + `migration_enabled`. Pairs with the Wizard for non-trivial
migrations.

### Treasurer Dashboard (`/staff/admin/treasurer`)
Operational treasurer view with cashflow, fund balances, and recent
transactions. `financial_reports_enabled` + staff/admin role.
See also: [Board Treasurer](board.md#board-treasurer-dashboard-staffadminboard-treasurer).

### Audiobooks Admin (`/staff/admin/audiobooks`)
Monitor performance, manage audiobook content and licensing.
AdminAuth + `streaming_enabled`. Distinct from the patron-facing player.

### Serials (`/staff/admin/serials`)
Serials dashboard: check-in patterns, claim missing issues, vendor
config. `serials_enabled` required.
- `/staff/admin/serials/titles` — manage serial title records
- `/staff/admin/serials/issues` — issue-level check-in
See also: [Acquisition Management](collection.md#acquisition-management-staffadminacquisition).

### Public Databases (`/staff/admin/databases`)
Manage subscription database listings, vendors, and proxy auth config
(Innovative, EBSCO, etc.). The patron-facing databases page reads from
here.

### Archival Collections (`/staff/admin/archival-collections`)
Archival/special-collections admin: finding aids, accessions, restricted
items. Requires `collection_management_enabled`.
See also: [collection.md](collection.md).

### Book Clubs (`/staff/admin/book-clubs`)
Manage book club groups, schedules, and discussion materials.
`book_clubs_enabled` required.

### AMAs (`/staff/admin/amas`)
Ask-Me-Anything sessions: schedule, run live, archive. `ama_enabled`
required.

### Reading Programs (`/staff/admin/reading-programs`)
Summer reading + year-round program admin: tiers, prizes, rules.
`reading_programs_enabled`. The patron-facing program lives elsewhere;
this is the curator view.

### About Us (`/staff/admin/about`)
Manage staff bios displayed on the public About Us page.

### RFID Simulator (`/staff/rfid/simulator`)
**Internal tool.** Simulates RFID reader events for testing checkout
flows without a physical reader. Admin-only.

### Audit Reversal (`/staff/audit-reversal`)
Reverse audit-logged actions (e.g. erroneous mass updates). Use with
extreme care; reversals are themselves audit-logged.

### Workflows (`/staff/workflows`)
Build multi-step automation workflows (e.g. "when overdue > 30 days,
notify and freeze card"). Read the run history before editing a live
workflow.

### Lifecycle Management (`/staff/lifecycle`)
Track and manage items through their complete lifecycle (acquired →
processed → circulating → repaired → withdrawn). The unified view that
underpins inventory, repair queue, and weeding.

### Equipment Management (`/staff/equipment`)
Manage non-circulating equipment (laptops, hotspots, AV gear) with
checkout/return + condition tracking.

### Patron Segmentation (`/staff/patron-segmentation`)
Build saved patron segments (e.g. "active teens", "lapsed cardholders")
used by Marketing and Outreach to target campaigns.

### Homepage Manager (`/staff/homepage`)
Quick links and the library-hours strip on the public homepage. Hero
and book shelves moved to the Home Page admin (below). Changes are
public immediately. Any staff role can edit.

### Home Page (`/staff/home-page`)
Hero pick and book shelves on the public home page. Admin-only (the
hero/shelf/config APIs require an admin role). Shelves are saved queries
(new arrivals, staff picks, subject, format, manual list) — the "staff
picks" kind shows the newest additions across active Staff Picks lists.
Hero and shelf items must be fully cataloged and public; the editor
rejects items that are not. Empty shelves hide themselves. Public output
is cached ~60s.
