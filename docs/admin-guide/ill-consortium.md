---
title: Interlibrary loan and consortium
audience: admin, circulation lead
diataxis: reference + how-to
estimated_time: 25 minutes to skim, keep open while configuring
last_reviewed: 2026-05-17
app_routes:
  - /staff/interlibrary-loan
  - /staff/admin/consortium
feature_flags:
  - ill_enabled
  - outreach_enabled
related_kb:
  - "Staff KB: How to Process an Interlibrary Loan (ILL) Request"
  - "Patron KB: Requesting an Interlibrary Loan (entry #147)"
---

# Interlibrary loan and consortium

## What this is for

L30 ships two related, but separately gated, surfaces:

- **Interlibrary loan (ILL)** -- one-off, request-driven lending and borrowing of
  items with any partner library, including libraries that are not on L30.
  Gated by the `ill_enabled` feature flag. Routed at
  [/staff/interlibrary-loan](/staff/interlibrary-loan).
- **Consortium management** -- ongoing reciprocal-borrowing relationships
  between two or more libraries that have explicitly joined a named consortium
  (shared catalog visibility, shared patron records, periodic billing).
  Gated by the `outreach_enabled` feature flag. Routed at
  [/staff/admin/consortium](/staff/admin/consortium).

If you only do occasional borrowing for patrons, you need ILL.
If you have signed a reciprocal-borrowing agreement with another library that
also runs L30 (or that participates via the consortium federation API), you
need both.

The patron-facing equivalents are the catalog "Request from another library"
button and the `My Account -> Interlibrary loans` page. Patron documentation
lives in the knowledge base; see entry #147 ("Requesting an Interlibrary
Loan") and the two new ILL entries added 2026-05-17.

## When you'd use it

- **First-time setup.** Turning on the feature, adding partner libraries,
  configuring shipping defaults, deciding whether to join a consortium.
- **Daily desk work.** Circulation staff: see
  [Circulation -- ILL handling](../staff-training/roles/circulation/ill-handling.md)
  for the step-by-step desk procedures.
- **Periodic admin tasks.** Reviewing fill rates, paying or invoicing
  consortium billing, suspending or activating member libraries, exporting
  invoices for board review.

## What ILL means in L30

The L30 ILL module covers two flows:

| Direction | Trigger | Who does what |
|-----------|---------|---------------|
| **Outgoing (borrowing)** | A patron requests an item we don't own, or staff request one on their behalf. | We act as the *borrowing library*. We locate the item at a partner, submit the request, receive the item, check it out to the patron, accept the return, and ship it back. |
| **Incoming (lending)** | A partner library requests one of our items. | We act as the *lending library*. We pull the item, ship it, track it, accept its return, and re-shelve it. |

The `ILLRequestType` enum has exactly these two values: `borrow` and `lend`.

The lifecycle is the same `ILLRequestStatus` enum for both directions, defined
in `backend/app/models/interlibrary_loan.py`:

```
pending -> searching -> located -> submitted -> approved
       -> in_transit -> received -> checked_out
       -> returned -> return_in_transit -> completed
```

Two side branches: `denied` and `not_found` end the lifecycle without a loan.
`cancelled` is patron- or staff-initiated. `lost` can be set at any point
after `in_transit`.

The patron only sees status updates that are marked patron-visible; staff
notes (cost negotiation, partner correspondence) stay internal.

### Eligibility rules

The default eligibility check, from the seeded staff KB article *How to
Process an Interlibrary Loan (ILL) Request*:

- Patron has an active library card in good standing.
- No overdue items more than 30 days past due.
- No more than 5 active ILL requests at once.

These are guidance, not hard-coded blocks. Staff can override at the desk.
Cite the seeded article for the canonical procedure -- the doc you're reading
explains the *system*; the KB article explains the *workflow*.

## Consortium overview

A **consortium** is a named group of member libraries with a shared agreement
about reciprocal borrowing, billing, and patron access. ILL between
consortium members is faster and cheaper than ILL to outside libraries
because patron records, catalog visibility, and billing are already in place.

L30's consortium model is built around three tables (see
`backend/app/models/multi_branch.py`):

