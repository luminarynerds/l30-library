---
title: L30 staff training docs
audience: all-staff
diataxis: reference
estimated_time: 5 min
last_reviewed: 2026-05-14
app_routes: []
---

# L30 staff training docs

## What this is

Documentation for library staff using L30. Organized by role. Start with the [first-day orientation](getting-started/orientation.md), then move to your role-specific docs.

These docs assume you're new to L30 -- maybe new to libraries entirely, or coming from a different ILS. The voice is constructive practitioner: plain language, real procedures, no marketing. If a doc tells you something that doesn't match what you see on the screen, the doc is wrong and we want to know; file an issue or tell `{{head_of_circulation_name}}`.

## Where to start

| I am a... | Start here |
|------|------|
| Someone new to L30 | [Welcome to L30 -- first-day orientation](getting-started/orientation.md) |
| Circulation desk worker | [First-day orientation](getting-started/orientation.md), then [Circulation desk role orientation](roles/circulation/orientation.md), then keep [Circulation daily tasks](roles/circulation/daily.md) open during your shift |
| Tech-services / cataloger | [First-day orientation](getting-started/orientation.md). Role-specific docs are coming in P2; until then, see the [glossary](getting-started/glossary.md) entries for MARC, BIBFRAME, RDA, LCSH, OCLC, authority records, holdings record |
| Youth-services librarian | [First-day orientation](getting-started/orientation.md). Role-specific docs are coming in P1 |
| Admin / branch manager | [First-day orientation](getting-started/orientation.md). Role-specific docs are coming in P1 |
| Someone who does all the jobs (solo librarian, small branch) | Read every orientation as it ships. Order doesn't matter; the docs don't depend on each other |

## What's here now (P0)

The pilot-blocker set: enough to get a new circulation worker through their first day.

- [Welcome to L30 -- first-day orientation](getting-started/orientation.md) -- 60-90 minute first-day walk-through.
- [Friendly intro to library concepts](getting-started/concepts.md) -- a narrative read for new staff on the bib / item / copy hierarchy and the working vocabulary.
- [Library and L30 glossary](getting-started/glossary.md) -- terminology reference.
- [Circulation desk role orientation](roles/circulation/orientation.md) -- circulation first-day walk-through.
- [Circulation daily tasks](roles/circulation/daily.md) -- circulation cookbook to keep open mid-shift.
- [Troubleshooting: login and access](troubleshooting/login-and-access.md) -- can't get in, can't see the right pages.

## What's coming

- **P1.** Youth-services full track (orientation, reading programs, events, certificates); admin orientation and users-and-roles; the workflows cheatsheet.
- **P2.** Tech-services full track (cataloging, imports, system health); admin policies and compliance; the error-messages reference.
- **P3.** Remaining escalation docs; scanner-and-kiosk and slow-or-broken troubleshooting; the in-app `Help` link wiring to open the matching role doc from the dashboard shell.

## For library administrators adopting these docs

These docs are written so any small public library can adopt them. Names, contacts, and library-specific URLs appear as tokens in double-braces:

- `{{library_name}}` -- the library's public name
- `{{library_domain}}` -- e.g. `mylibrary.example`
- `{{l30_staff_url}}` -- the URL staff use to reach the staff app, usually `https://{{library_domain}}/login`
- `{{head_of_circulation_name}}` -- the person on staff who handles circulation policy and day-to-day desk supervision
- `{{tech_services_lead_name}}` -- the person who handles cataloging and bib record issues
- `{{youth_services_lead_name}}` -- the person who handles reading programs and family registration
- `{{tech_support_email}}` -- the address for account problems, password resets, role changes
- `{{system_admin_email}}` -- the address for outages, data loss, security incidents

Before publishing these docs to your staff, search-and-replace each token with the correct value for your library. A token-fill helper script is planned for P1.

The patron-facing Help / Knowledge Base at `/help` is the canonical source for *current* loan periods, renewal limits, hold pickup windows, card-application requirements, and fine policy at any given library. If a staff doc and the Help pages disagree on a number, the Help pages win, and the staff doc should be updated. The glossary intentionally points back to Help rather than duplicating numbers, so future policy changes are a one-place edit.

## For doc contributors

The spec for this documentation lives at `2026-05-12-l30-staff-training-docs-design.md` (kept outside this repo, not the L30 repo -- this is a deliberate split between the L30 codebase and the cross-project doc-authoring workflow). The implementation plan for P0 lives at `2026-05-12-l30-staff-training-docs-p0.md`. Read both before writing.

Voice rules in short:

- Constructive practitioner. Plain language.
- No em dashes (use `--`). No emojis.
- Banned: "click here", "simply", "just", "obviously".
- Page shape: "What this is for" / "When you'd use it" / steps / "If it didn't work".
- Tokens in double-braces for anything library-specific.

A lint script enforcing these rules is planned for the next PR.

## Related

- [Welcome to L30 -- first-day orientation](getting-started/orientation.md)
- [Library and L30 glossary](getting-started/glossary.md)
- [Circulation desk role orientation](roles/circulation/orientation.md)
- [Troubleshooting: login and access](troubleshooting/login-and-access.md)
