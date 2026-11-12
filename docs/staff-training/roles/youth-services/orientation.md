---
title: Youth services -- role orientation
audience: youth-services
diataxis: tutorial
estimated_time: 60-90 min
last_reviewed: 2026-05-17
app_routes:
  - /staff/admin/reading-programs
  - /staff/admin/reading-ambassadors
  - /staff/events
  - /staff/admin/events
  - /staff/patrons
  - /staff/card-applications
  - /youth
  - /teen
  - /parent-onboarding
---

# Youth services -- role orientation

## What this is for

A first-day walk-through for a new youth-services librarian at {{library_name}}. By the end you'll know where the youth-services work lives in L30, who to ask when you're stuck, and what your first week looks like.

## When you'd use it

- Your first day in the youth-services role.
- Returning to youth services after time in a different role.
- Refresher when {{library_name}} re-organizes which staff cover youth work.

If you haven't done the [first-day orientation](../../getting-started/orientation.md) yet, do that first. This doc assumes you can already log in, find the staff dashboard, and look up a patron.

## What youth services covers at {{library_name}}

Youth services is the public-facing work for patrons from birth through high school, plus the adults who bring them in. Concretely, you own (or share ownership of):

- **The kids and teen catalog views.** L30 has dedicated public landing pages at [/youth](/youth) and [/teen](/teen) that surface age-appropriate items and program info. The general [/catalog](/catalog) is also available; the youth pages are curated entry points, not separate collections.
- **Reading programs.** Summer reading, winter reading, family challenges, and any year-round reading challenges your library runs. Managed at [/staff/admin/reading-programs](/staff/admin/reading-programs). See the [reading-programs how-to](reading-programs.md).
- **Programs and events.** Storytimes, teen nights, author visits, school-break activities. Managed at [/staff/events](/staff/events) (alias: [/staff/admin/events](/staff/admin/events)). See the [events how-to](events.md).
- **Parent and family communications.** Patron-account notes, the parent-onboarding flow at [/parent-onboarding](/parent-onboarding) (when `parent_onboarding_enabled` is on), and outbound messages tied to youth programs.
- **Age-gating.** Verifying that patrons signed up for kids/teen programs are in the right age bracket; flagging accounts where a parent needs to co-sign a card application.
- **School partnerships.** Coordinating with local schools for class visits, summer reading kickoffs, teacher card sign-ups. The teacher-facing surface lives at `/teacher/*` routes (e.g. [/teacher/family-challenges](/teacher/family-challenges) when `for_teachers_enabled` is on). TODO: verify with director which schools {{library_name}} currently partners with and who the contact is at each.

You do not own circulation policy, cataloging decisions, or facilities. Hand those off to {{head_of_circulation_name}}, {{tech_services_lead_name}}, and the building manager respectively.

## Who to ask

| Topic | Person |
|------|------|
| Reading-program policy and prizes | {{youth_services_lead_name}} |
| A patron's account is locked or wrong | {{head_of_circulation_name}} |
| A bib record is wrong, missing, or mis-aged | {{tech_services_lead_name}} |
| Account access, password, role permissions | {{tech_support_email}} |
| Outage, "the events page is down for everyone" | {{system_admin_email}} |
| School partnership questions | TODO: verify with director |

## The first-day flow

Plan for 60-90 minutes the first time through. Have {{youth_services_lead_name}} or a peer youth-services worker available for the parts that need a second pair of eyes.

### Step 1. Log in and verify your role

1. Go to {{l30_staff_url}} and log in.
2. From the staff dashboard, confirm you can see a `Youth` or `Reading Programs` tile. If not, email {{tech_support_email}} -- your role likely doesn't have `reading_programs_enabled` or `events_enabled` permission yet.
3. Open [/staff/admin/reading-programs](/staff/admin/reading-programs). If you get a "not authorized" or feature-disabled message, stop and email {{tech_support_email}}.

### Step 2. Walk the public youth pages

