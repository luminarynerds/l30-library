# Reports

Sidebar "Reports" group. Most pages are read-only aggregations — safe to
visit, slow to load when you ask for a wide date range. Exports (CSV/PDF)
are watermarked and audit-logged.

---

### Report Hub (`/staff/report-hub`)
The landing page for everything reporting. Tile-grid of every report
available, grouped by category (circulation, financial, programs,
collection, compliance). Use this when you know what question you have
but not where the report lives.

### Circulation Reports (`/staff/reports`)
Analytics and statistics for library operations: checkouts, renewals,
returns, holds fulfilled, by branch and date range. The default operational
report most staff visit weekly. Long date ranges are slow — narrow the
window if it hangs.

### Unified Reports (`/staff/reports/unified`)
Cross-domain report combining circulation, programs, fines, and patron
activity into one view. Useful for board packets and state-annual prep.

### Custom Report Builder (`/staff/custom-reports`)
Build, preview, and save custom reports. Pick a data source, choose
fields, filter, save. Saved reports show up in the Report Hub for the
author and anyone they share with. Heavy queries: preview first with a
narrow filter.

### Report Audit Log (`/staff/reports/audit-log`)
Track who generated which reports and when. Required for compliance
review of PII-sensitive reports. Read-only.

### Financial Reports (`/staff/admin/financial`)
Revenue, expenses, and fund management. AdminAuth + `board_features_enabled`.
The canonical board-facing financial report.
See also: [Treasurer Dashboard](admin-settings.md#treasurer-dashboard-staffadmintreasurer), [Board Treasurer](board.md#board-treasurer-dashboard-staffadminboard-treasurer).

### Financial Config (`/staff/admin/financial-config`)
Redirects to Circulation & Policy with the financial hash anchor.
Set fine rates, fee schedules, refund rules.
See also: [Circulation & Policy](admin-settings.md#circulation--policy-staffadmincirculation-policy).

### Material Costs (`/staff/admin/material-costs`)
Redirects to Circulation & Policy (material-costs hash). Per-format
replacement cost defaults that feed lost/damaged charge calculations.

### Annual Reports (`/staff/admin/annual-reports`)
Automated state annual report generation with pre-populated statistical
data. `board_features_enabled` + admin/director/staff. Review every field
before submitting to the state — auto-population uses the prior FY's
aggregates and will not catch policy changes mid-year.

### Website Traffic (`/staff/admin/website-analytics`)
Pageviews, active visitors in last 5 min, top pages, referrers. Same
underlying data as Website Analytics under Admin; surfaced under Reports
for staff who do not have full admin access. AdminAuth-gated.

### Lost & Damaged Reports (`/staff/reports/lost-damaged`)
Lost and damaged item charges, write-offs, and recovery rates. Feeds
the operational `/staff/lost-damaged` queue.

### Makerspace Reports (`/staff/reports/makerspace`)
Equipment usage, project counts, materials consumed. Requires
`makerspace_enabled`.

### Room Reservation Reports (`/staff/reports/rooms`)
Room booking volume, no-shows, peak times. Requires `meeting_rooms_enabled`.

### Streaming Reports (`/staff/streaming/reports`)
Streaming media usage and bandwidth. Requires `streaming_enabled`.

### Usage Statistics (`/staff/usage-statistics`)
High-level usage dashboard (total checkouts, active patrons, top items).
Lighter than the full Analytics dashboard; load it first when you just
need round numbers.

### Cohort Analysis (`/staff/analytics/cohorts`)
Retention/engagement cohorts (e.g. "patrons who signed up in Jan 2026
and their checkout activity over time"). Used for outreach analysis.

### School Impact Reporting (`/staff/admin/school-impact`)
School-by-school comparison report for partnership reporting.
AdminAuth required.

### Community Outcomes (`/staff/admin/community-outcomes`)
Cross-cutting impact metrics across all library programs and services.
`community_outcomes_enabled`. Feeds grant reporting.

### Home Delivery Reports (`/staff/home-delivery/reports`)
Home delivery activity: routes, volumes, missed deliveries.
`home_delivery_enabled`.
