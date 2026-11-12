# Feature Flags Reference

**Audience:** library administrators (you don't need to write code to use this doc).

This page lists every organization-wide boolean feature flag in L30, what it controls, and what happens when you flip it. Use it when you're deciding whether to turn a module on for your library, or when something just disappeared from a patron's screen and you need to figure out which switch did it.

---

## What feature flags are

Feature flags are on/off switches that turn whole sections of L30 on or off for your library. They live in a single database row (the `organization_features` table) and apply to your entire organization — there is no per-branch or per-user override.

When a flag is **off**:

- Backend API endpoints guarded by that flag refuse requests with HTTP 403 ("This feature is not enabled for your organization").
- Frontend sidebar links annotated with that flag disappear from staff navigation.
- Some features hide menu items but leave underlying data intact — turning a flag back on restores access to whatever was there.

## Where to toggle them

- **Admin UI:** `/staff/feature-flags` (requires admin role).
- **Setup wizard:** initial values are chosen during library onboarding.
- **API (developers only):** `PATCH /api/v1/organization-features`.

## Default state

All flags default to **on** except where noted below. New libraries start with nearly everything enabled; turn off what you don't use rather than turning on what you do.

## Safe-to-toggle-mid-day classification

- **Yes** — patrons or staff currently using the feature will see it disappear on next page navigation. No data is lost.
- **Caution** — in-progress workflows (a holds queue, a checkout in flight, a notification batch) may abort or behave inconsistently. Prefer flipping outside business hours.
- **Coordinate first** — flipping affects external integrations or scheduled jobs. Talk to whoever runs those before toggling.

## Recovery

Almost all flags are non-destructive: turning a flag off then on later restores the feature with all its underlying data. Exceptions are called out per-flag.

---

## Flag reference (alphabetical)

### `acquisition_enabled`
- **Gates:** Acquisitions module — vendor orders, EDI ordering, invoice processing.
- **Default:** On.
- **Mid-day:** Caution. EDI polling jobs may abort mid-cycle.
- **Recovery:** Re-enable. In-flight orders remain in the database; resume from the orders queue.

### `aggregate_trending_enabled`
- **Gates:** Aggregate "what neighbors are reading" trending rails on `/discover`.
- **Default:** On. Aggregate-only with a k-anonymity floor and per-patron opt-out; the `/discover` subhead promises this rail, so the flag exists only as a system-level kill switch (e.g. if a patron-privacy concern surfaces).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `ai_tools_enabled`
- **Gates:** Staff-facing AI assistant tools in the sidebar (reading recommendations helper, summarization, reference assist).
- **Default:** On.
- **Privacy note:** Patron-facing AI agents are separately controlled by the `DISABLE_AGENT_LLM` environment variable, not this flag. With LLM disabled, patron AI falls back to rule-based responses.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `ama_enabled`
- **Gates:** "Ask Me Anything" community Q&A surface.
- **Default:** **Off** (opt-in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable. Existing questions remain in the database.

### `banned_books_tracking_enabled`
- **Gates:** Banned/challenged-books tracking, challenge logging, ALA reporting export.
- **Default:** On.
- **Privacy note:** Patron names are never stored in challenge records — only staff who logged the challenge.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `beta_features_enabled`
- **Gates:** Opt-in experimental features that haven't been promoted to general availability.
- **Default:** **Off**.
- **Mid-day:** Yes, but expect rough edges from any beta feature you enable.
- **Recovery:** Re-enable; beta state is preserved.

### `board_features_enabled`
- **Gates:** Library board module — meeting minutes, packet builder, public board pages, trustee onboarding.
- **Default:** On.
- **Mid-day:** Yes. Public board pages 404 immediately when off.
- **Recovery:** Re-enable. Minutes and packets remain intact.

### `book_club_history_enabled`
- **Gates:** Book club discussion archive — full-text search across past club discussions.
- **Default:** **Off** (opt-in per library while the feature bakes in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable. Archived discussions are retained while off.

### `book_club_waitlist_enabled`
- **Gates:** FIFO waitlist and capacity signals on book club sign-ups.
- **Default:** **Off** (opt-in per library while the feature bakes in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `book_clubs_enabled`
- **Gates:** Book club management, club rosters, club-meeting calendar.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `circulation_hold_trap_card_enabled`
- **Gates (UI only):** The "hold-trap" card shown to staff on the check-in success screen when the item just checked in is the next available copy for an active hold.
- **Default:** On.
- **Note:** Frontend-only toggle — no backend `require_circulation_hold_trap_card_enabled` guard attaches to any router. Declared in the guard registry only so the admin Feature Toggles page renders the switch.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `circulation_print_slip_enabled`
- **Gates:** Printable and emailable post-checkout slip toolbar at the staff circulation desk.
- **Default:** On — fundamental library workflow.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `cohort_enabled`
- **Gates:** Learning-path cohorts — opt-in patron pair-up with a shared discussion wall.
- **Default:** **Off** (opt-in per library while the feature bakes in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `collection_management_enabled`
- **Gates:** Collection development workflows — selection lists, weeding queues, gap analysis.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable. Selection lists remain intact.

### `community_features_enabled`
- **Gates:** Community partnerships module, partner directory, MOU tracking.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `community_outcomes_enabled`
- **Gates:** Community-impact outcome tracking and reporting.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `compliance_enabled`
- **Gates:** Compliance dashboard — CIPA, COPPA, records-retention tracking.
- **Default:** On.
- **Privacy note:** Disabling this hides the dashboard but does not stop the underlying retention jobs. Compliance settings (e.g. retention windows) are stored elsewhere.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `customer_display_enabled`
- **Gates (UI only):** Patron-facing customer display (second monitor) at the staff circulation desk, plus its desk header link (`/staff/circulation/display`).
- **Default:** **Off** — most desks don't have a second monitor; opt-in per library.
- **Note:** Frontend-only toggle — no backend `require_customer_display_enabled` guard attaches to any router. Declared in the guard registry only so the admin Feature Toggles page renders the switch.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `digital_access_enabled`
- **Gates:** Digital-access module — public computer reservations, wifi vouchers, hotspot lending UI.
- **Default:** On.
- **Mid-day:** Caution. Active computer reservations are unaffected; the queue UI disappears for staff.
- **Recovery:** Re-enable.

### `email_notifications_enabled`
- **Gates:** Outbound email — holds-ready notices, overdue reminders, account confirmations, newsletters.
- **Default:** On.
- **Coordinate first:** Turning this off silences ALL transactional email. Patrons will not receive holds-ready notices.
- **Mid-day:** Caution. Notifications queued before toggling may or may not send depending on worker timing.
- **Recovery:** Re-enable; queued notifications resume sending.

### `emergency_services_enabled`
- **Gates:** Emergency-response coordination module (drill logs, incident reports, contact trees).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `events_enabled`
- **Gates:** Public events calendar, event registration, attendance tracking.
- **Default:** On.
- **Mid-day:** Caution. Patrons mid-registration may hit a 403; existing registrations are preserved.
- **Recovery:** Re-enable.

### `family_card_enabled`
- **Gates:** Household/family-card linking (`/households`) — one card covering multiple family members.
- **Default:** On.
- **Mid-day:** Caution. Households mid-checkout under a shared card may hit a 403; existing linkages are preserved.
- **Recovery:** Re-enable.

### `faq_chatbot_enabled`
- **Gates:** Patron-facing FAQ chatbot widget on the public site.
- **Default:** On.
- **Privacy note:** Chat transcripts are stored for staff review unless retention is configured otherwise.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `financial_reports_enabled`
- **Gates:** Financial reports module — budget snapshots, fund accounting summaries, annual report financials.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `for_teachers_enabled`
- **Gates:** Educator account features — class card management, classroom-loan bulk checkout, lesson-plan integrations.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable. Existing class cards remain valid.

### `free_ebooks_enabled`
- **Gates:** Free public-domain ebook catalog (Standard Ebooks, Project Gutenberg integration).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `front_desk_enabled`
- **Gates (UI only):** Public-facing entry points for library card signup (`/get-started`), branches/hours pages, and circulation-related navigation (header CTAs, sidebar link, mobile menu, hero highlights). Backend circulation endpoints stay live so staff can keep working.
- **Default:** On.
- **Note:** This is a UI-only toggle by design — hiding patron-facing entry surfaces without disabling circulation operations. There is intentionally no `require_front_desk_enabled` backend guard; staff must be able to circulate items regardless of whether the public CTAs are shown.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `gamification_enabled`
- **Gates:** Patron gamification — points, badges, leaderboards, reading streaks.
- **Default:** On.
- **Privacy note:** Disabling hides leaderboards; underlying points/badges history is retained.
- **Mid-day:** Yes.
- **Recovery:** Re-enable; history reappears.

### `genealogy_enabled`
- **Gates:** Genealogy research module — local-history collections, obituary index UI.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `home_delivery_enabled`
- **Gates:** Home-delivery program — patron self-enrollment, delivery routes, driver app.
- **Default:** On.
- **Mid-day:** Caution. Active routes for today should be allowed to complete; new requests will be refused.
- **Recovery:** Re-enable.

### `home_visit_day_plan_enabled`
- **Gates:** Map-aware "Today's route" day-plan view for staff home visits (parent-onboarding home-visit program).
- **Default:** **Off** — pending production validation of a real day plan and confirmation that Nominatim public-instance geocoding volume stays within its usage policy.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `home_visit_safety_enabled`
- **Gates:** Lone-worker safety check-in for staff conducting home visits (parent-onboarding home-visit program).
- **Default:** **Off** — pending library review of the supervisor-notification path and cron schedule.
- **Mid-day:** Coordinate first. Staff relying on this for a visit in progress should finish the visit before you toggle.
- **Recovery:** Re-enable.

### `ill_enabled`
- **Gates:** Interlibrary loan — patron ILL requests, OCLC integration, ILL queue.
- **Default:** On.
- **Coordinate first:** OCLC integration polling stops when off. Outstanding ILL requests remain but no new ones can be filed.
- **Mid-day:** Caution.
- **Recovery:** Re-enable; polling resumes on the next worker tick.

### `impact_measurement_enabled`
- **Gates:** Community-impact measurement reporting (Phase 1 governance scaffolding).
- **Default:** **Off** (opt-in per library).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `indie_platform_enabled`
- **Gates:** Indie-author and small-press catalog surface (including MetisLib integration where configured).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `learning_platform_enabled`
- **Gates:** Patron learning platform — course catalog, course enrollments, certificates.
- **Default:** On.
- **Mid-day:** Yes. Active learners keep access to enrolled courses until next navigation.
- **Recovery:** Re-enable.

### `legal_services_enabled`
- **Gates:** Legal services referral module — partner directory, intake forms.
- **Default:** On.
- **Privacy note:** Intake forms may contain sensitive data; ensure retention policy is set before enabling.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `literacy_programs_enabled`
- **Gates:** Adult and family literacy programs — tutor matching, level tracking.
- **Default:** On.
- **Privacy note:** Literacy level is sensitive — only show to staff with the literacy-coordinator role.
- **Mid-day:** Yes.
- **Recovery:** Re-enable. (Note: a literacy UI surface was removed by a dead-code sweep historically; verify your sidebar shows the link after enabling.)

### `makerspace_enabled`
- **Gates:** Makerspace module — equipment reservations, safety training records, badge tracking.
- **Default:** On.
- **Mid-day:** Caution. Active reservations are preserved; new ones refused.
- **Recovery:** Re-enable.

### `marketing_enabled`
- **Gates:** Marketing module — campaign builder, UTM tracking, social-share counters.
- **Default:** On.
- **Mid-day:** Yes. In-flight campaigns continue running on the scheduler.
- **Recovery:** Re-enable.

### `meeting_rooms_enabled`
- **Gates:** Meeting-room booking — public booking form, room calendar, deposit handling.
- **Default:** On.
- **Mid-day:** Caution. Existing bookings preserved; new requests refused.
- **Recovery:** Re-enable.

### `migration_enabled`
- **Gates:** Intended for data-migration tooling (importing from a previous ILS).
- **Default:** On.
- **Wiring note:** No backend `require_migration_enabled` guard and no sidebar entry found (as of 2026-05-17). This flag exists in the model but does not currently gate any surface. See "Wiring-questionable flags" below.
- **Mid-day:** Yes (no effect observed).
- **Recovery:** N/A — flag is effectively a no-op until wired.

### `notifications_enabled`
- **Gates:** General in-app notifications (bell icon, notification center).
- **Default:** On.
- **Distinct from `email_notifications_enabled`:** this controls IN-APP delivery only.
- **Mid-day:** Yes. Unread notifications remain; the panel just hides.
- **Recovery:** Re-enable.

### `outreach_enabled`
- **Gates:** Outreach module — bookmobile schedule, partner-site visits, outreach-event tracking.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `parent_onboarding_enabled`
- **Gates:** Parent/guardian onboarding flow for child-account creation.
- **Default:** On.
- **Privacy note:** This flow collects COPPA-relevant parent consent. Do not disable mid-onboarding for a family.
- **Mid-day:** Caution.
- **Recovery:** Re-enable. In-flight onboardings must be restarted.

### `patron_engagement_enabled`
- **Gates:** Patron-engagement metrics dashboard for staff (recency, frequency, last-seen tracking).
- **Default:** On.
- **Privacy note:** Aggregates patron activity for staff view; surface to small teams only.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `patron_portal_enabled`
- **Gates:** The patron-facing portal as a whole — "My Account," renewals, holds, history.
- **Default:** On.
- **Coordinate first:** Disabling this effectively takes patrons offline. Use only during scheduled maintenance.
- **Mid-day:** **Avoid.**
- **Recovery:** Re-enable. Patron data is untouched; only UI access was gated.

### `pickup_authorization_enabled`
- **Gates:** Childcare authorized-pickup enforcement — parents list adults authorized to pick up a child; the staff checkout endpoint validates the named pickup person against that list.
- **Default:** **Off.** Existing childcare registrations were created without a pickup list; flipping enforcement on for a library that hasn't collected pickup lists yet would block checkouts at the desk.
- **Coordinate first:** Confirm your childcare registrations have pickup lists on file before enabling.
- **Mid-day:** Caution.
- **Recovery:** Re-enable.

### `printing_enabled`
- **Gates:** Public-printing module — print release stations, quota management, payments.
- **Default:** On.
- **Mid-day:** Caution. In-progress print jobs may not release.
- **Recovery:** Re-enable. Quotas preserved.

### `processing_queue_enabled`
- **Gates:** Acquisitions/processing queue UI (the "what's on the cart" view for techs).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `reading_goals_enabled`
- **Gates:** Personal reading-goal tracking (books/year, minutes/day).
- **Default:** **Off** (opt-in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `reading_programs_booklist_enabled`
- **Gates:** Curated book-list feature on reading programs.
- **Default:** **Off** (opt-in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `reading_programs_enabled`
- **Gates:** Summer reading programs and other structured reading programs.
- **Default:** On.
- **Mid-day:** Caution if a program is actively running and patrons are logging today.
- **Recovery:** Re-enable; progress retained.

### `reading_programs_paper_log_enabled`
- **Gates:** Paper reading-log / kiosk claim-code path for reading programs (a patron logs reading on paper; staff or a kiosk apply it to their account later).
- **Default:** **Off** (opt-in).
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `reading_shelf_enabled`
- **Gates:** Patron "shelf" (currently-reading / read / want-to-read lists).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable; shelves retained.

### `saved_searches_enabled`
- **Gates:** Patron saved catalog searches and new-arrival alerts.
- **Default:** **Off** (rolls out per-library once notifier delivery is verified).
- **Mid-day:** Yes.
- **Recovery:** Re-enable; saved searches retained.

### `self_checkout_enabled`
- **Gates:** Self-checkout kiosk endpoints and PWA.
- **Default:** On.
- **Coordinate first:** If you run a physical self-checkout station, disabling this will stop the station from completing transactions.
- **Mid-day:** Caution.
- **Recovery:** Re-enable.

### `serials_enabled`
- **Gates:** Serials/periodicals management — subscription tracking, issue check-in.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `shelf_data_export_enabled`
- **Gates:** Patron's ability to export their own shelf data (CSV/JSON).
- **Default:** On.
- **Privacy note:** This is a patron right-of-access feature; keep enabled unless legal counsel advises otherwise.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `signage_enabled`
- **Gates:** Digital signage CMS — slide builder, display assignment.
- **Default:** On.
- **Mid-day:** Yes. Active signage displays continue showing the last loaded slide loop until they reconnect.
- **Recovery:** Re-enable.

### `sip2_rfid_enabled`
- **Gates:** SIP2 / RFID integrations (3M, Bibliotheca, etc.).
- **Default:** On.
- **Coordinate first:** Disabling breaks the link between L30 and your self-check / security-gate hardware.
- **Mid-day:** **Avoid** if vendor hardware is in use.
- **Recovery:** Re-enable; integrations resume on the next polling cycle.

### `staff_scheduling_enabled`
- **Gates:** Staff scheduling module — shift calendar, swap requests, time-off.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable. Schedules retained.

### `staff_wellness_enabled`
- **Gates:** Staff-wellness tools — anonymous check-ins, EAP resource links.
- **Default:** On.
- **Privacy note:** Anonymous check-in responses are aggregated; never tied to individuals.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `storytime_enabled`
- **Gates:** Storytime registration, attendance, themed-program planning.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `strategic_planning_enabled`
- **Gates:** Strategic-planning module — goals, KPIs, board reports.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `streaming_enabled`
- **Gates:** Streaming-media surface (Kanopy/Hoopla-style links and analytics).
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `tech_services_enabled`
- **Gates:** Technical services dashboard — cataloging queues, authority work.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

### `training_modules_enabled`
- **Gates:** Staff training module — course assignments, due dates, certificates.
- **Default:** On.
- **Mid-day:** Yes.
- **Recovery:** Re-enable; assignments retained.

### `volunteers_enabled`
- **Gates:** Volunteer management — applications, hour logging, recognition.
- **Default:** On.
- **Privacy note:** Volunteer applications may contain background-check status; access already gated by role.
- **Mid-day:** Yes.
- **Recovery:** Re-enable.

---

## Important distinctions

### Essentials mode is not the accessible layer
The patron Essentials mode is an **opt-in calm/low-stimulation experience**, not the default-accessible version of L30. The default patron pages must independently meet WCAG AA. Do not assume turning on Essentials mode is how you "make L30 accessible."

### Patron AI is controlled by an env var, not a flag
`ai_tools_enabled` controls **staff** AI tools. Patron-facing AI agents are governed by the `DISABLE_AGENT_LLM` environment variable on the backend container, which is currently set to disable the LLM in favor of rule-based responses (pending GPU hardware). Flipping `ai_tools_enabled` will not re-enable patron AI.

### Email vs in-app notifications
`email_notifications_enabled` and `notifications_enabled` are independent. Email controls outbound mail; the other controls the in-app bell icon and notification center.

---

## Wiring-questionable flags

As of 2026-05-17, the following flags exist in the `OrganizationFeatures` model but appear to be missing one or more of the standard touchpoints (model, schemas, service, guard, alembic, context, admin UI, setup wizard):

| Flag | Backend `require_*` guard? | Sidebar entry? | Notes |
|------|----------------------------|----------------|-------|
| `migration_enabled` | Yes | Admin-only routes (`/staff/admin/migration`, `/staff/admin/migration-project`) | Gates the migration wizard + multi-phase migration project routers. Admin-only. |
| `front_desk_enabled` | No (by design) | Yes | UI-only toggle — hides public-facing entry surfaces (get-a-card CTA, branches/hours nav, mobile menu) without disabling circulation. Staff endpoints must stay live regardless. See section above. |

If you find another flag where toggling has no observable effect, file a bug — that's a wiring gap, not your imagination.

---

## When a flag isn't documented here

If a flag exists in the database but is missing from this page, check the canonical model file:

```
backend/app/models/organization_features.py
```

Class `OrganizationFeatures` is the source of truth. If you find a flag there that's not on this page, please update this doc — short rows are better than missing rows.

For the eight standard touchpoints required when adding a NEW flag (model, schemas, service, guard, alembic, context, admin UI, setup wizard), see the engineering memory note `feedback_l30_feature_flag_add_checklist` or ask a developer.
