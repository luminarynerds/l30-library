---
title: Circulation -- ILL handling
audience: circulation
diataxis: how-to
estimated_time: keep this tab open during ILL work
last_reviewed: 2026-05-17
app_routes:
  - /staff/interlibrary-loan
  - /staff/circulation
  - /staff/patrons
feature_flags:
  - ill_enabled
related_docs:
  - ../../../admin-guide/ill-consortium.md
related_kb:
  - "Staff KB: How to Process an Interlibrary Loan (ILL) Request"
---

# Circulation -- ILL handling

## What this is for

Step-by-step desk procedures for handling interlibrary loan (ILL) items at
the circulation counter. Skim to the section you need. The
[admin-guide ILL doc](../../../admin-guide/ill-consortium.md) explains the
*system* (flags, partners, lifecycle); this page explains the *moves your
hands make* during a shift.

## When you'd use it

- A patron asks for a book we don't own.
- An ILL package arrives at the desk.
- A patron returns an ILL item.
- A consortium courier drops off or picks up a tub.

If you haven't done
[Circulation desk role orientation](orientation.md), do that first.

## How to take an ILL request from a patron at the desk

### What this is for

A patron asks for an item we don't own (or that's all checked out with a
long hold queue).

### When you'd use it

- Patron has a specific title/author in mind.
- A reference search confirms we don't have it, or the wait is unacceptable.

### Steps

1. In the catalog, confirm we genuinely don't own it. If we do, offer a
   normal hold instead -- ILL is slower and costlier.
2. Open [/staff/interlibrary-loan](/staff/interlibrary-loan), click
   `+ New request`.
