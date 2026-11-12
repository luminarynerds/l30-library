# BIBFRAME-Aware Cataloging in L30

This page explains how L30 keeps a BIBFRAME view of your catalog alongside the operational MARC-style catalog, when records get synced from one to the other, what to do if the sync fails, and how to inspect the linked-data state of a record.

It is written for catalogers and library directors. Some familiarity with BIBFRAME (Work / Instance / Item) helps; no code knowledge is assumed.

## What this is

L30 stores every catalog record twice, in two different shapes:

- The **operational catalog** (`catalog_items`) — a flat row-per-item table that mirrors the day-to-day MARC fields most ILS workflows expect. This is what circulation, search, and reports run on.
- The **BIBFRAME view** (`bibframe_works`, `bibframe_instances`, `bibframe_items`) — the modern Work / Instance / Item hierarchy that the Library of Congress is moving toward. Works are intellectual content, Instances are specific editions, Items are individual copies.

Why both? Because L30 is trying to do two things at once: be a working public-library ILS that staff can use today, and be ready to participate in the linked-data future that LC and the major academic libraries are building toward. The operational catalog keeps daily work fast and familiar. The BIBFRAME view keeps the library's data in a shape that can be exported, federated, and queried as linked data without a future migration project.

For 95% of cataloging work, you only see the operational view. The BIBFRAME side is dual-written for you, in the background. The other 5% is what this page is about.

## When records get synced to BIBFRAME

The sync is **dual-write on the operational catalog**. Every time a `CatalogItem` is created, updated, or deleted through the catalog API, L30 also writes the corresponding change to the BIBFRAME side:

- **Create a catalog item** → look up or create a `BibframeWork` (deduped by title), look up or create a `BibframeInstance` (deduped by ISBN + item type), and create a new `BibframeItem`. Contributors and subjects are also synced to the work.
- **Update a catalog item** → find the matching `BibframeItem` and update its status, location, and any other mirrored fields.
- **Delete a catalog item** → soft-delete the `BibframeItem`. The `BibframeWork` and `BibframeInstance` stay around, because other catalog items may still reference them.

This happens synchronously, inside the same database transaction as the catalog change. There is **no background sync queue and no scheduled batch sync**. If a record is in `catalog_items`, the BIBFRAME side should reflect it within milliseconds — unless the sync failed (see below).

The sync is invoked from:

- `backend/app/api/v1/catalog/crud.py` — single-item create, update, delete.
- `backend/app/api/v1/catalog/batch_update.py` — batch updates from the staff UI.

Imports through the [MARC batch import](importing_marc.md) flow create `CatalogItem` rows the same way single-item creation does, so BIBFRAME sync is triggered for each imported record.

## What happens if the sync fails

The sync is wrapped in a try/except: **if BIBFRAME sync fails, the catalog operation still succeeds.** The error is logged with full stack trace under `app.services.catalog_bibframe_sync`, but the catalog stays consistent — patrons can check the book out, staff can edit it, and circulation doesn't break.

This is the right tradeoff for an operational system. You do not want a BIBFRAME-side bug to take down circulation. But it does mean that a sync failure is **silent from the staff UI**: there is no toast, no error banner, no row in the recent-jobs panel. The only place a failed sync shows up is in the backend logs and in the divergence between `catalog_items` and `bibframe_*` row counts.

### Known issue: column mismatch in sync

There is a known bug in the BIBFRAME sync service where certain catalog item shapes cause a column mismatch when writing the BIBFRAME row. The symptom is:

- The `CatalogItem` is created or updated successfully.
- The BIBFRAME-side write fails inside the dual-write try/except.
- The error is logged but not surfaced to staff.
- The record is missing from the BIBFRAME view (search, JSON-LD export, federation) until the sync is re-run for that record.

The root cause is a schema drift between the operational catalog's column set and what the BIBFRAME mapping expects to read. It has not yet been fully fixed — see the L30 issue tracker for the active bug. Until then, treat the BIBFRAME view as eventually-consistent rather than strictly-consistent, and use the inspection tools below to verify a record's state when it matters.

If you find a record missing from the BIBFRAME view, the recovery path is:

1. Touch the catalog item (open it, save it without changes) to retrigger the dual-write — sometimes the sync succeeds on the second pass after a transient issue.
2. If the record still doesn't appear, ask your L30 admin to run a one-off resync against that specific catalog item ID. The admin can invoke `CatalogBibframeSync.create_from_catalog` against the row directly.
3. If a class of records is consistently failing, capture the log line (it includes the catalog item ID and the underlying exception) and report it to the L30 issue tracker — that is the data the engineering team needs to fix the column mismatch at the source.

There is no general "rebuild the entire BIBFRAME view" command exposed today. TODO: verify with cataloger whether a periodic admin-triggered full-resync would be useful.

## How to inspect the linked-data state of a record

When you need to confirm what BIBFRAME thinks about a record — for debugging a missing record, validating an export, or just exploring — L30 exposes several read-only endpoints under `/api/v1/bibframe-catalog/`.

