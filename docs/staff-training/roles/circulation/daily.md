---
title: Circulation -- daily tasks
audience: circulation
diataxis: how-to
estimated_time: keep this tab open during your shift
last_reviewed: 2026-05-14
app_routes:
  - /staff/circulation
  - /staff/holds/shelf
  - /staff/patrons
  - /staff/fines
  - /staff/lost-damaged
  - /staff/card-applications
  - /catalog
---

# Circulation -- daily tasks

## What this is for

Quick how-tos for the tasks a circulation worker does multiple times per shift. Each section stands alone -- skim to the one you need.

## When you'd use it

- Mid-shift, needing to remember a specific procedure.
- Refreshing on a task you haven't done in a while.

If you haven't done [Circulation desk role orientation](orientation.md), do that first. This doc is the cookbook; the orientation is the cooking class.

## How to check out items to a patron

### What this is for

Lending one or more items to a patron present at the desk.

### When you'd use it

- A patron is at the desk with items to borrow.
- You're processing a holds-pickup for a patron in person.

### Steps

1. Open [/staff/circulation](/staff/circulation) and switch to the `Check Out` tab.
2. Scan the patron's library card, or type their name or barcode and pick from the dropdown.
3. Verify the name on screen matches the person.
4. Scan each item. Confirm the title and due date in the running list.
5. Click `Finish`.
6. Call the due date aloud and hand the items over.

### If it didn't work

