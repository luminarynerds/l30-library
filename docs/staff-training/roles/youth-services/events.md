---
title: Youth services -- events end-to-end
audience: youth-services
diataxis: how-to
estimated_time: keep this tab open when running events
last_reviewed: 2026-05-17
app_routes:
  - /staff/events
  - /staff/admin/events
  - /staff/events/:eventId/roster
  - /staff/attendance
  - /staff/program-planning
  - /staff/program-partners
  - /staff/event-reviews
---

# Youth services -- events end-to-end

## What this is for

How to run a library event from creation to wrap-up at {{library_name}}: create the event, manage registrations, take attendance, send reminders, handle waitlists, and review post-event data.

## When you'd use it

- Setting up a storytime, teen night, author visit, school-break program, or any other library event.
- Mid-shift, needing the exact procedure for a single task (taking attendance, processing a waitlist).
- Post-event review and reporting.

Events sit behind the `events_enabled` feature flag. If [/staff/events](/staff/events) shows "feature not enabled", talk to your admin or {{tech_support_email}}.

This is the doc that [Circulation daily tasks](../circulation/daily.md) references as "coming in P1". If you're a circulation worker covering a youth event, the sections you need most are "How to take attendance" and "How to process a walk-in registration".

## How to create an event

### What this is for

Standing up a new event so patrons can find it on the public events page and register.

### When you'd use it

- 2-8 weeks before the event date is typical. TODO: verify with director the lead time {{library_name}} uses for different program types.

### Steps

1. Open [/staff/events](/staff/events) (or the admin alias [/staff/admin/events](/staff/admin/events)).
2. Click `New Event` (or the equivalent create control).
3. Fill in:
   - Title
   - Date, start time, end time
   - Location (branch and room; pick from the dropdown if `meeting_rooms_enabled` is on)
   - Description -- this shows on the patron-facing page; write it the way a parent or teen will read it
   - Audience or age band
   - Registration: required or drop-in
   - Capacity (if registration required)
   - Waitlist behavior (open / closed / auto-promote)
4. Optional but recommended:
   - Image -- a photo or graphic that will show on the public page
   - Tags or categories so the event surfaces in the right filters
   - Partner organization -- if a school, museum, or community group is co-hosting, link them at [/staff/program-partners](/staff/program-partners)
5. Save as `Draft` first and preview. Then `Publish` when ready.

For complex multi-session programs (a six-week coding club, a summer storytime series), use [/staff/program-planning](/staff/program-planning) instead -- it handles series scheduling better than creating events one by one.

### If it didn't work

- Save fails with a room conflict: another event is booked in the same room at the same time. Check [/staff/rooms](/staff/rooms) and resolve. Don't double-book.
- Save fails with "audience required" or a similar field error: the field is required by your library's configuration. Fill it.
- Event saves but doesn't appear on the public events page: the status is `Draft`. Flip to `Published`.

## How to manage registrations

### What this is for

Seeing who's signed up, adding or removing registrants, switching attendees between sessions.

### When you'd use it

- Mid-week before an event, when a parent calls to register their kid by phone.
- A patron emails asking to be added.
- A patron asks to cancel.

### Steps

1. Open [/staff/events](/staff/events) and click into the event.
2. Open the `Registrations` or `Roster` tab (also accessible at `/staff/events/:eventId/roster`).
3. To add a registrant: search the patron, confirm the registration, send the confirmation email if your library's policy is to send one. TODO: verify with director whether {{library_name}} sends confirmations on staff-added registrations by default.
4. To cancel a registrant: click the row, click `Cancel` or `Remove`, optionally promote the first waitlist entry (see waitlist section).
5. To register a non-patron walk-up (e.g. a parent without a card who shows up at storytime): TODO: verify with director the {{library_name}} policy here. The system supports guest registration but some libraries require a card first.

### If it didn't work

- Patron is registered but doesn't show on the roster: refresh. If still missing, the registration may have errored on submission. Re-register from the staff side.
- "Patron not found" search: the patron may not have a card yet. Send them to [/staff/card-applications](/staff/card-applications) or handle per your walk-up policy.

## How to take attendance

### What this is for

Recording who actually showed up so the post-event report is accurate.

### When you'd use it

- At the door as patrons arrive.
- Immediately after the event ends.

### Steps