- `Consortium` -- the named group itself (e.g. "Northeast Ohio Reciprocal").
- `ConsortiumMember` -- one row per member library, with its membership type
  (`full`, `associate`, `reciprocal_only`) and status (`active`, `suspended`,
  `pending`, `terminated`).
- `ConsortiumPatronLink` -- a row per patron who has authenticated against a
  partner library, enabling cross-library checkouts without a duplicate card.

> Consortium routing across non-L30 systems (i.e. automatic catalog search +
> request submission against an external consortium partner's ILS) is
> **partially shipped**. Within-L30 reciprocal lending and billing work
> today. Cross-ILS federation uses the `/api/v1/consortiums/.../searchable-
> systems` endpoint, which is wired and returns results, but the auto-route
> path through `/ill/staff/requests/{id}/auto-search` still falls back to a
> staff worklist for non-L30 targets. Treat the auto-search as a hint, not a
> hands-off pipeline, until that integration lands.

### Which libraries are in the consortium

There is no hard-coded list. Each L30 deployment defines its own
consortium(s) at [/staff/admin/consortium](/staff/admin/consortium). At
install time, the consortium list is empty. To see who is currently a
member:

1. Go to [/staff/admin/consortium](/staff/admin/consortium).
2. Pick the consortium from the list (if you have more than one).
3. The **Members** tab lists every member library with its status and
   membership type.

API: `GET /api/v1/consortiums/{consortium_id}/members`.

### How routing works

When a patron submits an ILL request, the borrowing library's L30 instance:

1. Checks the local catalog one more time (race-condition guard).
2. Calls `searchable-systems` to enumerate consortium members willing to
   lend this item type.
3. Queries each candidate's catalog API and ranks results by proximity,
   delivery time, and any per-partner cost.
4. If a clear winner is found, status moves to `located`; otherwise the
   request stays `searching` and staff intervene from
   [/staff/interlibrary-loan](/staff/interlibrary-loan).
5. Once staff (or the auto-router) submits to the chosen lender, status
   moves to `submitted`. From here, the lender drives the lifecycle.

For non-consortium ILL (a partner library outside any of your consortia),
skip steps 2 and 3 -- the request goes straight to a staff worklist for
manual lender selection.

## Setting up an ILL vendor or partner library

A **partner library** is any library you exchange ILL materials with. It
does not have to be in a consortium; many libraries have a long list of
informal ILL partners. Partner data lives in `ill_partner_libraries`.

To add a partner:

1. Confirm `ill_enabled` is on for your library system.
   Admin -> Feature flags -> `ill_enabled`. If it isn't there, your
   organization plan doesn't include ILL; contact your admin.
2. Go to [/staff/interlibrary-loan](/staff/interlibrary-loan) and open
   the **Partners** tab.
3. `+ New partner`. Required fields: name, short code (used on shipping
   labels and in reports -- make it memorable, like `CLE-PUB` for
   Cleveland Public), contact email, address.
4. Optional but recommended: shipping method default (`usps`, `ups`,
   `fedex`, `courier`, `digital`), per-request fee if any, average
   turnaround in days, and whether they accept rush requests.
5. Save. Status defaults to `active`. Use `inactive` to keep the history
   but stop offering them as a lender; use `suspended` for short-term
   issues (e.g. they're closed for renovation).

API: `POST /api/v1/ill/staff/partners`.

To edit a partner: `PATCH /api/v1/ill/staff/partners/{partner_id}`, or
the same screen.

> Partner libraries and consortium members are **separate records**. A
> library can be both -- e.g. CLE-PUB is in your reciprocal consortium
> *and* a partner record exists for ILL bookkeeping. The partner record
> is what shipping labels and cost reports key off; the consortium member
> record is what reciprocal billing keys off. Keep both in sync (same
> code, same address) to avoid confusion.

## Processing an outgoing ILL request end-to-end

This is the "we are borrowing on behalf of a patron" path. Circulation
staff: see
[Circulation -- ILL handling](../staff-training/roles/circulation/ill-handling.md)
for the desk-side version with screen-by-screen steps.

1. **Request arrives.** Either a patron submits via the catalog
   ([`POST /api/v1/ill/requests`](#)), or staff create one on a patron's
   behalf ([`POST /api/v1/ill/staff/requests`](#)). New requests land in
   `pending` and appear at
   [/staff/interlibrary-loan](/staff/interlibrary-loan) under **New
   requests**.
2. **Triage.** Confirm eligibility (see Eligibility rules above). If the
   request doesn't qualify, status -> `cancelled` with a patron-visible
   note explaining why.
3. **Locate a lender.** Click `Auto-search`
   (`POST /api/v1/ill/staff/requests/{id}/auto-search`). Pick from the
   ranked list, or override manually. Status moves to `located` or
   `not_found`.
4. **Submit to lender.** Send the request -- email, OCLC, or whatever
   the partner accepts. Update the L30 record: status -> `submitted`,
   note the lender and expected ship date.
5. **Lender responds.** When the lender approves and ships, set status
   to `approved` then `in_transit`. Each transition can carry a
   patron-visible tracking update via `POST /api/v1/ill/staff/requests/
   {id}/tracking`.
6. **Receive the item.** Status -> `received`. Apply the ILL barcode
   label. The system generates a temporary catalog stub so it can be
   checked out in the normal circulation flow.
7. **Check out to patron.** Status -> `checked_out`. Hand over the item,
   call out the (typically shorter, non-renewable) due date.
8. **Renewal (sometimes).** If the patron asks for more time:
   `POST /api/v1/ill/staff/requests/{id}/renew`. The system asks the
   lender; only their approval extends the loan.
9. **Return.** Patron returns -> status `returned`. Print the return
   shipping label
   (`GET /api/v1/ill/staff/requests/{id}/shipping-label`), pack, ship.
   Status -> `return_in_transit`.
10. **Close.** Lender confirms receipt -> status `completed`. Record any
    final costs against `POST /api/v1/ill/staff/requests/{id}/costs`.

## Processing an incoming ILL request end-to-end

This is the "another library is borrowing one of ours" path.

1. **Request arrives.** From a consortium partner (auto-created via the
   federation API) or by email/phone from a non-consortium partner.
   Create the record at
   [/staff/interlibrary-loan](/staff/interlibrary-loan) -> **New request**
   -> type `lend`.
2. **Verify availability.** Pull up the item in the local catalog. If
   it's checked out or on hold, set status to `denied` with a reason --
   the borrowing library will requeue or look elsewhere.
3. **Pull and process.** Pull the item, route to ILL prep (envelope,
   ILL slip, due date sticker). Status -> `approved`.
4. **Ship.** Pack, ship via the partner's preferred method, status ->
   `in_transit`. Print the shipping label from the partner record's
   `shipping_method` default. Record the tracking number in a tracking
   update.
5. **Borrowing library reports `received`.** Their system or staff
   notifies us. Status mirrors to `received`. Nothing else for us to
   do until the return.
6. **Borrowing library reports `returned`** and ships back. When the
   package arrives at our desk: status -> `completed`, re-shelve or
   route to the cataloging review queue if condition has changed.
7. **Lost in transit.** If the item doesn't arrive at either end within
   30 days of the expected date, status -> `lost`. Add a cost record
   with category `lost_item` for the borrowing library to settle via
   the consortium billing cycle (or a direct invoice for non-consortium
   partners). See *Lost-in-transit* below.

## Tracking, due dates, renewals, returns, lost-in-transit

- **Tracking updates** are append-only on every request:
  `POST /api/v1/ill/staff/requests/{id}/tracking`. Toggle
  `is_patron_visible` per update -- a default of "visible" is fine for
  most milestones; keep internal correspondence private.
- **Due dates** for outgoing ILL items are set by the lender and stored
  on the request, not the catalog item. The shorter of (lender's date,
  local policy ceiling) is what circulation enforces. Local policy
  default is 3 weeks; override per request if the lender allows more.
- **Renewals** are not automatic. Patron-side renewal is disabled on
  ILL items by design; staff must explicitly request it via
  `POST /api/v1/ill/staff/requests/{id}/renew`, which generates a
  patron-visible "renewal requested" tracking entry.
- **Returns** trigger the return-shipping-label flow. The label is
  generated server-side from the partner's address; if the partner
  record is missing an address, the endpoint returns 404 -- fix the
  partner record first.
- **Lost-in-transit** is its own status (`lost`). Set it manually when
  a package is overdue by the agreed grace period (default 30 days,
  configurable per partner). It does not auto-bill -- staff add a cost
  record so the lost item appears on the next consortium billing cycle
  or partner invoice.

## Consortium settings

Available at [/staff/admin/consortium](/staff/admin/consortium) when
`outreach_enabled` is on. Each consortium has its own settings page;
member libraries see their own member-level overrides.

| Setting | Where | What it controls |
|---------|-------|------------------|
| Consortium-wide defaults | `PATCH /api/v1/consortiums/{id}/settings` | Default loan periods, default cost-sharing %, billing currency, billing cadence. |
| Reciprocal borrowing | `PATCH /api/v1/consortiums/members/{member_id}/reciprocal-settings` | Per-member overrides: max active loans, allowed item types, blackout dates. |
| Billing generation | `POST /api/v1/consortiums/{consortium_id}/billing/generate` | Roll up the last cycle's costs into invoices. |
| Billing payment | `POST /api/v1/consortiums/billing/{billing_id}/pay` | Mark an invoice paid. |
| Billing dispute | `POST /api/v1/consortiums/billing/{billing_id}/dispute` | Open a dispute; freezes the invoice pending resolution. |
| White-label per member | `PUT /api/v1/consortiums/members/{member_id}/white-label` | Hosted catalog branding for member-specific subdomains. |
| Invoice export | `GET /api/v1/consortiums/billing/{billing_id}/export/pdf` and `.../export/csv` | Download for board packets or accounting upload. |

## Reports

Three built-in reports under [/staff/interlibrary-loan](/staff/interlibrary-loan)
-> Reports:

- **Fill rate** (`GET /api/v1/ill/staff/reports/fill-rate`) -- percentage of
  outgoing requests that resulted in a delivered item. Useful for picking
  which partners to lean on.
- **Costs** (`GET /api/v1/ill/staff/reports/costs`) -- breakdown by category
  (`shipping`, `lending_fee`, `photocopy`, `processing`, `lost_item`,
  `damage`, `other`) and partner, for a date range.
- **Reciprocal lending dashboard**
  (`GET /api/v1/ill/staff/reports/reciprocal-dashboard`) -- borrow-vs-lend
  balance with each consortium member. A persistent imbalance can be a
  conversation-starter at the next consortium meeting.

## If it didn't work

- **`/staff/interlibrary-loan` 404s or shows "Feature not available".**
  `ill_enabled` is off for your library system. Admin -> Feature flags
  -> turn on `ill_enabled`, refresh. See
  [Admin settings](admin-settings.md) for where the flag lives.
- **`/staff/admin/consortium` 404s.** `outreach_enabled` is off. Same
  fix as above, different flag.
- **`Auto-search` returns nothing.** Either no partner libraries are
  configured, or none has the item type marked as lendable. Check
  **Partners** first, then per-consortium reciprocal settings.
- **Return shipping label endpoint 404s.** The partner library record
  is missing an address. Edit the partner, save, retry.
- **Consortium billing generation creates a $0 invoice.** No cost
  records exist for the billing period. Confirm staff are recording
  costs via `POST /api/v1/ill/staff/requests/{id}/costs` at the time of
  shipping; back-fill if needed before re-running generation.
- **Patron sees a status they shouldn't.** A tracking update was marked
  patron-visible by mistake. There is no per-update redact today (TODO
  -- if this becomes a recurring issue, file a feature request). For
  now, add a corrective patron-visible tracking note.

## Related

- [Front desk -- ILL section](front-desk.md) for the circulation-counter
  overview.
- [Circulation -- ILL handling](../staff-training/roles/circulation/ill-handling.md)
  for desk-side step-by-step procedures.
- [Admin settings -- feature flags](admin-settings.md) to toggle
  `ill_enabled` and `outreach_enabled`.
- Staff KB: *How to Process an Interlibrary Loan (ILL) Request* (seeded;
  see `backend/app/seeds/seed_staff_knowledge_base.py`).
- Patron KB: entry #147 *Requesting an Interlibrary Loan*, plus the two
  new entries added 2026-05-17 (*How do I request a book the library
  doesn't have*, *How long do interlibrary loans take*).