- Account-hold or block alert: see [Circulation orientation -- Account-state explanations](orientation.md#account-state-explanations).
- Item won't scan: try keyboard entry of the visible barcode; if still no match, the item may not be cataloged at this branch.

## How to check in returning items

### What this is for

Receiving items returned by a patron or from the book-drop.

### When you'd use it

- A patron returns items at the desk.
- You're processing the morning book-drop queue.

### Steps

1. Open [/staff/circulation](/staff/circulation) and switch to the `Check In` tab.
2. Scan each item.
3. Watch for alerts on each scan:
   - Routine return: place on re-shelving cart.
   - Hold fills: follow the prompt to the hold shelf (see "Print a hold-shelf slip" below).
   - In transit: place in the destination branch's transit bin.
   - Damaged or lost: see "Mark an item lost" or "Mark an item damaged" below.

### If it didn't work

- "Item not found" on scan: confirm the barcode is the item barcode, not a patron card. If the barcode is correct but unknown, the item may need cataloging; escalate to `{{tech_services_lead_name}}`.

## How to pull holds for today

### What this is for

Pulling the items the hold system has flagged for pickup, processing them, and shelving them on the hold shelf.

### When you'd use it

- Each morning, or on whatever schedule your library uses for pulls.

### Steps

1. Open [/staff/holds/shelf](/staff/holds/shelf) and switch to the `To Pull` view.
2. Sort by call number.
3. Walk the stacks and pull each item.
4. Bring them all to the desk.
5. Check in each item at [/staff/circulation](/staff/circulation) `Check In` tab. The system flips the hold to `ready` and prompts you to place the item in a hold-shelf slot.
6. Place each item on the hold shelf in the indicated slot.

### If it didn't work

- An item isn't on the shelf: leave it in the pull list; it auto-retries next cycle. Log persistent misses for shelf-reading at [/staff/shelf-reading](/staff/shelf-reading).

## How to add a hold for a patron

### What this is for

Placing a hold on an item on behalf of a patron at the desk.

### When you'd use it

- A patron asks for a hold but doesn't want to do it themselves.
- A patron asks for a hold on something not currently available.

### Steps

1. Look up the patron at [/staff/patrons](/staff/patrons) so you have them on file.
2. Open [/catalog](/catalog) in a new tab.
3. Find the bib (title, author, ISBN, call number).
4. Click `Place Hold` on the item detail page.
5. Pick the patron's preferred pickup branch in the modal.
6. Confirm. The hold appears under the patron's `Holds` tab.
7. Tell the patron their queue position and estimated wait.

### If it didn't work

- Hold blocked with "account hold": resolve the account state first.
- No `Place Hold` control: the item type may not be holdable at this library (some reference items, museum passes). Check `circulation policy`.

## How to cancel a hold for a patron

### What this is for

Removing a patron's hold at the patron's request.

### When you'd use it

- Patron no longer wants the item.
- Hold was placed in error.

### Steps

1. Open the patron at [/staff/patrons](/staff/patrons).
2. Switch to the `Holds` tab.
3. Click cancel on the hold row.
4. Enter a reason (`Patron requested` is typical).
5. Confirm.

### If it didn't work

- Hold was already `ready` on the shelf: cancel still succeeds, but retrieve the physical item from the shelf and re-shelve it -- the cancel doesn't move the book.

## How to renew an item

### What this is for

Extending a patron's due date on an item they're not done with.

### When you'd use it

- Patron asks at the desk or by phone.
- Self-service renewal failed and they're asking why.

### Steps

1. Open the patron at [/staff/patrons](/staff/patrons), `Checkouts` tab. Or open [/staff/circulation](/staff/circulation) and switch to the `Renew` tab.
2. Click `Renew` on the item row.
3. The new due date appears. Read it to the patron.

### If it didn't work

- "Renewal not allowed": another patron has a hold on the bib, or the item type is non-renewable (new releases at this library per `/help`), or the patron has hit the renewal limit (`2 renewals` per item by current policy). Quote the Help-page figures only after confirming current policy at `Borrowing Rules` or with `{{head_of_circulation_name}}`.

## How to look up a patron

### What this is for

Finding a patron's record to see their checkouts, holds, fines, or to take action on their account.

### When you'd use it

- Almost every interaction at the desk.

### Steps

1. Open [/staff/patrons](/staff/patrons).
2. Scan the patron's card, or type any of: name, barcode, phone, email.
3. Pick from the search results.
4. The detail page tabs are `Profile`, `Checkouts`, `Holds`, `Fines`, `History`, `Communication`.

### If it didn't work

- No results for a patron you believe is in system: try variant spellings, the phone number, or the email. If still no match, the patron may be at a different library system or need to apply for a card; see "Process a card application" below.

## How to add a note to a patron account

### What this is for

Recording context on a patron account: a verified ID change, a disputed fine, a behavior incident.

### When you'd use it

- When information about a patron interaction should be visible to the next staff person reading their record.

### Steps

1. Open the patron at [/staff/patrons](/staff/patrons).
2. On the `Profile` tab, find the patron-notes section.
3. Add a dated note. Be factual and specific; "patron disputed `$5.00` fine on barcode `12345`; resolved with waiver, see audit" is useful. "Difficult patron" is not.
4. Save.

### If it didn't work

- Notes section not visible or read-only: your role may not include note-edit. Ask `{{head_of_circulation_name}}` for the role change, or have them add the note.

## How to mark an item lost

### What this is for

Recording that a patron has declared an item lost (or that you've determined it lost).

### When you'd use it

- Patron tells you they can't find an item they checked out.
- An item is 30+ days overdue and the system has auto-flagged it.

### Steps

1. Open [/staff/lost-damaged](/staff/lost-damaged) and switch to the `Lost` tab.
2. Find the item in the queue (or add it if it's not there yet).
3. Confirm the lost-item handling per your library's policy. The patron-facing Help pages at `/help` state the patron is charged the replacement cost, the charge clears if the item is returned (even if late), and a small processing fee may remain.
4. Save. The lost-item charge posts to the patron account.

### If it didn't work

- Action denied: lost-item processing may be gated by a role you don't have. Route to `{{head_of_circulation_name}}`.

## How to mark an item damaged

### What this is for

Routing a damaged item to mending and (where applicable) posting a charge to the patron.

### When you'd use it

- An item is damaged on return.
- A patron declares damage on an item still checked out.

### Steps

1. Open [/staff/lost-damaged](/staff/lost-damaged) and switch to the `Damaged` tab.
2. Add the item to the queue with a damage description (water, tear, missing pages, missing parts).
3. The system routes the item to the mending workflow and, per your library's policy, may post a partial charge to the patron. Confirm the charge handling with `{{head_of_circulation_name}}` before discussing dollar amounts with the patron.
4. Place the physical item in the mending bin or return cart as your library directs.

### If it didn't work

- Damage workflow not present: feature may not be enabled at your library. Hold the item, log the damage in a patron note, and route to `{{tech_services_lead_name}}`.

## How to take a fine or fee payment

### What this is for

Collecting payment from a patron for an outstanding fine, fee, or lost-item charge.

### When you'd use it

- Patron asks to pay at the desk.
- Patron is paying as part of clearing an account block.

### Steps

1. Open the patron at [/staff/patrons](/staff/patrons), `Fines` tab.
2. Click `Pay` on the row the patron wants to settle.
3. Enter the amount and payment method (cash, check, card).
4. Confirm.
5. Print or email the receipt.

### If it didn't work

- Card-payment integration not configured: take cash or check; route card-only patrons to the online payment surface, or to a payment terminal if one is available at your branch.
- Patron disputes the charge: do NOT delete or waive on the spot if the dispute is substantive. Document in a patron note and route to `{{head_of_circulation_name}}`. See "Waive a fine" below for the policy boundary.

## How to waive a fine

### What this is for

Removing a fine from a patron's account with a documented reason and an audit trail.

### When you'd use it

- A fine was assessed in error (system or staff error).
- A fine is being waived as part of a documented courtesy or hardship policy.

### Policy gate

The L30 backend gates waivers behind `require_staff`, meaning any staff role can technically perform a waiver. The `Fine Management` page at [/staff/fines](/staff/fines) is presented as an admin-shell page. Most libraries restrict waivers by *policy* to a smaller set of people (head of circulation, admin, director). **Confirm your library's policy before waiving.** If your library says "head of circulation only" and that's not you, escalate to `{{head_of_circulation_name}}`.

### Steps

1. Confirm the waiver is within your authority.
2. Open the patron at [/staff/patrons](/staff/patrons), `Fines` tab. (Or [/staff/fines](/staff/fines) for cross-patron waivers.)
3. Click `Waive` on the fine row.
4. Enter a specific reason ("patron disputed; resolved at desk with `{{head_of_circulation_name}}`" or "system error verified, see audit ticket X"). Vague reasons fail audit review.
5. Submit. The fine flips to `waived` with your user and timestamp on the audit trail.

### If it didn't work

- `Waive` control not visible: your role doesn't include the waiver action even though the backend allows it; the frontend may gate by `dashboard function` or feature flag. Route to `{{head_of_circulation_name}}`.

## How to print a hold-shelf slip

### What this is for

Producing the slip with patron name and pickup slot that goes into an item on the hold shelf.

### When you'd use it

- The check-in workflow on a holdable item generates this prompt.
- A slip prints poorly or gets lost and you need to re-print.

### Steps

1. The slip prints automatically when you check in an item that fills a hold.
2. To re-print, open [/staff/holds/shelf](/staff/holds/shelf), find the hold in the `Ready` view, and use the re-print control on the row.
3. If the slip didn't print at all, check the receipt-printer connection at your station, and confirm with `{{tech_support_email}}` that the print integration is enabled.

### If it didn't work

- Manual workaround: write the patron name and pickup slot on a slip by hand; the digital record is already correct, the paper slip is for shelf navigation.

## How to search for an item

### What this is for

Finding a bib or item by title, author, ISBN, call number, or barcode.

### When you'd use it

- Patron asks "do you have...?"
- You need to verify a bib exists before placing a hold.

### Steps

1. Open [/catalog](/catalog) (the same catalog patrons use).
2. Type any of: title, author, ISBN, or call number.
3. Filter by branch, format, or audience using the facets.
4. Open the item detail page for full holdings (which branches own copies, what's available, what's on hold).

For staff-only bib editing (MARC, BIBFRAME), use [/staff/cataloging](/staff/cataloging) instead -- but only catalogers and tech-services staff should be editing bib records.

### If it didn't work

- No results: try a broader search (the author alone, or only an ISBN). If the bib really doesn't exist, the item may need cataloging; route to `{{tech_services_lead_name}}`.

## How to place an item in transit to another branch

### What this is for

Sending an item to another branch (to fill a hold, return to owner, or load-balance).

### When you'd use it

- Item returned at branch B, owned by branch A.
- A hold for a patron at branch B is filled by a copy from branch A.

### Steps

1. Check in the item at [/staff/circulation](/staff/circulation) `Check In` tab.
2. If the destination is another branch, the system shows `in transit` and prints (or shows) a transit slip with the destination branch name.
3. Place the item with the transit slip in the destination branch's transit bin.
4. Do NOT re-route an item that already shows `in transit`. Wait for it to arrive at its destination before further action.

### If it didn't work

- No transit slip: confirm your receipt printer or check [/staff/transit](/staff/transit) for the active transit queue and re-print from there.

## How to process a card application

### What this is for

Reviewing a pending library-card application and approving (or escalating) it.

### When you'd use it

- A patron applied online and you're staffing the queue.
- A walk-in is asking for a new card.

### Steps

1. Open [/staff/card-applications](/staff/card-applications).
2. Pick the pending application.
3. Verify the patron's documentation per your library's policy. The patron-facing Help pages at `/help` are canonical: photo ID plus proof of address; non-residents pay `$50/year` (or are free if from Elmdale or Thornbury per the current sharing agreement); shelter address, social-services letter, or library address accepted for unhoused patrons; expired and out-of-area ID accepted with a social-services letter.
4. Approve if criteria are met. The account activates.
5. If the applicant is under 13, the account stays inactive until `parental consent (COPPA)` is recorded. Hand the parent the consent handout; the parent completes the consent token from their email.

### If it didn't work

- You're unsure whether the patron meets the criteria: do not reject. Escalate to `{{head_of_circulation_name}}`. The policy is intentionally inclusive ("we're here to help, not judge" -- direct quote from the Help pages).
- Full account creation, deletion, merging, or special account types: requires admin role; see `roles/admin/users-and-roles.md` (P1).

## How to reserve a study room

This workflow lives on the events tooling and isn't owned by circulation directly. See `roles/youth-services/events.md` once that doc ships in P1. In the meantime, study-room reservations are typically handled at the events surface at [/staff/rooms](/staff/rooms) (if your library has `meeting_rooms_enabled`) -- ask `{{head_of_circulation_name}}` for the local procedure.

## How to log a patron complaint or incident

### What this is for

Recording a complaint or incident on the patron record so the next staff person reading the record sees the context.

### When you'd use it

- Patron files a complaint at the desk.
- A behavior incident occurs (verbal, physical, security).

### Steps

1. Resolve the immediate situation first; documentation is second priority.
2. Open the patron at [/staff/patrons](/staff/patrons) and add a dated patron note (see "Add a note to a patron account" above). Be factual and specific.
3. If the incident is a safety issue or involves law enforcement, do NOT handle it through patron notes alone. Notify `{{head_of_circulation_name}}` and follow your library's incident-report procedure. If the incident involves a law-enforcement request, route to the `director` role -- regular staff cannot process these.

### If it didn't work

- Complaint surface is broken or unclear: log a manual incident report per your library's procedure and notify `{{head_of_circulation_name}}` directly.

## What's NOT in this doc

- Fine waivers above the per-incident threshold, account creation, account deletion, role assignment -- see `roles/admin/users-and-roles.md` (P1).
- Reading-program registration, family registration, summer-reading enrollment -- see `roles/youth-services/reading-programs.md` (P1).
- Bib record editing, MARC, BIBFRAME, authority records -- see `roles/tech-services/cataloging.md` (P2).
- Scanner or kiosk hardware issues -- see `troubleshooting/scanner-and-kiosk.md` (P3).
- Anything that requires a `director` or `super_admin` role -- escalate to `{{system_admin_email}}`.

## Related

- [Circulation desk role orientation](orientation.md)
- [Library and L30 glossary](../../getting-started/glossary.md)
- [Welcome to L30 -- first-day orientation](../../getting-started/orientation.md)
- [Troubleshooting: login and access](../../troubleshooting/login-and-access.md)
