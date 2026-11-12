# Library

Sidebar "Library" group plus related sub-groups (Volunteers, Scheduling,
Parent Onboarding, Courses). These are the community-facing operational
surfaces. Most are gated by `community_features_enabled` and per-feature
flags.

---

### Library Hub (`/staff/library-hub`)
Landing page for library/community operations. Tile-grid of events,
programs, services, training, computers, reference chat. Use as your
map when running floor operations.

### Events (`/staff/events`)
Event management: create, edit, publish, manage rosters. Requires
`events_enabled`. Each event has a roster at
`/staff/events/:eventId/roster`. Capacity, waitlists, and registration
forms configured per event.

### Programming Partners (`/staff/program-partners`)
External presenter/partner directory used when creating events.
Requires `events_enabled`. Keeping this current makes event planning
much faster.

### Program Planning (`/staff/program-planning`)
Multi-event planning workspace (e.g. a summer reading series).
Requires `events_enabled`.

### Blog (`/staff/blog`)
Staff blog editor (L30 blog module — not a personal blog, not the
Unhinged Librarian site). TipTap-based rich editor. Drafts are autosaved.

### Reading Programs (`/staff/admin/reading-programs`)
Manage reading programs: tiers, prizes, rules.
Requires `reading_programs_enabled`. Patron-facing program is separate;
this is the curator/editor view.
See also: [admin-settings.md](admin-settings.md#reading-programs-staffadminreading-programs).

### Book Clubs (`/staff/admin/book-clubs`)
Book club groups, schedules, discussion materials.
Requires `book_clubs_enabled`.

### Services / Home Delivery (`/staff/home-delivery`)
Home delivery management: requests, routes, deliveries, volunteers.
Requires `home_delivery_enabled`. Sub-pages: `/deliveries`, `/volunteers`,
`/reports`. Settings live at `/staff/admin/home-delivery-settings`.

### Training (`/staff/training`)
Staff training dashboard: assigned courses, progress, certifications.
Requires `training_modules_enabled`.

### Library Visits (`/staff/library-visits`)
Manage scheduled school/group visits to the library (or staff-led
visits out). Requires `learning_platform_enabled`.

### Onboarding (`/staff/onboarding`)
New-patron onboarding workflows: welcome series, card activation
follow-up, first-checkout nudges.

### Computers (`/staff/computers`)
Operational view of public-access computers: see who's logged in,
end sessions, top up time. `tech_services_enabled` required. The
admin config lives at `/staff/admin/computers`.
See also: [Admin Computers](admin-settings.md#computers-staffadmincomputers).

### Reference Chat (`/staff/reference-chat`)
Staff interface for the patron reference chat (the AI-assisted ask-a-
librarian channel). Requires `ai_tools_enabled`. Staff can intervene
in any live conversation and take over from the agent.

---

## Volunteers

### Volunteers (`/staff/volunteers`)
Volunteer roster, applications, hours, assignments.
Requires `volunteers_enabled`.

### Teen Volunteers (`/staff/teen-volunteers`)
Teen volunteer program with parent-consent + hours-for-school-credit
workflows. Requires `volunteers_enabled`.

---

## Scheduling

### Scheduling Hub (`/staff/fair-scheduling`)
Fair-scheduling dashboard: published schedule, open shifts, swap
requests. Requires `staff_scheduling_enabled`.

### Generate Schedule (`/staff/fair-scheduling/generate`)
Run the schedule generator for an upcoming period. Pulls from
profiles, preferences, and call-outs. Always review before publishing —
the generator is good, not infallible.

### Profiles (`/staff/fair-scheduling/profiles`)
Per-staff scheduling profile: role, qualifications, max hours.

### Preferences (`/staff/fair-scheduling/preferences`)
Staff preference inputs (preferred shifts, unavailable days).
Staff edit their own; admins can edit anyone.

### Call-Outs (`/staff/fair-scheduling/call-outs`)
Record and resolve call-outs/absences. Reassignment options surface
inline based on coverage rules.

### Fatigue (`/staff/fair-scheduling/fatigue`)
Surface staff approaching fatigue thresholds (too many closing-opening
shifts, too many consecutive days). Use before publishing the next
period.

### Explanations (`/staff/fair-scheduling/explanations`)
Why-did-the-generator-do-that view. Per-shift rationale traces from
the optimizer. Use when staff push back on an assignment.

### Payroll (`/staff/fair-scheduling/payroll`)
Pay-period summary feeding to payroll. Uses Pay Rates + Timesheets.
Lock the period before exporting.

### Focus Time (`/staff/focus-time`)
Block focus time on the schedule (no patron-facing duties).
Requires `staff_wellness_enabled`.

---

## Parent Onboarding

`parent_onboarding_enabled` required for all of these. Used by libraries
that run new-parent welcome programs.

### Overview (`/staff/parent-onboarding`)
Dashboard for the parent onboarding program: active families, upcoming
sessions, resource usage.

### Childcare (`/staff/parent-onboarding/childcare`)
Manage on-site childcare provided during parent programming.

### Connection Groups (`/staff/parent-onboarding/connection-groups`)
Cohort groupings (e.g. "Spring 2026 newborns") used for follow-up.

### Home Visits (`/staff/parent-onboarding/home-visits`)
Schedule and record in-home outreach visits.

### Resources (`/staff/parent-onboarding/resources`)
Curated parent resource library (books, kits, links).

---

## Courses (Admin)

Sidebar "Courses" group. `learning_platform_enabled` required.

### Course Templates (`/staff/admin/courses/templates`)
Pre-built course structures. Start from one, customize, save as a new
course. Saves a lot of time vs building from scratch.

### Course Import (`/staff/admin/courses/import`)
Bulk import courses from JSON. Useful for migrating from another LMS or
for sharing course definitions across libraries.

### Course Feedback (`/staff/admin/courses/feedback`)
Review and manage feedback submitted by patrons on courses and lessons.
Triage signal for what's working and what's confusing.

### Manage Courses (`/staff/admin/courses`)
Create, edit, and organize courses. Course form, lesson editor, module
management. AdminAuth-adjacent surfaces.

### Learning Paths (`/staff/admin/learning-paths`)
Multi-course learning paths (e.g. "Digital Literacy Track"). Sequenced
courses with prerequisites.

### Course Sessions (`/staff/admin/sessions`)
Scheduled instructor-led sessions of a course (vs self-paced).