### Browse the BIBFRAME view

- **`GET /api/v1/bibframe-catalog/search`** — full-text search across works, with filters for title, genre, language, publication year range. Returns a list of works with their instance and item counts.
- **`GET /api/v1/bibframe-catalog/`** — list works, paginated.
- **`GET /api/v1/bibframe-catalog/{work_id}`** — detail view of a single work, including its instances and the items under each instance.

If a catalog item should be in the BIBFRAME view and isn't, search by title and ISBN through these endpoints. A record present in `catalog_items` but absent here is a sync failure.

### Inspect a work as linked data

- **`GET /api/v1/bibframe-catalog/{work_id}/linked-data`** — returns the work, its instances, contributors, and subjects as **BIBFRAME JSON-LD** and **Schema.org JSON-LD**. This is the format that linked-data consumers (other library systems, search engines, federation partners) would see if your catalog were federated.

This is the canonical "is this record correctly modeled" check. If the JSON-LD looks right — the work has the right title, language, contributors, subjects, instances with ISBNs and carrier types, items with statuses — the BIBFRAME side is healthy. If a field is missing or null, that's a sync gap worth chasing.

### From the staff UI

There is no dedicated "BIBFRAME inspector" panel in the staff UI today. Inspection happens through the API endpoints above, which a director or admin can hit directly from a browser (they require authentication for some routes, but search and detail are open).

TODO: verify with cataloger whether a staff-UI BIBFRAME viewer (a "show me the linked-data view of this record" button on the catalog item detail page) is wanted on the near-term roadmap.

## What gets stored on the BIBFRAME side

A quick map of what lives where, so you know what to look for:

- **`BibframeWork`** — title, subtitle, work type (text, performed music, three-dimensional moving image, etc.), language, summary, genre form, table of contents, Dewey classification, origin date.
- **`BibframeInstance`** — ISBN-10, ISBN-13, instance type (print, electronic, audio, audiovisual, etc.), carrier type (volume, audio disc, online resource, etc.), media type (unmediated, computer, audio, video, etc.), publisher, publication date.
- **`BibframeItem`** — barcode, status (available, checked_out, on_hold, in_processing, lost, damaged, etc.), location, the instance it belongs to.
- **`BibframeContributor`** — name, role (creator, contributor, editor, etc.) — linked to works through a `work_contributors` association.
- **`BibframeSubject`** — heading, source — linked to works through a `work_subjects` association.

ISBNs on the operational catalog are stored as a single string. The sync **splits** the ISBN into `isbn_10` and `isbn_13` columns on the BIBFRAME instance based on length and check-digit shape (10 chars with optional `X` check digit goes to `isbn_10`; 13 digits goes to `isbn_13`). If your catalog ISBN is malformed, neither column is set and the BIBFRAME instance is created without an ISBN — this is benign but worth knowing if you're looking for a record by ISBN on the BIBFRAME side and can't find it.

## Dedupe behavior on BIBFRAME

The sync deduplicates aggressively to keep the BIBFRAME view tidy:

- **Works are deduped by exact title match.** Two catalog items with the same title share a work. This is intentional (different editions of the same book are different instances of the same work) but it means that two unrelated books that happen to share a title also collapse into one work. The current model accepts this in exchange for simplicity. TODO: verify with cataloger whether title+author dedup would meaningfully improve work-level accuracy without breaking the simple model.
- **Instances are deduped by ISBN + work.** Two catalog items with the same ISBN under the same work share an instance. Different ISBNs (or no ISBN) get separate instances.
- **Items are not deduped.** Every catalog item gets its own BIBFRAME item, identified by barcode and pointing at the instance.

## Known limitations

**Sync is silent on failure.** A BIBFRAME write failure does not surface to the staff UI. Discovery is through log inspection or through noticing a record is missing from the BIBFRAME view. The known column-mismatch bug above is the most common offender.

**No background resync.** There is no scheduled job that catches up sync failures or rebuilds the BIBFRAME view from `catalog_items`. Resyncs are admin-triggered, one record at a time.

**Title-based work dedupe.** Two unrelated books with the same title share a `BibframeWork`. Acceptable today; revisit if false positives become a usability problem.

**Operational catalog is the source of truth.** Edits made through a future BIBFRAME-side editor would need their own propagation path back to `catalog_items`. Today, all edits flow operational-catalog → BIBFRAME, never the other direction.

**No OAI-PMH or federation endpoint yet.** The linked-data JSON-LD is read-only, per-record. Bulk harvesting and live federation are not exposed.

## Who to ask

For questions about whether a specific record is correctly represented on the BIBFRAME side, contact your L30 admin. They can pull the JSON-LD view and resync a single record if needed.

For suspected bugs in the dual-write — especially anything that looks like the column-mismatch issue described above — capture the catalog item ID and the relevant log line (your admin can grep `catalog_bibframe_sync` in the backend logs) and report through the L30 issue tracker. The more example records you can attach, the faster the underlying schema drift can be tracked down.
