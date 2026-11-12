# Acquisitions

Pages under the sidebar "Acquisitions" workflows and the admin EDI surface.
Requires `acquisition_enabled`. When the flag is off, the routes below render
the "feature not enabled" placeholder and the sidebar entries are hidden;
turn it on at [Library Configuration](admin-settings.md#library-configuration-staffadminlibrary-config).

Acquisitions in L30 covers vendor records, funds and budget rollover,
selection lists and purchase requests, purchase orders, EDI transmission
(EDIFACT or X12) including invoices and shipment notices, donations intake,
and the material-cost rate table used for replacement billing.

Most pages are gated by `Auth` (any signed-in staffer). The EDI settings
page additionally requires `AdminAuth`. Several writes here move real money
or send messages to outside vendors — read the warnings.

---

## Workflow surfaces

### Acquisitions Hub (`/staff/acquisition`)
Tabbed landing page with Funds and Vendors as primary tabs (the legacy
`/staff/acquisitions` path 301-redirects here). Use as your map for
day-to-day work. Read-only at the hub level — actual edits happen in the
tab forms.

### Vendors (`/staff/vendors` and the Vendors tab)
List, create, and edit vendor records. Required fields: vendor code (used
in PO numbers and EDI envelopes), legal name, contact email, default
currency. Optional: SAN, GLN, default discount, default fund. The vendor
record is metadata only — EDI credentials live on the EDI profile, not
here. Backed by `/api/v1/acquisition/vendors`. The detail page also exposes the
serial-subscriptions summary and a vendor-spend summary card.
See also: [EDI Settings](#edi-settings-staffadminedi).

### Funds (`/staff/funds`)
Per-fund budget tracking: allocation, encumbered, expended, free balance.
Funds drive PO budget validation; a PO that would push a fund over its
encumbered ceiling is blocked at approve time, not at submit time. Use
"Rollover" at fiscal year-end to carry forward unspent balances per your
policy. Backed by `/api/v1/acquisition/funds` and `/api/v1/acquisition/funds/rollover`.

### Selection List (`/staff/selection-list`)
Working pool of titles being considered for purchase. Selectors add items
from catalog search, ISBN lookup, or external-vendor search. Items can be
approved, rejected, or rolled into a PO directly via "Convert to PO,"
which copies the selected lines into a draft purchase order. Backed by
`/api/v1/acquisition/selection-list`.

### Selector Dashboard (`/staff/selectors`)
Per-selector view: their open selection items, conversion rate, fund
utilization. Helpful for collection-development leads doing 1:1s with
their team. Read-only.

### Purchase Requests Queue (`/staff/purchase-requests`)
Staff-side intake for patron purchase suggestions (the patron form lives
at `/suggest-purchase`). Approve, decline (with a template
reason), or link to an existing PO. Bulk approve/decline are available
for clearing duplicate suggestions. Backed by `/api/v1/purchase-requests`.
See also: [Selection List](#selection-list-staffselection-list).

### Donations (`/staff/donations`)
Track incoming donated materials: donor, intake date, item count,
condition, accept/reject decision. The "process" action moves accepted
items into the catalog intake flow (or weeding, if rejected). Useful
audit trail for tax-receipt requests. Backed by `/api/v1/donations`.

### Acquisitions Management (`/staff/admin/acquisition`)
Admin overview for the whole acquisitions module: open POs, fund health,
overdue receipts, recent EDI activity. AdminAuth required. Use this when
something is "stuck somewhere in acquisitions" and you want the full
picture before drilling in.

---

## Purchase orders

POs are the spine of acquisitions. Lifecycle: `draft` → `submitted` →
(`partially_received` →) `received`, with `approve` / `reject` gates
depending on your circulation-policy config.

### Create a PO
Three entry points, all hitting `POST /api/v1/purchase-orders`:
1. From a Selection List ("Convert to PO" — bulk).
2. From an Order Template at `/api/v1/order-templates/{id}/create-po`
   (good for recurring standing orders).
3. Manually from the PO detail page (add lines one at a time or via
   ISBN-bulk lookup).

### Send a PO
Two transmission modes, picked per vendor:
- **Email** — `POST /purchase-orders/{po_id}/email-vendor` attaches a
  generated PDF (also downloadable at `/purchase-orders/{po_id}/pdf`).
  Used for vendors without EDI.
- **EDI** — `POST /api/v1/edi/send-order` packages the PO as an EDIFACT
  ORDERS or X12 850 message and transmits via the vendor's configured
  EDI profile. Validate with "Test Connection" on the EDI profile first;
  the send call refuses if the vendor has no active profile.

### Approve / receive
- `PATCH /purchase-orders/{po_id}/approve` flips draft → submitted and
  encumbers funds. Subject to budget validation (`/budget-validation`).
- `PATCH /purchase-orders/{po_id}/receive` records receipt — full or
  partial. Partial receipt sets `partially_received`; subsequent receives
  on the same PO accumulate until everything is in.
- Inbound EDI shipment notices (DESADV / X12 856) **auto-receive** when
  linked to an open PO (see spec `docs/specs/2026-05-07-edi-po-integration-spec.md`).
  Manual receipt is still available for short shipments, damaged items,
  or anything the auto-receive logic flags.

---

## EDI

### EDI Settings (`/staff/admin/edi`)
AdminAuth + `acquisition_enabled`. Manage vendor EDI profiles, run the
inbound poller, view transactions, reconcile invoices, watch statistics.
This is the only EDI configuration surface — everything else is read-only
status.

### Vendor EDI profiles
One profile per vendor that supports EDI. Fields:
- **EDI standard:** `edifact` or `x12`. Most US trade partners are X12,
  most international and library-specific (e.g. BIC) are EDIFACT.
- **Transport protocol:** `sftp` (default), `ftp`, `as2`, or `http`.
  SFTP is the path of least resistance — credentials are a host, port,
  username, and either a password or a key reference.
- **Sender/receiver IDs** (ISA/UNB qualifiers), inbound and outbound
  folder paths, optional pre-shared key for AS2.
- **Test mode** flag — when on, messages are written to the outbound
  folder but flagged so the partner can drop them.

After creating a profile, hit **Test Connection** before sending live
traffic. The test just opens the transport, lists the inbox folder, and
reports success — it does not validate that the partner can parse your
envelopes.

### Sending an order
Click "Send via EDI" on a submitted PO, or call `/api/v1/edi/send-order`
directly. The processor builds the message, writes a transaction row in
`pending`, ships the file, then flips the row to `sent`. Failures stay
`pending` with an error string; use the **Retry** action on the
transaction row to re-send after fixing the underlying issue.

### Inbound processing
"Process Inbound" on the settings page (or `POST /edi/process-inbound`)
polls every configured profile's inbound folder, parses any new files,
and creates the appropriate domain rows:
- **ORDRSP / 855** → vendor order responses (price/availability changes).
- **DESADV / 856** → shipment notices, which auto-receive their linked PO.
- **INVOIC / 810** → invoices, queued for reconciliation.

The poller is **manual by default** — schedule it via the scheduler at
`/staff/admin/scheduler` if you want hands-off processing.

### Invoices and reconciliation
- **List:** `/api/v1/edi/invoices` (mirrored in the settings UI).
- **Reconcile:** matches invoice lines against PO lines on ISBN +
  quantity + unit price (within tolerance). One-off:
  `/invoices/{id}/reconcile`. Bulk: `/invoices/batch-reconcile`.
- **Approve / dispute:** `/invoices/{id}/approve` releases the invoice
  for payment in your finance system; `/dispute` flags it for vendor
  follow-up with a note.
- **Auto-approve:** `/invoices/auto-approve` approves every invoice that
  reconciled cleanly under the configured tolerance. Run only after you
  trust your tolerance settings — the action is audit-logged but not
  reversible.

### Transactions and statistics
The Transactions tab lists every EDI message in or out, with a detail
drawer that shows the raw envelope. Statistics shows volume and
success-rate trends by partner. Both pull from `/edi/transactions` and
`/edi/statistics`.

---

## Material costs

The material-cost rate table feeds replacement charges in
[Front Desk](front-desk.md) billing and lost-item processing in
[Circulation & Policy](admin-settings.md#circulation--policy-staffadmincirculation-policy).
The legacy route `/staff/admin/material-costs` 301-redirects to the
`#material-costs` anchor on Circulation & Policy — edit rates there.

The patron-facing read-only price-transparency list at `/material-costs`
is backed by `/api/v1/material-costs` (full router) and is wired
end-to-end. The admin CRUD at `/api/v1/admin/material-costs/*` is a stub
that returns empty lists and "Not yet implemented" responses — the dashboard,
categories, bulk update, import/export, audit log, and methodology endpoints
are all placeholders. **Edit rates via the Circulation & Policy financial
config section**, not via a direct admin-material-costs API call.

---

## Reports

- **Open POs / receipts overdue** — Acquisitions Management
  (`/staff/admin/acquisition`).
- **Vendor spend and performance** — vendor detail page (summary card)
  and the Strategic / Analytics dashboards at
  [Analytics](admin-settings.md#analytics-staffadminanalytics).
- **Fund utilization** — Funds page rolls up encumbered vs expended per
  fund per fiscal year.
- **EDI volume and error rate** — EDI Settings → Statistics tab.

Cross-fiscal-year spend rollups currently come from the general
[Reports](reports.md) module — there is no acquisitions-specific
annual export beyond the fund rollover artifact.

---

## Common errors

- **"Vendor has no active EDI profile"** on Send via EDI — create or
  re-activate the profile at `/staff/admin/edi`.
- **"Connection test failed"** — usually wrong host/port, wrong path
  separator on Windows-side SFTP servers, or a key that the partner
  hasn't whitelisted. Check `docker logs l30-backend` for the underlying
  paramiko/ftplib error.
- **DESADV arrives but PO doesn't auto-receive** — the PO either isn't
  in `submitted`/`partially_received` status, or the ISBN normalization
  didn't match (hyphens/spaces are stripped, but ISBN-10 vs ISBN-13
  mismatch will miss). Receive manually and file a follow-up.
- **Invoice reconciliation flags everything as mismatched** — check the
  vendor's price units (cents vs dollars) and your fund currency.
  Reconciliation tolerance is a percentage, not an absolute amount.
- **Encoding errors on inbound EDIFACT** — partners that send UNOC
  (Latin-1) when you expect UNOB (ASCII) need a profile change. The
  parser will write a transaction row with status `parse_failed` and the
  raw bytes preserved for inspection.
- **PO approve blocked with "fund over budget"** — check the fund
  detail; an earlier draft PO may already be encumbering the balance.
  Cancel or reduce the older PO first.
- **`/staff/admin/material-costs` shows nothing** — expected; the admin
  CRUD is a stub. Use the Circulation & Policy financial config section
  to edit rates.
