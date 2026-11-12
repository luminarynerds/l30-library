---
title: Youth services -- run a reading program end-to-end
audience: youth-services
diataxis: how-to
estimated_time: keep this tab open during a program season
last_reviewed: 2026-05-17
app_routes:
  - /staff/admin/reading-programs
  - /staff/admin/reading-ambassadors
  - /staff/reading-review
  - /staff/patrons
---

# Youth services -- run a reading program end-to-end

## What this is for

How to run a summer or winter reading challenge from setup to wrap-up at {{library_name}}: create the program, set goals, approve ambassadors, award badges and certificates, view participation reports, and handle disputes.

## When you'd use it

- Setting up summer reading in the spring.
- Setting up a winter or break challenge.
- Mid-season operations: approving ambassadors, awarding goals, answering parent questions.
- End-of-season wrap-up and reporting to the director.

If you haven't done the [youth-services orientation](orientation.md), do that first. Reading programs sit behind the `reading_programs_enabled` feature flag; if [/staff/admin/reading-programs](/staff/admin/reading-programs) shows "feature not enabled", talk to {{tech_support_email}} or the admin who owns feature flags.

## How to create a new reading challenge

### What this is for

Standing up a new program (e.g. "Summer Reading 2026") that patrons can sign up for and log progress against.

### When you'd use it

- 4-6 weeks before the program starts is typical lead time. TODO: verify with director the lead time {{library_name}} uses.

### Steps

1. Open [/staff/admin/reading-programs](/staff/admin/reading-programs).
2. Click `New Program` (or the equivalent create control).
3. Fill in:
   - Program name (e.g. `Summer Reading 2026`)
   - Age group or grade band
   - Start date and end date
   - Description -- this shows on the patron-facing page
4. Save the draft. The program is not yet visible to patrons.
5. Add goals (see next section) before publishing.
6. When ready, flip the program to `Published` or `Active`. TODO: verify with director the exact state label used at {{library_name}} -- the page exposes a status control but naming has changed across releases.

### If it didn't work

- Save fails with a date-range error: the end date is before the start date, or overlaps with another program of the same age group in a way your library's policy disallows. Adjust dates.
- The program saves but doesn't appear on [/youth](/youth) or [/teen](/teen): check that the status is `Published` / `Active`, not `Draft`. If it's published and still not showing, escalate to {{tech_support_email}}.

## How to set goals for a program

### What this is for

Defining what counts as progress (minutes read, books finished, activities completed) and what rewards a participant unlocks at each tier.

### When you'd use it

- During program setup, before publishing.
- Mid-season to add a stretch goal (only if your policy allows it without disadvantaging existing participants).

### Steps

1. From [/staff/admin/reading-programs](/staff/admin/reading-programs), click into the program.
2. Open the `Goals` (or `Tiers`) tab.
3. For each goal, set:
   - Goal name (e.g. `Read 5 books`)
   - Metric and target (books, minutes, activities, with a number)
   - Reward (badge, certificate, prize description)
4. Save.

### If it didn't work

- Patrons report they hit a goal but the system didn't award it: see "How to handle a disputed goal completion" below.

## How to approve a reading ambassador

### What this is for

Reading ambassadors are patrons (often teens or active adult readers) who help promote the program, mentor newer participants, and may have small program privileges. Applications come in from the public site and need staff approval before the ambassador is active.

### When you'd use it

- A new ambassador application is pending.
- Renewing an ambassador for a new season.

### Steps

1. Open [/staff/admin/reading-ambassadors](/staff/admin/reading-ambassadors).
2. Look at the `Pending` queue.
3. Click into an applicant. Review:
   - Their patron record (account in good standing, age matches program)
   - Their application essay / answers
   - Any prior ambassador history
4. Approve or decline. If you decline, add an internal note explaining why -- the next staffer reviewing a renewal will need that context.
5. For approvals, confirm the assignment to a specific program.

### If it didn't work

- Approve button is missing or grayed out: your role likely doesn't have ambassador-admin permission. {{youth_services_lead_name}} or an admin needs to do the approval.
- Applicant's patron record looks wrong (age mismatch, blocked): resolve the underlying patron-account issue first via [/staff/patrons](/staff/patrons), then revisit the application.

## How to award a badge or certificate

### What this is for

Marking a participant's goal as complete and triggering the badge/certificate the program defines.