1. Open [/staff/attendance](/staff/attendance) on a tablet or laptop at the door, or open the event roster directly.
2. As each registered patron arrives, mark them present (tap the row or scan their card).
3. For walk-ins (registered or not): use the walk-in / add-on control on the attendance page.
4. After the event ends, mark any registered no-shows. Don't leave them blank -- the report needs the distinction between "no-show" and "not yet checked in."
5. Save / submit.

### If it didn't work

- Patron is on the roster but the attendance page won't let you mark them: confirm the event is `In Progress` or `Today`. Events too far in the future or past may lock attendance.
- You forgot to take attendance during the event: you can still record it after the fact from [/staff/attendance](/staff/attendance) -- pick the event from the past-events filter and enter the counts. Note any uncertainty in the event's internal notes.

## How to send reminders

### What this is for

A reminder email or message to registered patrons before the event.

### When you'd use it

- 24-48 hours before an event with required registration.
- Day-of for events with high no-show history.

### Steps

1. Open the event from [/staff/events](/staff/events).
2. Look for a `Send Reminder` action on the event detail or roster page. TODO: verify with director whether {{library_name}} uses automatic reminders (configured at [/staff/admin/outreach](/staff/admin/outreach) under email-notifications) or relies on manual sends.
3. If sending manually: review the message template, confirm the recipient list, send.
4. Log the send in the event's internal notes so the next staffer knows it went out.

### If it didn't work

- Reminders aren't going out at all: the `events_enabled` reminder pipeline depends on outbound email being configured. Check with the admin who owns [/staff/admin/outreach](/staff/admin/outreach).
- Patron reports they didn't receive the reminder: check their `Communication` tab on the patron record. They may have unsubscribed from event email or have a stale email address.

## How to handle waitlists

### What this is for

Managing the overflow when an event is full.

### When you'd use it

- When an event hits capacity and the waitlist starts filling.
- When a registered patron cancels and you want to promote the first waitlist entry.

### Steps

1. Open the event's `Registrations` or `Roster` tab.
2. The waitlist is visible as a separate section below the active registrations.
3. To promote: cancel a registered patron (or wait for the auto-promote setting to fire), then either let the system auto-promote or manually promote the next person on the waitlist.
4. When promoting manually, send a notification so the patron knows they got a spot. Give them a reasonable window (e.g. 24 hours) to confirm before promoting the next person. TODO: verify with director the {{library_name}} convention on confirmation windows.

### If it didn't work

- Auto-promote doesn't fire: check the event's waitlist behavior setting (open / closed / auto-promote). If it's set to `Closed`, you'll need to switch it or promote manually.
- A patron says they're on the waitlist but doesn't appear: confirm the event ID and the patron account. Sometimes patrons confuse two similar events.

## How to view post-event reports

### What this is for

Seeing attendance counts, no-show rates, demographic breakdown, and any patron reviews after an event has happened.

### When you'd use it

- The day after an event.
- Weekly for the program report to {{youth_services_lead_name}}.
- For grant reporting and annual board reports.

### Steps

1. From [/staff/events](/staff/events), click into the event and open the `Report` tab.
2. Confirm attendance numbers match what you took at the door.
3. Look at the no-show rate. If it's high (over your library's threshold), that's a signal to adjust reminders or registration policy.
4. For event reviews and patron feedback, open [/staff/event-reviews](/staff/event-reviews). Read the reviews; respond to any that need a response per your library's policy. TODO: verify with director whether {{library_name}} responds publicly to event reviews.
5. For cross-event analytics (trends over time, by program type, by branch), use [/staff/analytics](/staff/analytics) or the report-hub.

### If it didn't work

- Attendance counts don't match what you remember: the at-door entries may not have been saved. Re-enter from your paper backup if you have one and add an internal note.

## Quick reference: walk-in registration at the door

A circulation worker covering the door asks: "What do I do for a walk-up?"

1. Open the event in [/staff/events](/staff/events).
2. Click `Add Registration` or use the attendance walk-in control.
3. Search the patron. If they have a card, register and mark present in one step.
4. If they don't have a card: TODO: verify with director the {{library_name}} walk-up policy. The system supports guest registration; some libraries require a card.
5. Hand them the program materials and let them in.

## Related

- [Youth services orientation](orientation.md)
- [Reading programs how-to](reading-programs.md) -- reading programs often launch with an event
- [Circulation daily tasks](../circulation/daily.md)
- [Patron privacy notice](../../../governance/patron-privacy-notice.md)
