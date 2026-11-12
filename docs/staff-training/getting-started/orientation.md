---
title: Welcome to L30 -- first-day orientation
audience: all-staff
diataxis: tutorial
estimated_time: 60-90 min
last_reviewed: 2026-05-14
app_routes:
  - /login
  - /staff
  - /account
  - /staff/patrons
  - /staff/circulation
  - /staff/holds/shelf
  - /staff/cataloging
  - /catalog
---

# Welcome to L30 -- first-day orientation

## What this is for

A 60-90 minute walk-through of the L30 staff interface for someone using it for the first time.

## When you'd use it

- Your first day on the job at a library running L30.
- You're switching from another ILS and need to map your existing knowledge onto L30 terminology and screens.

## Before you start

You need:

- Your staff account (email plus a temporary password) from `{{head_of_circulation_name}}`.
- Your role assignment (`circulation`, `tech-services`, `youth-services`, `admin`, or some combination). If you don't know what you have, see step 4 below.
- The URL for your library's L30 staff entry point: `{{l30_staff_url}}` (typically `https://{{library_domain}}/login`).
- A computer with a modern browser (Firefox, Chrome, Safari, Edge). A barcode scanner at your station if you'll be doing circulation work; standard USB keyboard-wedge scanners work with no driver.

If anything in that list is missing, stop and ask `{{head_of_circulation_name}}` before continuing.

## Log in for the first time

1. Open `{{l30_staff_url}}` in your browser.
2. On the [login page](/login), enter your email and the temporary password from `{{head_of_circulation_name}}`.
3. If the system prompts you to set a permanent password, do that now. Pick something you can remember; the password reset flow works (see `troubleshooting/login-and-access.md`) but it's not pleasant on day one.
4. After login you land on the staff dashboard at `/staff`. If you land somewhere else (a public catalog page, for instance), see "If it didn't work" at the bottom of this doc.

<!-- screenshot: login page with email and password fields, "Sign in" button highlighted -->

## The shape of the staff interface

L30 has four main surfaces you'll touch every day. Each is reached from the top navigation, or by typing the URL directly, or by using the command palette (described below).