### When you'd use it

- A patron reports they finished a goal at the desk or in person.
- Reviewing the gamification queue for self-reported goal completions.

### Steps

1. If the patron's reading log needs review first, open [/staff/reading-review](/staff/reading-review) (the gamification review queue, when `gamification_enabled` is on). Approve the log entries that contribute to the goal.
2. Open [/staff/admin/reading-programs](/staff/admin/reading-programs), click into the program, and find the participant.
3. Verify their progress against the goal.
4. Mark the goal complete (or confirm the auto-awarded badge). The system fires the reward defined on the goal.
5. If the reward is a physical prize, hand it over at the desk and log the handoff. TODO: verify with director the {{library_name}} convention for logging physical-prize handoffs.

Certificates: participants can also view and print their own certificates from their patron account; the staff-side page for certificate verification is at `/certificate/verify`.

### If it didn't work

- Goal won't mark complete: the patron's logged progress may not meet the target. Check their reading log first. If progress looks right but the button won't fire, escalate to {{tech_support_email}} with the patron ID, program ID, and goal name.
- Badge fires but no email notification: the program may be misconfigured for notifications, or the patron has unsubscribed from program email. Check `Communication` on the patron record.

## How to view participation reports

### What this is for

Seeing how the program is doing: sign-ups, active participants, goal completion rates, demographic breakdown.

### When you'd use it

- Weekly during a program season.
- For end-of-season wrap-up to {{youth_services_lead_name}} and the director.
- When the board asks for impact numbers.

### Steps

1. Open [/staff/admin/reading-programs](/staff/admin/reading-programs).
2. Click into the program.
3. Open the `Reports` or `Participation` tab.
4. Filter by date range, age group, or branch as needed.
5. Export to CSV if you need to share outside L30. Be careful with patron names in any exported file; see the [patron privacy notice](../../../governance/patron-privacy-notice.md).

For cross-program analytics (multiple programs, year-over-year), see [/staff/admin/analytics](/staff/admin/analytics) or the report-hub.

### If it didn't work

- Report numbers look wildly wrong (e.g. zero participants when you know there are many): the program ID filter may be set to a draft duplicate. Confirm you're looking at the right program. If still wrong, escalate.

## How to handle a disputed goal completion

### What this is for

A patron (or parent) believes they completed a goal but the system disagrees, or believes a reward is missing.

### When you'd use it

- Parent reports at the desk: "My kid read 10 books but the badge didn't show up."

### Steps

1. Open the patron at [/staff/patrons](/staff/patrons). Look at their reading log on the `Reading` tab (or the linked log page).
2. Cross-reference against the program goal (open the program in a second tab).
3. If the patron's logged entries genuinely meet the goal, manually mark the goal complete per "How to award a badge or certificate" above. Add an internal note: who reported, when, what you verified.
4. If the entries don't meet the goal, walk through the math with the parent in plain language: which entries counted, which didn't, why. Don't blame the patron or the software; just show the count.
5. If the patron disagrees with how the log was recorded (e.g. "we logged a 200-page book, the system shows 20 pages"), correct the log entry from [/staff/reading-review](/staff/reading-review) and note the correction.
6. If you can't resolve it at the desk, escalate to {{youth_services_lead_name}} with a screenshot and the patron ID. Do not promise a specific outcome.

### If it didn't work

- Cannot edit log entries: your role may lack `gamification_enabled` write permission. Escalate.
- Pattern emerges (multiple patrons reporting the same goal misfiring): this is a bug, not a one-off. File an issue with {{tech_support_email}} and include three example patron IDs.

## End-of-season wrap-up

After the program closes:

1. Export final participation reports (see "How to view participation reports").
2. Spot-check: do all participants who hit a goal show that goal as awarded?
3. Confirm with the director that any physical-prize fulfilment is complete.
4. Archive or mark the program as `Closed` so it stops appearing on the patron-facing landing pages. TODO: verify with director the {{library_name}} convention for archiving vs leaving programs visible as historical.
5. Schedule a 30-minute debrief with {{youth_services_lead_name}}: what worked, what didn't, what to change for next year.

## Related

- [Youth services orientation](orientation.md)
- [Events how-to](events.md) -- many reading-program kickoffs are events
- [Patron privacy notice](../../../governance/patron-privacy-notice.md)
- [Glossary](../../getting-started/glossary.md)