3. Scan or search the patron's card. Their account must be in good
   standing -- see
   [Circulation orientation -- Account-state explanations](orientation.md#account-state-explanations).
4. Enter what you know: title (required), author, ISBN if you can find
   it, publisher, year. The more you give, the higher the auto-search hit
   rate.
5. Pick a format if the patron has a preference (print, large-print,
   audio, ebook). Leave blank if any is fine -- you'll get more matches.
6. Set the patron's `needed by` date if they mentioned one. The system
   warns you if turnaround likely won't meet it.
7. Save. Status is `pending`. Tell the patron:
   - Typical arrival: 5-14 business days for consortium, 2-4 weeks for
     outside ILL.
   - They'll get an email and/or text when it arrives.
   - The loan period is typically 3 weeks, **not renewable** through
     their account (they have to ask staff).
   - There may be a small fee -- you'll let them know before submitting
     to the lender if so.

### If it didn't work

- Patron's account is blocked: resolve the block first (overdue items
  > 30 days, more than 5 active ILL requests, fines over local
  threshold). See the admin-guide
  [Eligibility rules](../../../admin-guide/ill-consortium.md#eligibility-rules).
- Auto-search returns "no matches": the item exists nowhere in your
  partner network. Offer a purchase suggestion via
  [/staff/acquisitions](/staff/acquisitions) instead.

## How to triage the ILL queue at shift start

### What this is for

Catch new patron-submitted requests so nothing sits in `pending` for days.

### When you'd use it

- Start of each shift. Two minutes.

### Steps

1. Open [/staff/interlibrary-loan](/staff/interlibrary-loan).
2. Filter by status `pending`. Anything older than 24 hours is your
   first priority.
3. For each: click in, click `Auto-search`. If a partner is located,
   status moves to `located` -- review the suggested lender, then click
   `Submit to lender`. If `not_found`, see *If it didn't work* below.
4. Check status `in_transit` -- anything older than the partner's
   average turnaround + 5 days, follow up with the lender directly.
5. Check status `denied` -- the lender said no. Either pick a different
   lender or notify the patron.

### If it didn't work

- Auto-search says `not_found`: pick a likely partner manually from
  the dropdown and submit by email. Note in a staff-only tracking
  update which partner you tried.
- A request has been `submitted` for more than two weeks with no
  response: email the lender. Set a staff-only tracking note with the
  date you followed up.

## How to receive an incoming ILL package

### What this is for

A package arrives addressed to your library with an ILL slip inside (or
a courier drops a consortium tub).

### When you'd use it

- Mail arrives. Courier arrives. Always at the desk; never leave ILL
  packages in a mail room overnight.

### Steps

1. Open the package over a clear surface. Pull out the ILL slip.
2. Match the slip to the request: open
   [/staff/interlibrary-loan](/staff/interlibrary-loan), search by
   title, partner code, or patron name.
3. Click `Mark received`. Status moves to `received`. The system
   generates a temporary catalog stub.
4. Apply the ILL barcode label (front of book, lower-right -- don't
   cover the lender's barcode). Apply the ILL due-date sticker with
   the date the request shows.
5. Note any condition issues *before* circulation. Photograph if
   serious. Add a staff-only tracking update -- the lender will hold
   us responsible for damage that wasn't there at receipt.
6. Place on the holds shelf with the patron's notification slip.
7. Trigger the patron notification: the system does this automatically
   when status moves to `received`, but verify under the patron's
   account that the message went out.

### If it didn't work

- No matching request in L30: the lender shipped to us without our
  having submitted. Possible match-error, or a long-lost re-ship.
  Email the lender's ILL contact (on the slip) before checking the
  item in.
- Lender barcode is missing or damaged: do not strip or replace it.
  Tape it down with archival tape if loose; add a staff-only tracking
  note.

## How to check an ILL item out to a patron

### What this is for

Patron arrives to pick up their ILL.

### When you'd use it

- Standard pickup, after the patron has been notified.

### Steps

1. Open [/staff/circulation](/staff/circulation) `Check Out` tab. Scan
   the patron's card.
2. Scan the **ILL barcode** (the one you applied), not the lender's
   barcode. The system recognizes it as an ILL stub and pulls the
   shorter due date and the "non-renewable" flag automatically.
3. Confirm the title and due date on screen.
4. Click `Finish`. Status on the ILL request moves to `checked_out`.
5. Hand over the item. Say the due date aloud. Add: "This one isn't
   renewable through your account -- if you need more time, call us
   and we'll ask the lender."

### If it didn't work

- System refuses checkout with "ILL request not in `received`
  state": somebody skipped a step. Open the request, fix the status
  forward, retry.
- Patron asks for renewal at checkout: explain renewal is request-only
  on ILL items and requires lender approval. Don't promise it.

## How to handle an ILL renewal request

### What this is for

Patron calls or emails asking for more time on an ILL item.

### When you'd use it

- Patron has the item, due date is approaching, they're not done.

### Steps

1. Open [/staff/interlibrary-loan](/staff/interlibrary-loan), find the
   request, click `Renew`. This sends a renewal request to the lender
   and posts a patron-visible tracking note.
2. Tell the patron: "I've asked the lender. I should hear back in a
   few business days. The current due date stands unless they
   approve."
3. When the lender replies:
   - Approved -> update the due date on the request to the new date.
     The system pushes the updated due date to the catalog stub, so
     circulation sees it on next checkout/return.
   - Denied -> post a patron-visible tracking note and contact the
     patron. The original due date holds.

### If it didn't work

- Lender doesn't respond within a week: email them directly. Don't
  let it pass the original due date in silence -- it becomes an
  overdue toward us, not the patron.

## How to process an ILL return

### What this is for

Patron returns an ILL item.

### When you'd use it

- Returned at the desk or via the book drop.

### Steps

1. Scan the ILL barcode in [/staff/circulation](/staff/circulation)
   `Check In`. The system flags it as an ILL return -- circulation
   marks the patron's account clear, then routes the physical item to
   the ILL return shelf.
2. Inspect for damage. Note in a staff-only tracking update if
   anything has changed since receipt.
3. Open the ILL request, click `Generate return shipping label`. The
   label uses the partner's saved shipping method and address.
4. Pack the item with the lender's original slip if you still have it.
   Apply the return label.
5. Mark the request `return_in_transit`. Drop in the outbound courier
   tub or hand to USPS/UPS/FedEx per the partner's preference.

### If it didn't work

- Return shipping label endpoint errors: the partner record is missing
  an address. Flag your supervisor; do not make up an address.
- Item came back damaged from the patron: still send it back -- the
  lender decides next steps. Add a damage cost record so the patron
  account can be billed if the lender invoices us.

## How to handle a "lost in transit" ILL

### What this is for

A package didn't arrive at either end within the grace window
(default 30 days past expected date).

### When you'd use it

- An outgoing return that the lender never reports receiving.
- An incoming item that we shipped to a borrowing library but they
  never report receiving.
- A consortium tub that vanished between libraries.

### Steps

1. Open the request, set status to `lost`.
2. Add a staff-only tracking update with what you know: tracking
   number, last known status, dates you followed up.
3. Add a cost record (`POST /api/v1/ill/staff/requests/{id}/costs`)
   with category `lost_item` and the partner's stated replacement
   cost. This will appear on the next consortium billing cycle, or
   on a direct invoice for non-consortium partners.
4. For patron-borrowed items lost on the way back: do **not**
   automatically charge the patron. Talk to your supervisor first --
   responsibility depends on whether the patron returned at the desk
   (we own it from that point) or via book drop (judgment call).

### If it didn't work

- Tracking shows the package was delivered but the partner says it
  wasn't: have the partner check their incoming-mail area before
  declaring it lost. Set status to `lost` only after both sides have
  searched.

## Related

- [Circulation -- daily tasks](daily.md) for the rest of the desk
  cookbook.
- [Circulation orientation](orientation.md) for account-state and
  block explanations.
- [Admin guide -- ILL and consortium](../../../admin-guide/ill-consortium.md)
  for system setup, partner records, consortium settings, and
  reports.
- Staff KB: *How to Process an Interlibrary Loan (ILL) Request*
  (search the staff KB by title).
