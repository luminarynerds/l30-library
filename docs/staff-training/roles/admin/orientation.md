---
title: Admin -- first-week orientation
audience: admin
diataxis: tutorial
estimated_time: 3-5 hours across the first week
last_reviewed: 2026-05-17
app_routes:
  - /setup
  - /staff/admin
  - /staff/admin/dashboard
  - /staff/admin/settings
  - /staff/admin/library-config
  - /staff/admin/users
  - /staff/admin/branding
  - /staff/admin/about
  - /staff/admin/integrations
  - /staff/feature-flags
  - /branches
---

# Admin -- first-week orientation

## What this is for

A first-week walk-through for a new library admin at {{library_name}}. By the end, you'll know where the admin surfaces live in L30, how the configuration model is organized, who to call when something is on fire, and what to leave alone until you've talked to the previous admin or {{system_admin_email}}.

This doc is deliberately a tour, not a click-by-click runbook. For operational procedures during an incident, jump straight to the [runbooks](../../../runbooks/) -- don't try to learn the system from this doc while production is broken.

## When you'd use it

- First week as the L30 admin or director at {{library_name}}.
- Returning to admin work after extended time away.
- Onboarding a deputy or backup admin.

You should have done the [first-day orientation](../../getting-started/orientation.md) before this. Admin tasks assume comfort with the staff app generally.

## What "admin" means in L30

A few things wear that word. Disambiguate before you act:

- **Library admin / director** -- a person. You. Has the `admin` role and can reach `AdminAuth`-gated pages.
- **The admin surface** -- the pages under `/staff/admin/*` in the app.
- **The org-features model** -- which features are turned on for {{library_name}}. Configured at [/staff/admin/library-config](/staff/admin/library-config) under the `features` tab.
- **Per-user feature flags** -- a separate development-oriented surface at [/staff/feature-flags](/staff/feature-flags). Usually you do not touch this; it's for the L30 maintainers and beta testers.

If a doc or a colleague says "turn on a feature," they almost always mean the org-features model, not the per-user flags. See the [feature flags reference](../../../governance/feature-flags-reference.md) for the canonical list of features and what they each switch on. (TODO: that reference doc is being written in parallel; if it's not there yet, ask {{tech_support_email}}.)

## The hubs you'll live in

L30 has several "hub" pages that aggregate related admin work. Bookmark these:

- [/staff/admin](/staff/admin) or [/staff/admin/dashboard](/staff/admin/dashboard) -- top-level admin dashboard.
- [/staff/admin/settings](/staff/admin/settings) -- settings hub; the entry point for nearly all configuration.
- [/staff/admin/library-config](/staff/admin/library-config) -- library configuration: site settings, features, community resources, circulation policies. This is the single most-visited admin page.
- [/staff/admin/users](/staff/admin/users) -- staff and patron user management.
- [/staff/admin/system](/staff/admin/system) -- system dashboard: health, integrations, low-level state.
- [/staff/admin/about](/staff/admin/about) -- "About us" content management; what shows on the public About page.
- [/staff/admin/branding](/staff/admin/branding) -- logos, colors, fonts.
- [/staff/admin/integrations](/staff/admin/integrations) -- third-party integration configuration (email, SMS, payments, etc.).

There are also focused hubs you'll touch less often: [/staff/library-hub](/staff/library-hub), [/staff/report-hub](/staff/report-hub), [/staff/board-hub](/staff/board-hub) (when `board_features_enabled`), [/staff/front-desk-hub](/staff/front-desk-hub).

## The first-week flow

Spread this across the week. Don't try to do it all on day one.

### Day 1: orient and read

1. Log in at {{l30_staff_url}}. Confirm your role is `admin`. If [/staff/admin](/staff/admin) gives you "not authorized," stop and email {{tech_support_email}}.
2. Open [/staff/admin/dashboard](/staff/admin/dashboard). Read every tile. Don't click anything you don't understand.
3. Open [/staff/admin/library-config](/staff/admin/library-config) and walk through each of the four tabs (`site-settings`, `features`, `community-resources`, `circulation-policies`). Read the current values. Take notes. Do not change anything.
4. Read the [feature flags reference](../../../governance/feature-flags-reference.md) end-to-end. Knowing which feature controls which surface is the single highest-leverage thing you can learn this week.
5. Read the [patron-lockout](../../../runbooks/patron-lockout.md) runbook. The rest of `docs/runbooks/` is written for whoever operates the server (backups, deploys, incident response) — not day-to-day admin work. Patron-lockout is the one you'll actually reach for: what to do when a patron can't get into their account and it can't wait for IT.

### Day 2: setup wizard and library identity

1. The setup wizard at [/setup](/setup) is what runs on first-time install. {{library_name}} has already been through it, but it's worth walking through to see what configuration L30 considers foundational. TODO: verify whether {{library_name}}'s setup can be re-run safely or whether it's a one-time flow -- the current implementation hides re-entry once a library is configured.
2. Open [/staff/admin/about](/staff/admin/about). Verify the About-us content matches reality: leadership names, contact info, hours, services offered.
3. Open [/staff/admin/branding](/staff/admin/branding). Verify logos and colors. Upload corrections if needed.
4. Open the public [/branches](/branches) page. Confirm every branch, address, and hours block is correct. If wrong, fix in [/staff/admin/library-config](/staff/admin/library-config) under `site-settings`.

### Day 3: users and roles

1. Open [/staff/admin/users](/staff/admin/users).
2. Review every staff account: is the role correct, is the account still active, has the person left {{library_name}}?
3. Deactivate accounts for people who have left. Do not delete -- you may need the audit trail.
4. For any role you don't recognize, check the role definition (TODO: verify where role definitions live in {{library_name}}'s setup; the page exposes per-user role assignment but the role catalog itself is configured separately).
5. If you need to add a new staff member, send them through the standard onboarding: [/staff/onboarding](/staff/onboarding) and the first-day docs.

