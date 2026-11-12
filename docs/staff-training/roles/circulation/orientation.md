---
title: Circulation desk -- role orientation
audience: circulation
diataxis: tutorial
estimated_time: 1-2 hours
last_reviewed: 2026-05-14
app_routes:
  - /staff
  - /staff/circulation
  - /staff/patrons
  - /staff/holds/shelf
  - /staff/fines
  - /staff/lost-damaged
  - /staff/card-applications
  - /catalog
---

# Circulation desk -- role orientation

## What this is for

A hands-on walk-through of every task a circulation desk worker does on a typical shift, run end to end.

## When you'd use it

- Your first day or first week at the circulation desk.
- Coming back after a long break and needing a refresher on a workflow.

## Before you start

- You've completed [Welcome to L30 -- first-day orientation](../../getting-started/orientation.md).
- You have a `circulation` role on your staff account. Verify at [/account](/account).
- You have a barcode scanner at your station. USB keyboard-wedge scanners work with no driver; the scanner types into whichever input field has focus.
- You know where the physical hold shelf is at your branch and which letter or number ordering it uses (alphabetical-by-patron-last-name is the default at most libraries; ask `{{head_of_circulation_name}}` if unsure).
- You know your library's current circulation policy: loan periods, renewal limits, hold pickup window, and lost-item policy. The patron-facing Help / Knowledge Base at `/help` is the canonical statement of those numbers for this library; check there or with `{{head_of_circulation_name}}` before quoting policy to a patron.

## The shape of the circulation dashboard

When you open [/staff](/staff) with a `circulation` role, the dashboard surfaces the work you'll do today: holds-to-pull for your branch, items returned today, today's check-outs, outstanding fines and recent payments, and any patron alerts (account holds, expired cards, COPPA-pending accounts). The dashboard is read-only -- it's a status surface, not the place where work happens. The work surfaces are at [/staff/circulation](/staff/circulation), [/staff/holds/shelf](/staff/holds/shelf), [/staff/patrons](/staff/patrons), [/staff/fines](/staff/fines), and [/staff/lost-damaged](/staff/lost-damaged).

<!-- screenshot: circulation-role dashboard with the four main panels labeled -->

The rest of this doc walks each major task end to end. The companion [Circulation daily tasks](daily.md) doc is a cookbook -- short procedures you keep open during your shift. Read this orientation once; use the daily doc forever.

## Check out an item to a patron

1. Open [/staff/circulation](/staff/circulation) and switch to the `Check Out` tab. (The page has tabs labeled `All`, `Check Out`, `Check In`, `Renew`, `Holds`.)
2. The patron-lookup field on the left expects a library-card barcode or a patron search. Scan the patron's card, or type their name, phone, or email and pick from the dropdown.
3. Confirm the patron name and photo (if available) match the person in front of you. This is the moment to catch a mis-presented card; do not skip it.
4. If the patron has an `account hold`, `account block`, `suspension`, `restriction`, or `expired` status, an alert banner appears with the reason. See "Account-state explanations" below before proceeding.
5. With the patron loaded, scan the first item's barcode. The title, due date, and item type appear in the running checkout list.
6. Repeat for additional items. If the patron is at their checkout limit per `circulation policy`, the system blocks the next item and explains why.
7. If any item shows `Status: pending`, `Status: in transit`, `Status: lost`, or another non-`available` status, see "Common issues" below.
8. When done, click `Finish` (or whatever the prominent confirm button reads on your build).
9. Hand items to the patron with the due date called out aloud. If your station has a receipt printer the receipt prints automatically; otherwise offer the patron an emailed receipt from the confirmation screen.

## Check in a returning item

1. Open [/staff/circulation](/staff/circulation) and switch to the `Check In` tab.
2. Scan each returning item. The system identifies the item, removes it from the patron's checkouts, and shows one of these outcomes:
   - **Routine return.** The item is now `available`. Place it on the re-shelving cart.
   - **Hold fills.** The system prompts you to route the item to the hold shelf with a slip showing the patron name and pickup slot. Place the slip in the item and put it on the hold shelf in the correct slot.
   - **In transit.** The item is owned by another branch. The system prints (or shows) a transit slip with the destination branch. Put the item in the transit bin for that branch.
   - **Damaged or lost-status return.** The system prompts you to route the item through the lost-and-damaged workflow at [/staff/lost-damaged](/staff/lost-damaged). Don't try to clear the status from the check-in screen.
   - **Claims returned.** If the patron is in front of you saying "I returned this last week," check in normally; the system clears the `claims returned` flag. If you find the item without the patron present, follow the local claims-returned procedure with `{{head_of_circulation_name}}`.
