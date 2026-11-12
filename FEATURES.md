<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 — Full Feature Inventory

Generated: 2026-07-08 (reconciled against live `backend/app/api/v1/` routers and
the production `organization_features` toggle state — all 70 module toggles ON).

---

## Public / Patron

### Catalog & Discovery
- Full-text + faceted catalog search, grid/list toggle
- AI/semantic search (pgvector embeddings)
- Federated / unified search across sources
- Saved searches
- Item detail: availability, holds, waitlist timeline, wayfinding modal
- Mood browsing, new arrivals, curated shelves, release radar
- Series, story arcs, reading orders (comics/manga)
- OPDS feed, BIBFRAME linked-data view
- Staff picks, staff reviews (public-facing)

### Account & Auth
- Registration, email verification, magic link, OAuth (Google), TOTP 2FA
- Forgot/reset password
- Account page: checkouts, holds, ebooks, favorites, history, notifications
- Security: activity log, alerts, recovery options, connected accounts
- Family account linking (child/dependent accounts), household management
- Guest pass form

### Holds & Checkout
- Place/manage holds (physical + digital), pickup authorization
- Renew, checkout history
- Streamlined self-checkout
- Interlibrary loan requests

### Reading Shelf
- Reading status tracking (want to read / reading / finished)
- Reading goals, milestones, confetti
- Reading logs and minutes tracking
- Reading insights dashboard
- Export shelf data

### Reading Programs
- Summer reading and other reading programs (booklist + paper-log modes)
- Challenges, leaderboards, certificates (with public verify URL)
- Achievements, Read-to-Reduce, family reading challenges

### Digital Resources
- Ebooks (browse, borrow, manage)
- Project Gutenberg integration
- Streaming video/audio (feature-flagged)
- Database subscriptions directory

### Events & Programs
- Events calendar (list/agenda/calendar views), registration
- Event series, AMA sessions, book clubs
- iCal export

### Community
- Youth hub: homework help, coding, teen mentors, makerspace, community archives
- Parent onboarding wizard (intake, care coordinator, home visits, childcare, connection groups)
- Teacher portal (reading lists, family challenges, library visit scheduling)
- Makerspace: equipment catalog, booking, certifications, workshops
- Immigrant services
- Adult-literacy tutor matching (learners, tutors, matching, outcomes)

### Tech Help
- Self-service guides (WiFi, printing, email, holds, etc.)
- Computer session timer and reservations
- Room booking
- Offline sync

### Feature-Flagged Public Portals
- Legal resources hub (calculators, document wizard, bankruptcy browser, court directory, clinics)
- Genealogy workspace (family tree, DNA links, timeline, collaborators)
- Indie author/MetisLib catalog integration
- Home delivery enrollment
- AI tools hub and AI chat
- Learning platform with AI literacy labs ("Real or Fake?", "Who Wrote This?", "Fix This Prompt", "AI Said What?")

### Other Public Pages
- Branches/locations finder with detail modal
- About, contact, donate, careers, accessibility statement
- Ban tracker (+ subscriptions), intellectual freedom/advocacy pages
- Patron reports dashboard, public library statistics
- Knowledge base / FAQ chatbot
- Emergency operations portal (11 sub-pages)
- Setup wizard (first-run)

---

## Staff Portal

### Circulation
- Full circ desk: checkout, check-in, renew
- Hold shelf, transit, book drop, fast book drop
- Lost/damaged items, claims returned, mending queue, repairs
- Fine management: payments, payment plans, waivers, receipts, analytics
- Cash drawer, print notices, end-of-day reconciliation
- Overdue management
- Customer-facing display

### Cataloging
- Item form, bulk actions, catalog queue, processing queue
- Manga and comics cataloging (series, volumes, issues, story arcs)
- MARC batch import, authority lookup, local authority control
- Z39.50 copy cataloging
- BIBFRAME/linked data, SPARQL query interface
- LCSH browsing
- Series management, work relationships
- Inventory management, mobile inventory scan
- RFID management (readers, tags, auto-scan, security, simulator)
- SIP2 interface

### Patron Management
- Patron search + advanced filters
- Patron profile: checkouts, holds, fines, history, communication, settings
- Block/unblock, photo upload, card print, patron merge
- Bulk operations (block, waive fines, notify)
- Patron segmentation and targeted messaging
- Estate management, GDPR deletion management
- Card application processing

