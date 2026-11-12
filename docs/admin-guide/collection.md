# Collection

Sidebar "Collection" group. Requires `collection_management_enabled`.
These are the cataloging, inventory, and acquisitions surfaces. Many
operations write to the catalog and trigger search re-index, so be
deliberate.

---

### Collection Hub (`/staff/collection-hub`)
Landing page. Tile-grid of every collection surface (cataloging, MARC
tools, inventory, analytics, acquisitions). Use as your map.

### Collection Intelligence (`/staff/collection-dashboard`)
Cross-module health overview: format distribution, age distribution,
gaps, condition trends. Read-only. Heaviest dashboard in the module —
load with the date range you actually need.

### Cataloging (`/staff/cataloging`)
Primary cataloging interface: search, create, edit, copy records. Pulls
from Z39.50 sources configured at `/staff/admin/z3950`. Edits are
versioned; you can revert.

### Manga Cataloging (`/staff/manga-cataloging`)
Specialized cataloging view tuned for manga series (volume linking,
series navigation, original-language title handling).

### Comic Cataloging (`/staff/comic-cataloging`)
Specialized cataloging view tuned for single-issue comics and TPB
collections.

### Lexile Bulk Import (`/staff/cataloging/lexile-import`)
Bulk import or update Lexile reading levels for catalog items.
Useful for school partnership data feeds.

### MARC Macros (`/staff/marc-macros`)
Reusable MARC editing macros (e.g. "add 856 link", "normalize 245
punctuation"). Cuts down repetitive cataloging keystrokes.

### Export MARC (`/staff/export-marc`)
Export catalog records as MARC for backup or consortium sharing.
Filter by date, location, format.

### Local Authorities (`/staff/local-authorities`)
Library-specific authority records (local subjects, names) that
augment LC/standard authorities.

### Linked Data (`/staff/linked-data`)
BIBFRAME linked-data view of the catalog. Mostly inspection/diagnostic;
sync issues to backend service surface here first.

### SPARQL (`/staff/sparql`)
**Internal tool.** SPARQL query console over the linked-data store.
For advanced diagnostics — most staff will never need this.

### Inventory (`/staff/inventory`)
Inventory dashboard: items in/out, by location, missing, recently
added. Operational view that pairs with weeding and shelf reading.

### Inventory Management (`/staff/inventory-management`)
Deeper inventory operations: copy-level history, condition updates,
withdrawal. Heavier writes than the dashboard.

### Mobile Audit (`/staff/inventory/mobile-audit`)
Mobile-optimized audit workflow for handheld devices. Scan-driven.

### Mobile Inventory Scan (`/staff/inventory/scan`)
Mobile-optimized item lookup/scan. Quick check-current-status flow.

### Shelf Reading (`/staff/shelf-reading`)
Shelf-reading assignments and tracking. Use to coordinate inventory
sweeps across staff.

### Staff Picks (`/staff/picks`)
Curate staff-pick lists shown to patrons. Active lists appear on the
public `/picks` page, feed the home page "Staff picks" shelf (newest
additions across all active lists), and the first active list is
highlighted on the catalog landing page. Any staff role can edit.

### Reading Lists (`/staff/reading-lists`)
Editorial reading lists for the patron-facing catalog.

### Curated Shelves (`/staff/curated-shelves`)
Not currently in use: shelves saved here are not rendered anywhere on
the public site. Use Staff Picks or the Home Page admin
(`/staff/home-page`) instead. Queued for removal in the next dead-code
sweep.

### Collection Analytics (`/staff/collection-analytics`)
Usage metrics, condition trends, cost efficiency. Format distribution
breakdown.

### Archival Collections (`/staff/admin/archival-collections`)
Special-collections admin: finding aids, accessions, restricted items.
Sidebar entry under Collection.

### Mood Categories (`/staff/admin/mood-categories`)
Curate the mood taxonomy used in catalog discovery. Sidebar entry
under Collection, but AdminAuth.
See also: [admin-settings.md](admin-settings.md#mood-categories-staffadminmood-categories).

### Weeding (`/staff/weeding`)
Weeding workflow: list candidates, mark for withdrawal, process.
Withdrawn items move out of circulation but are kept in history.

### Repair Queue (`/staff/repair-queue`)
Items awaiting repair. Track status from intake to return to shelf.

### Processing Queue (`/staff/processing`)
New items awaiting processing (RFID, spine label, jacket, etc.).
Requires `processing_queue_enabled`.

### Lost & Damaged (`/staff/lost-damaged`)
Operational lost/damaged queue. Pair with the report page
(`/staff/reports/lost-damaged`).

### Found Items (`/staff/found-items`)
Items reported lost that have been found and need to be reconciled
back to the patron.

### Content Flags (`/staff/content-flags`)
Patron-reported content concerns: handle, dismiss, escalate.

### Audiobook Review (`/staff/audiobooks/review`)
Editorial review queue for audiobook listings before publishing.

### Book Challenges (`/staff/book-challenges`)
Track formal book challenges/reconsideration requests. Requires
`banned_books_tracking_enabled`.

### Acquisition (`/staff/acquisition`)
Acquisitions main page: purchase orders, receiving, vendor management.
Requires `acquisition_enabled`.

### Acquisition Management (`/staff/admin/acquisition`)
Admin-level acquisitions: budgets, fiscal periods, vendor accounts.
Requires `acquisition_enabled`.

### Funds (`/staff/funds`)
Acquisition fund management: budgets, allocations, encumbrances.

### Vendors (`/staff/vendors`)
Acquisition vendor directory: contacts, account numbers, EDI config.

### Selection List (`/staff/selection-list`)
Working list of titles under consideration for purchase. Bridges
purchase requests and POs.

### Purchase Requests (`/staff/purchase-requests`)
Patron and staff suggestions for purchase. Triage, approve, deny.

### Donations (`/staff/donations`)
Track donated items: intake, evaluation, accept/discard.

### Selector Dashboard (`/staff/selectors`)
Per-selector dashboard for the staff member curating acquisitions.

### Fines (`/staff/fines`)
Fine management: lookup, adjust, waive. Requires
`financial_reports_enabled`.

### Interlibrary Loan (`/staff/interlibrary-loan`)
ILL request management: outgoing and incoming. Requires `ill_enabled`.

### Book Drop (`/staff/book-drop`)
Book drop management dashboard. Sub-pages: `/fast-process` for the
speed-checkin flow, `/:tab` for per-tab views.

### Fast Book Drop Process (`/staff/book-drop/fast-process`)
Streamlined check-in for clearing a full drop quickly.

### Review Responses (`/staff/review-responses`)
Respond to patron reviews/ratings on catalog items.

### Event Reviews (`/staff/event-reviews`)
Respond to patron reviews of events/programs.

### Storytime (`/staff/storytime`)
Storytime planning and tracking. Requires `storytime_enabled`.