### Day 4: features and org-features model

1. Open [/staff/admin/library-config#features](/staff/admin/library-config#features).
2. For each feature currently enabled, ask: "Does {{library_name}} actually use this?" If the answer is no, talk to {{youth_services_lead_name}} and {{head_of_circulation_name}} before disabling -- features can have downstream surfaces (patron-facing pages, scheduled jobs, integrations) that aren't obvious.
3. For each feature currently disabled that you think you might want, read the corresponding section of the [feature flags reference](../../../governance/feature-flags-reference.md) before flipping.
4. Never flip more than one feature per day in your first month. When something breaks, you want to know which change caused it.

### Day 5: integrations, ops, and the system dashboard

1. Open [/staff/admin/integrations](/staff/admin/integrations). Note every configured integration: email provider, SMS, payment, OCLC, partner libraries. If a credential is expiring soon, plan the rotation.
2. Open [/staff/admin/system](/staff/admin/system). Review system health. If anything is red, work the [incident-triage runbook](../../../runbooks/incident-triage.md).
3. Confirm you know how to reach {{system_admin_email}} fast. Save the phone number if there is one.
4. Confirm backups are running. The [backup-restore runbook](../../../runbooks/backup-restore.md) tells you what "running" looks like for {{library_name}}'s setup.

## What to leave alone in your first week

- **Database access pages** (any direct DB or SQL admin tools). Read-only is fine; do not run writes.
- **`/staff/feature-flags`** (per-user dev flags) -- not the same as the org-features model. Wrong page.
- **Migration wizard** at [/staff/admin/migration](/staff/admin/migration) -- only relevant during an ILS migration project.
- **Compliance, CIPA, state-compliance, public-records pages** under [/staff/admin/compliance](/staff/admin/compliance) -- read them to understand what's tracked, but configuration changes here can have legal implications. Talk to the director and legal counsel first.
- **Pay rates, timesheets, financial reports** -- if those aren't part of your admin scope at {{library_name}}, leave them. TODO: verify with director the scope of {{library_name}} admin's financial responsibilities.

## Who to ask

| Topic | Person |
|------|------|
| Day-to-day admin questions, "is this normal?" | The outgoing admin or {{system_admin_email}} |
| Account access, role assignment | {{tech_support_email}} |
| Outage, system down, data loss | {{system_admin_email}} |
| Feature behavior questions | {{tech_support_email}} or the feature flags reference |
| Circulation policy | {{head_of_circulation_name}} |
| Cataloging policy | {{tech_services_lead_name}} |
| Youth services policy | {{youth_services_lead_name}} |
| Legal, compliance, records requests | Director and legal counsel; do not improvise |

## If something is on fire right now

You're not learning, you're responding. Go straight to [incident-triage](../../../runbooks/incident-triage.md). Come back to this orientation doc when the incident is closed.

## Related

- [Feature flags reference](../../../governance/feature-flags-reference.md) (in progress)
- [Runbooks index](../../../runbooks/)
- [Patron privacy notice](../../../governance/patron-privacy-notice.md)
- [First-day orientation](../../getting-started/orientation.md)
- [Glossary](../../getting-started/glossary.md)