Open these in a new tab and read them the way a parent would:

1. [/youth](/youth) -- the kids landing page. Note what's featured, what events show up, what reading programs are visible.
2. [/teen](/teen) -- the teen landing page.
3. [/catalog](/catalog) -- the general catalog. Search for a kids title you know and look at the item detail page. This is what a parent helping their kid will see.

Make a note of anything that looks stale, off-brand, or wrong. Bring it to your one-on-one with {{youth_services_lead_name}}. Don't edit anything yet.

### Step 3. Look at active reading programs

1. Open [/staff/admin/reading-programs](/staff/admin/reading-programs).
2. Look at the active programs list. For each one, note: name, age group, start and end dates, participant count.
3. Click into one program to see its goals, ambassador list, and participation report.
4. Do not change anything yet. The full procedure is in the [reading-programs how-to](reading-programs.md).

### Step 4. Look at upcoming events

1. Open [/staff/events](/staff/events).
2. Filter to the next 30 days.
3. Skim the list. For each youth or family event, click in and look at the registration count, capacity, and waitlist.
4. Open [/staff/attendance](/staff/attendance) and look at the recent attendance entries to see what an in-flight event looks like at the desk.

### Step 5. Look up a recent youth patron

1. Open [/staff/patrons](/staff/patrons).
2. Search for a patron you know is enrolled in a current reading program.
3. Look at the `Profile`, `Holds`, `Communication` tabs. Notice age and any guardian-linkage fields. TODO: verify with director the exact age-gating fields in use at {{library_name}}; the patron model supports several configurations.
4. Don't make changes. You're learning the shape of the data.

### Step 6. Read the patron-facing Help pages

1. Open `/help`.
2. This is the canonical answer for loan periods, card-application requirements, and parental-consent rules. If a parent asks at the desk, you can read straight off the Help pages -- no internal lookups needed.
3. If a staff doc you read later disagrees with Help on a number, Help wins and the staff doc should be updated.

### Step 7. Bookmark your daily tabs

In your browser, bookmark and group these:

- [/staff/events](/staff/events)
- [/staff/admin/reading-programs](/staff/admin/reading-programs)
- [/staff/patrons](/staff/patrons)
- [/staff/card-applications](/staff/card-applications)
- [/staff/knowledge-base](/staff/knowledge-base)

These are the pages you'll touch every shift.

## What your first week looks like

Day 1: This orientation. Shadow {{youth_services_lead_name}} or a peer for one storytime or one program-desk shift.

Day 2-3: Read the [reading-programs how-to](reading-programs.md) and [events how-to](events.md) end-to-end. Set up one test event and one test reading program in a non-public state if your library has a staging mode, or sit with {{youth_services_lead_name}} and do it for real on a low-stakes upcoming event.

Day 4-5: Handle a real check-in shift for an event. Process at least one reading-program goal completion. Field one parent question with FAQ-backed answers.

By the end of week one you should be able to: create an event, take attendance, approve a reading ambassador, mark a reading-program goal complete, and answer parent FAQ questions without escalation.

## If it didn't work

- "I can see the patron-facing youth page but not the staff admin page" -- your role is missing `reading_programs_enabled` or you're not assigned to the right org-features set. Email {{tech_support_email}} with the exact URL that failed and the message you saw.
- "The youth catalog page is empty / shows adult titles" -- this is a curation or feature-flag issue, not a youth-services workflow problem. Note the URL and the time and escalate to {{tech_services_lead_name}}.
- "I see events but can't edit them" -- you have read-only access. Email {{tech_support_email}} to request `events_enabled` write access for your role.

## Related

- [Reading programs -- how to run a challenge end-to-end](reading-programs.md)
- [Events -- create, register, attend, report](events.md)
- [Circulation daily tasks](../circulation/daily.md) -- helpful when youth services covers the desk
- [First-day orientation](../../getting-started/orientation.md)
- [Glossary](../../getting-started/glossary.md)