**The dashboard** at `/staff` is your starting point. It's role-calibrated -- what shows up depends on your `role` and `dashboard function`. A circulation worker sees holds-to-pull, today's check-ins, fines collected; a youth-services librarian sees reading-program activity; an admin sees user-management shortcuts. If your dashboard looks empty or wrong, see the [dashboard function](glossary.md#dashboard-function) glossary entry and step 6 below.

**The work surfaces** are role-specific pages: [Patron lookup](/staff/patrons), [Circulation](/staff/circulation) for check-out and check-in, [Hold shelf](/staff/holds/shelf) for ready holds, [Cataloging](/staff/cataloging) for bib editing, and a wider tree of role-specific tools that appear in the nav based on your role.

**The catalog** at [/catalog](/catalog) is the same public-facing item search a patron uses. Staff use it constantly: looking up an item by title or ISBN, placing a hold on behalf of a patron, checking what's available. The catalog is not in `/staff/`; it's at the root.

**Your account** at [/account](/account) is where you manage your own profile, preferences, password, and accessibility settings. Note: this is the same account page patrons use. Staff don't have a separate `/staff/profile`. The page knows you're staff and shows the relevant tabs.

**Command palette.** Press `Cmd+K` (macOS) or `Ctrl+K` (Windows/Linux) anywhere in the app to open a search-first navigator. Type the name of a page or action; the palette jumps you there. Use this whenever you don't remember a URL.

<!-- screenshot: command palette open with search field and a few suggested results -->

## Set up your account

1. Open [/account](/account).
2. Confirm your displayed name, email, and branch are correct. If a field is wrong, ask `{{head_of_circulation_name}}` to update it -- some fields are admin-only.
3. Set your dashboard tone preference. Open the `Settings` tab and look for `Dashboard tone`. The three values are `calm` (low density, large type), `standard` (default), `full` (everything visible). This is a personal preference -- pick what's least tiring for an eight-hour shift. You can change it any time.
4. Open the `Accessibility` tab and set anything you need: contrast, motion-reduction, font size. These persist across sessions on this device.
5. Confirm your function tag(s). If the field is empty or wrong, ask `{{head_of_circulation_name}}` to set it. Your function tag is what drives the dashboard layout in step 1.
6. Save.

If after saving the dashboard still looks wrong, see `troubleshooting/login-and-access.md` for the "I logged in but the wrong dashboard loads" recipe.

## A 10-minute clickaround

Open each of these in a new tab and look around. Don't try to *do* anything yet; this is a tour, not a task list.

1. [/staff](/staff) -- your dashboard. The panels here are the ones you'll see most often.
2. [/staff/patrons](/staff/patrons) -- patron search and detail. Type a name or scan a card.
3. [/staff/circulation](/staff/circulation) -- the check-out, check-in, renew, and holds tabs.
4. [/staff/holds/shelf](/staff/holds/shelf) -- the hold shelf with `To Pull`, `Ready`, `Expiring`, `Expired` views.
5. [/staff/cataloging](/staff/cataloging) -- bib record search and editing (the MARC form). Most staff don't edit here; catalogers do.
6. [/staff/card-applications](/staff/card-applications) -- pending library-card applications waiting for staff review.
7. [/staff/fines](/staff/fines) -- fine management: track, collect payment, process waivers.
8. [/staff/lost-damaged](/staff/lost-damaged) -- the lost-and-damaged item queue.
9. [/catalog](/catalog) -- the public catalog. Try searching for any title.
10. [/account](/account) -- your account page (the one you configured in the previous section).

If a page returns a `403 Forbidden`, you don't have the role that grants access -- that's expected, not broken. The `roles/admin/*` tree (P1) is admin-only; the cataloging form is tech-services-and-up; some features are gated by per-library feature flags. Note any 403s for the admin-or-supervisor conversation later; don't escalate from here.

## A note on app organization

L30 puts staff tools under `/staff/...` and patron-facing pages at the top level (`/catalog`, `/account`, `/help`). You'll use both. The patron-facing catalog and Help / Knowledge Base pages aren't separate from your job; they're often the easiest way to look up an item or quote a policy to a patron. The Help pages at `/help` are the canonical statement of *current* loan periods, renewal rules, hold pickup windows, lost-item handling, and card-application requirements at this library. When a patron asks a policy question at the desk, Help is usually the fastest source of truth -- and if a staff doc disagrees with Help, Help wins.

You'll also notice that some routes you might expect (a separate staff profile, a separate `/staff/holds` shortcut) don't exist as standalone pages. The staff profile is part of the same `/account` page patrons use; the hold shelf lives at `/staff/holds/shelf` and the per-patron hold list lives on the patron detail page under the `Holds` tab. The [glossary](glossary.md) has entries for each of these to keep terminology consistent.

## What your next read should be

Once you've finished this orientation, the next doc depends on your role:

- **Circulation** -- read [Circulation desk role orientation](../roles/circulation/orientation.md), then keep [Circulation daily tasks](../roles/circulation/daily.md) open during your shift.
- **Tech-services / cataloger** -- the role-specific orientation is coming in P2. Until then, the [glossary](glossary.md) covers MARC, BIBFRAME, RDA, AACR2, and authority records; read those entries and ask `{{head_of_circulation_name}}` for a hands-on walkthrough.
- **Youth-services** -- the role-specific orientation is coming in P1. Until then, ask the youth-services lead for a desk walkthrough of `/staff/reading-review` and the events tooling.
- **Admin / branch manager** -- the role-specific orientation is coming in P1. Until then, the [glossary](glossary.md) entries for `role`, `function tag`, `circulation policy`, `fine schedule`, and `IMLS report` cover the working vocabulary.

If you have more than one role, read the orientations in any order; they don't depend on each other.

## Who do I ask?

L30's authoring assumption is that "the person who handles this" varies per library, so contacts are tokens you fill in. At your library:

| Topic | Person or address |
|------|------|
| Circulation policy, scheduling, day-to-day desk questions | `{{head_of_circulation_name}}` |
| Account problems, password reset, role changes | `{{tech_support_email}}` |
| Cataloging and bib record issues | `{{tech_services_lead_name}}` |
| Reading programs, events, family registrations | `{{youth_services_lead_name}}` |
| System down, data loss, security incident | `{{system_admin_email}}` (treat as outage) |

If it's not an emergency and you're not sure who, default to `{{head_of_circulation_name}}` -- they'll route you.

## If it didn't work

- Login failed or the dashboard looks empty or wrong -- see [Troubleshooting: login and access](../troubleshooting/login-and-access.md).
- A page returned `403 Forbidden` you expected to see -- your role doesn't include access. Ask `{{head_of_circulation_name}}` to add the role.
- A page returned `404 Not Found` -- the feature may not be enabled at your library. Check with `{{tech_support_email}}`.

## Related

- [Library and L30 glossary](glossary.md)
- [Friendly intro to library concepts](concepts.md)
- [Circulation desk role orientation](../roles/circulation/orientation.md)
- [Troubleshooting: login and access](../troubleshooting/login-and-access.md)