3. After the last item, leave the tab open if the patron is waiting for a receipt or has more items. Otherwise it's safe to switch tabs.

## Place a hold for a patron

Holds are placed from the catalog, not from the circulation page. The catalog is the same surface a patron uses to place a hold on their own; the staff workflow is the catalog plus the patron-on-file context.

1. Look up the patron at [/staff/patrons](/staff/patrons) first so you know whose hold you're placing.
2. In a new tab, open [/catalog](/catalog) and find the bib the patron wants (by title, author, ISBN, or call number).
3. Open the item detail page and click `Place Hold`.
4. The modal asks for pickup branch (and on some builds, the patron account if the system is in staff-on-behalf mode). Pick the patron's preferred pickup branch.
5. Confirm. The hold appears under the patron's `Holds` tab on the patron detail page.
6. Tell the patron the estimated wait. The system shows queue position; "position 1" doesn't necessarily mean today (a copy might still be checked out).

If the patron wants a hold on a specific copy rather than the bib, that's a recall, not a hold -- see the [glossary entry for recall](../../getting-started/glossary.md#recall) and escalate to `{{head_of_circulation_name}}`.

## Pull and shelve holds

Each morning (or whatever your local rhythm is), pull and process new holds:

1. Open [/staff/holds/shelf](/staff/holds/shelf) and switch to the `To Pull` view.
2. The list shows each item, its call number, and the patron name. Sort by call number to make the pull route efficient.
3. Walk the stacks and pull each item. Bring them all to the desk in one trip.
4. At the desk, scan each item through the `Check In` tab (this is how the system flips the hold from `pending` to `ready`).
5. For each item that fills a hold, the system prints (or shows) a hold slip with the patron name and pickup slot.
6. Place each item on the hold shelf in the slot indicated. Ordering convention varies by branch (alphabetical-by-patron-last-name is common); ask `{{head_of_circulation_name}}` for the rule at your branch.
7. Items that didn't pull (missing on shelf, in-use copy) automatically retry the next pull cycle. Note any persistent miss on the daily report or in the patron note.

## Cancel a hold

1. Open the patron detail page at [/staff/patrons](/staff/patrons) and find the hold under the `Holds` tab.
2. Click the cancel control on the hold row. The system asks for a reason (`Cancelled by staff` is the default; you can specify "patron requested" or similar).
3. The hold flips to `cancelled` and the next patron in the queue rolls up.

If a patron asks you to cancel a hold while their item is already `ready` on the hold shelf, the cancel still works -- but go retrieve the physical item from the shelf and re-shelve it, or it sits there until its expiry.

## Look up a patron

1. Open [/staff/patrons](/staff/patrons).
2. Search by name, library-card barcode, phone, or email -- the search field accepts all of those.
3. Pick the patron from the results.
4. The detail page tabs are `Profile`, `Checkouts`, `Holds`, `Fines`, `History`, `Communication`. Each shows the patron's current state in that area.
5. Use `Communication` to send a patron message (overdue reminder, hold-ready note) without leaving the page. The message ships through whatever channels the patron has configured.

To edit a patron record (change of address, name correction, parental-consent re-verification), the controls live on the `Profile` tab. Some fields are admin-only and read as plain text for circulation-role staff -- that's correct; route those edits to `{{head_of_circulation_name}}` or an admin.

## Take a fine or fee payment

Two paths, depending on where you're starting:

**From the patron detail page** at [/staff/patrons](/staff/patrons):

1. Open the `Fines` tab.
2. The list shows outstanding fines and fees by item or event, with `amount`, `status` (`outstanding`, `partial`, `paid`, `waived`), and a `Pay` control on each row.
3. Click `Pay` on the row the patron wants to settle, enter the amount, and pick the payment method (cash, check, card). The workflow is the same across methods.
4. The fine flips to `paid` (or `partial` if the patron paid less than the full amount).
5. Print or email the receipt from the confirmation screen.

**From the fine-management surface** at [/staff/fines](/staff/fines):

1. The page lists all outstanding fines across patrons, with filters.
2. Take payment as above. The fine-management surface is more useful for end-of-day reconciliation and bulk operations than for at-the-desk single payments.