### Acquisitions
- Purchase orders, EDI invoices/shipments
- Budget intelligence, vendor comparison/performance
- Selection list management, enrichment suggestions
- Acquisition funds, vendor directory, order templates
- Pre-orders and release radar management

### Reports & Analytics
- Circulation, fines, lost/damaged, financial reports
- Home delivery, makerspace, room, streaming reports
- PLS export, usage statistics
- Audit log viewer, audit reversal
- Journey analytics, staff analytics
- QR analytics, website analytics

### Outreach
- Bookmobile management
- Home delivery management and volunteers
- Community outcomes dashboard
- Marketing campaigns (email, SMS, event marketing)
- School impact reporting, partnership tiers
- Reading ambassadors, bundle distribution
- Storytime management, attendance tracking

### Staff Operations
- Dashboard: desk mode, hold queue status, item lifecycle, library stats, theme velocity
- Command palette, keyboard shortcuts
- Staff directory, knowledge base, message board
- PTO management, shift swap board
- Focus time scheduler, end-of-shift/day checklists
- Panic alert, threat response, safety tools, medical emergency alerts
- Shelf reading, found items management
- ILL management
- Serials management
- Staff training dashboard, onboarding, policy acknowledgment
- Staff picks lists, curated recommendations
- Review management, content flags moderation
- Book challenges, book clubs, teen volunteers
- Staff wellness suite: joy capture, positivity, perfectionism antidotes, professional-judgment support
- Nudges, engagement surveys, cohorts

---

## Admin Portal
- Library config: site settings, feature toggles, community resources
- Users, roles and permissions, session management
- AI settings: models, tools, agents, guardrails, usage limits, test console
- Circulation policy (rules, patron/staff settings, financial settings)
- Compliance: CIPA, ban tracker, law enforcement requests, public records, state compliance
- System health: API status, cache, storage, scheduler, virus scan, security
- Integrations: SIP2, Z39.50, EDI, semantic search, home delivery settings
- Consortium management (members, shared resources, billing, white-label)
- Data export, migration wizard, PLS export
- Learning platform: courses, lessons, learning paths, external resources
- Strategic planning: goals, milestones, import/export, analytics
- Branding, meta tags, social sharing, link health checker
- Digital signage
- Carbon / sustainability metrics
- Beta invites, computers management, legal admin

---

## Board Portal (feature-flagged)
- Dashboard, member gallery
- Meetings, prep pages, documents with version history, minutes
- Motions with voting, committees, action items
- Public comments (per meeting, with active comment period banner)
- Board reports, scheduled report generation, PDF exports
- Attendance tracking, board notices
- Demo/walkthrough mode for new board members

---

## Workflow Automation & AI

### Workflow automation engine (staff-facing, rule-based)
- Triggers: event, schedule, manual
- Step types: action, condition, delay, notification (branching + waits)
- Actions: send email/SMS, create transit, update status, generate report, assign
  task, place/cancel hold, flag account, send to collections, auto-order copies,
  generate MARC record, check duplicates, assign shelf location, move to hold shelf,
  notify next in queue
- Prebuilt templates: Overdue Notice Escalation, Hold Fulfillment, New Item Processing
- Deterministic (not LLM-driven); executions tracked with per-step status

### AI assistants (Ollama / llama3.2)
- Chat personalities with system prompts (Ernie, Reader Advisory, Writing Assistant)
- FAQ chatbot + staff reference chat, grounded on a knowledge-base pipeline (RAG)
- Admin console: agents, tools, guardrails, usage limits, test console
- Single-shot generate/chat with retrieval — **not** an autonomous tool-calling agent loop

### Constraint-solver scheduling
- Hard/soft-constraint optimizer for staff shifts (intelligent scheduling, fair scheduling)
- Compliance-deadline and tech-booking schedulers via a unified scheduler

---

## Infrastructure
- Feature flags (per-library enable/disable on any major feature — 70 module toggles)
- RBAC (patron / staff / admin / board_member / director / super_admin)
- Dual audit system: DB-queryable ops log + HMAC-signed tamper-evident file log
- Redis caching, pgvector semantic search
- WebSocket support, SMS/email notifications
- OAuth (Google), OPDS, SIP2, Z39.50, RFID, EDI, MARC, BIBFRAME/SPARQL
- Multi-branch support
- Consortium/white-label support
- PTO fair scheduling
- Demo mode