Use the right name on the receipt: a **fine** accrues over time (overdue days), a **fee** is a fixed one-time charge (card replacement), and a **lost-item charge** is the combined replacement plus processing posted when an item is declared lost. Returning the lost item clears the replacement portion of a lost-item charge; it does not clear a fine or fee. See the [glossary entry](../../getting-started/glossary.md#fine-vs-fee-vs-lost-item-charge).

## Waive a fine

Fine waivers require a documented reason and create an audit trail. The L30 backend gates waivers behind `require_staff` (any staff role can perform a waiver), but most libraries restrict waivers by *policy* to a smaller set of people (head of circulation, admin, director). The frontend `Fine Management` surface at [/staff/fines](/staff/fines) is presented as an admin-shell page; if you can reach it, you can technically perform a waiver -- but **only do so within your library's policy**.

1. Confirm the waiver is within your authority at this library. If your library's policy says "head of circulation only" and that's not you, escalate to `{{head_of_circulation_name}}` instead.
2. Open [/staff/fines](/staff/fines) (or the patron's `Fines` tab).
3. Click the `Waive` control on the fine row.
4. Enter the reason. The reason is mandatory and appears on the audit trail; "patron disputed; resolved at desk" or "system error verified by `{{head_of_circulation_name}}`" are typical. Vague reasons ("courtesy") fail review later.
5. Submit. The fine status flips to `waived` and the audit record is created with your user, the reason, and a timestamp.

If a fine "looks wrong" on a screen but you're not sure why, do NOT delete or waive it. Flag to `{{head_of_circulation_name}}` and document in a patron note. Waiving covers up evidence of a real system issue.

## Mark an item lost or damaged

If a patron tells you an item is lost or you find damage during check-in:

1. Don't try to clear the status from the circulation page. Open [/staff/lost-damaged](/staff/lost-damaged).
2. Pick the relevant tab: `Lost`, `Damaged`, `Claims`, `Mending`. The `Lost` tab handles "patron declared this lost" and "system marked this lost after 30 days overdue" cases. The `Damaged` tab handles physical-damage triage and routing to mending.
3. Add the item to the queue with the relevant evidence (patron statement, your damage notes, photos if your library captures them).
4. The system posts the lost-item charge (replacement plus processing) to the patron account when an item is declared lost. Per the patron-facing Help pages at `/help`, returning the item clears the replacement portion of the charge even if the return is late; a small processing fee may remain. Confirm your library's current handling with `{{head_of_circulation_name}}`.

## Renew an item

1. Look up the patron at [/staff/patrons](/staff/patrons) and open the `Checkouts` tab. Or open [/staff/circulation](/staff/circulation) and switch to the `Renew` tab.
2. Each checkout row shows the title, due date, and a `Renew` control if the item is renewable.
3. Click `Renew`. The system extends the due date per the `circulation policy` for that item type.
4. Renewals are blocked if another patron has a hold on the bib (the queue takes priority), or if the item type is non-renewable. Per the patron-facing Help pages at `/help`, this library allows up to `2 renewals` per item; new releases are non-renewable. Confirm current rules at `Borrowing Rules` or with `{{head_of_circulation_name}}`.

## Process a card application

A patron has applied for a card online or filled in a paper application. The application waits in a queue for staff review:

1. Open [/staff/card-applications](/staff/card-applications).
2. Pick the pending application from the list.
3. Verify the patron's ID and proof of address per your library's policy. The patron-facing Help pages at `/help` document what's accepted (photo ID plus proof of address; expired ID accepted with a social-services letter; shelter address or library address accepted for unhoused patrons). Read Help before you say no.
4. If the patron meets the criteria, approve the application. The patron account activates and they can borrow immediately. If you're not sure whether they meet the criteria, escalate to `{{head_of_circulation_name}}` rather than rejecting -- the policy is intentionally inclusive.
5. If the applicant is under 13, the account stays inactive until `parental consent (COPPA)` is recorded. Hand the parent the consent handout; the parent completes the consent token from their email. Staff cannot complete consent at the desk.

Full account creation and edits (changing a name, merging duplicates, applying special account types) require an admin role -- see `roles/admin/users-and-roles.md` (P1). At circulation you're the first reviewer, not the full administrator.

## Hold troubleshooting: "why isn't my hold ready?"

A patron asks why their hold hasn't filled. Common causes, in rough order of frequency:

- **They're not first in queue.** Open the patron's `Holds` tab and check the queue position. Position 3 means three patrons ahead.
- **No copy has been returned yet.** Even if the patron is position 1, the system can't fill the hold until a copy comes in. If the only copy is checked out for another two weeks, the hold waits.
- **All copies are at another branch and haven't shipped.** A copy returned at branch B that's owed to branch A shows `in transit`; the hold doesn't fill until the item arrives at the pickup branch.
- **The patron asked for a specific pickup branch with no copies.** Reset the pickup branch to "any branch" on the hold and the next-returned copy can fill it.
- **The patron has an `account hold` or expired card.** Holds don't trigger checkout if the account isn't allowed to circulate. Resolve the account state first.

If none of those explain it, escalate to `{{head_of_circulation_name}}`.

## Account-state explanations

Five overlapping concepts here. Staff confuse them constantly; the glossary cross-references each entry.

- **[Account hold](../../getting-started/glossary.md#account-hold)** -- umbrella term for "this account can't circulate normally." Causes: overdue items past a threshold, unpaid fines past a threshold, expired card, pending parental consent. The patron detail page shows the reason and the resolution path.
- **[Account block](../../getting-started/glossary.md#account-block)** -- one specific type of account hold: administrative, set by a staff member, requires a staff member to lift. Used after repeated lost items, disputes, or behavior issues. Always documented on the patron note.
- **[Suspension](../../getting-started/glossary.md#suspension)** -- automatic, time-bounded. Triggers from a circulation event (third overdue notice, for instance). Lifts on its own when the end date passes.
- **[Restriction](../../getting-started/glossary.md#restriction)** -- staff-applied scoped limit. The patron can still borrow, but not from one collection or with one specific privilege (no holds, for instance). Used for parent-permission cases on challenged titles.
- **[Expired account](../../getting-started/glossary.md#expired-account)** -- the card hit its `expiry` date. Renew at the desk after re-verifying address and ID per the patron-facing Help pages at `/help`.

If a patron is upset about a block or suspension at the desk, do NOT debate the policy at the desk; resolve what you can today and route the rest to `{{head_of_circulation_name}}` for a follow-up conversation.

## Common issues

| Symptom | Likely cause | What to do |
|------|------|------|
| Patron has `account hold` at `Check Out` | Overdue, unpaid fees, or expired card | Read the alert; route to the right resolution. Card renewal you can do; large fee dispute goes to `{{head_of_circulation_name}}`. |
| Item won't scan | Dirty barcode, lost data, or torn label | Try keyboard entry of the visible barcode. If still no match, check the call number and re-find the bib in [/staff/cataloging](/staff/cataloging) or [/catalog](/catalog). |
| "Item is in transit" appears at check-in | Already routed to another branch | Place in that branch's transit bin. Do not re-route. |
| Patron not in system | New patron (no card yet) | Walk them through the card application; see "Process a card application" above. |
| Fine looks wrong | Could be system or could be correct | Do NOT delete or waive on suspicion. Flag to `{{head_of_circulation_name}}` and add a patron note. |
| Hold shows `expired` | Pickup window passed (per `/help`, default is `7 days` from `ready` notification at this library) | Patron can re-place the hold; they keep their data, lose only their queue position. |
| Patron complaining about a block | Account block or suspension | Read the reason on the patron note. Resolve what you can; escalate disputes to `{{head_of_circulation_name}}`. |

## End of shift

A short checklist before you log out:

1. Close any in-flight check-outs or check-ins. Open transactions don't auto-close.
2. Reconcile cash collected today against the receipt count from [/staff/fines](/staff/fines) (or your library's cash-drawer procedure at [/staff/cash-drawer](/staff/cash-drawer) if your build has it enabled).
3. Return any item still at the desk to the re-shelving cart or the appropriate slot.
4. Check the dashboard for unresolved alerts. Hand any open issue to the next shift via the message board, or log it as a patron note.
5. Log out (top-right menu). On a shared desk computer, also close the browser to clear any session cache.

## Related

- [Circulation daily tasks](daily.md)
- [Library and L30 glossary](../../getting-started/glossary.md)
- [Welcome to L30 -- first-day orientation](../../getting-started/orientation.md)
- [Troubleshooting: login and access](../../troubleshooting/login-and-access.md)
