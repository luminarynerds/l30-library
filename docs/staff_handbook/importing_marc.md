# Importing MARC Records

This page explains how to bring MARC records into L30. It is written for catalogers and library directors. No code knowledge is assumed except for the optional command-line section near the end.

## What this is

Importing is the mirror image of [exporting MARC](exporting_marc.md). Where the export turns L30 records into a MARC21 (or MARCXML) file that other systems can read, the import takes a MARC file produced by someone else, previews it, and adds the records to your catalog.

Most public libraries import MARC for four reasons: bringing in vendor records that ship with a book order, copy-cataloging from the Library of Congress or OCLC, migrating from a previous ILS, and pulling a peer L30 library's records when you join a consortium or share a collection.

L30 treats every import the same way: parse the file, show you a preview, let you decide what to do with each record, and only then write to the catalog. There is no silent "import 5,000 records" path that bypasses staff review.

## The four import paths

### 1. From a file you already have

Use this when a vendor (Baker & Taylor, Ingram, Brodart) emails you a MARC file with your latest order, or when you've downloaded a file from MarcEdit, WorldCat, or another library system.

1. Open the **Staff Tools** menu in the top navigation.
2. Click **Cataloging** to land on `/staff/cataloging`.
3. Choose **Import MARC file**.
4. Drag the file in, or click to browse. Files up to **50 MB** are accepted in a single upload. Larger files should be split in MarcEdit first.
5. Choose the format: **MARC21 binary** (`.mrc`, `.marc`) or **MARCXML** (`.xml`).
6. Click **Upload to preview**.

The upload itself does not change the catalog. It creates an import job in `pending` state and returns a preview screen showing every record in the file with its title, author, ISBN, LCCN, publisher, year, and a **match column** indicating whether L30 already has a record with the same ISBN.

You then walk down the list and pick an action for each record:

- **Import** — create a new `CatalogItem` from the MARC record.
- **Merge** — fill in missing fields on the existing matched record (publisher and year only; the merge is intentionally conservative and will not overwrite anything you already have).
- **Skip** — do nothing.

Click **Execute import** to commit your decisions. The job moves to `completed`, and the summary shows how many records were created, updated, skipped, and errored.

### 2. From Z39.50 or SRU (copy cataloging from LC or OCLC)

Use this when you have a book in hand and want to pull its record from the Library of Congress or OCLC WorldCat rather than typing it from scratch.

1. From `/staff/cataloging`, choose **Copy cataloging (Z39.50)**.
2. Pick the source: **Library of Congress** (no authentication required, open to all libraries) or **OCLC WorldCat** (requires your library's OCLC credentials, configured by an admin under **Settings → Z39.50**).
3. Enter an ISBN, title, or author. ISBN search is the most accurate; title + author is the most forgiving when an ISBN isn't printed.
4. The system returns up to 50 candidate records. Click one to see the full MARC view.
5. Click **Import to catalog** to write it as a new `CatalogItem`, or **Import to BIBFRAME** to send it through the BIBFRAME-aware import path (see [bibframe_workflow.md](bibframe_workflow.md)).

Z39.50 availability depends on the `PyZ3950` library being installed on the L30 server. If the page shows "Z39.50 service unavailable," ask your L30 admin — this is a server configuration issue, not a catalog issue.

OCLC connections additionally require credentials that an admin sets up under **Settings → Z39.50**. If OCLC search returns "requires authentication," that is the missing piece.

### 3. From OCLC by control number

If you already know the OCLC control number for a record (you've found it in WorldCat and want to pull it), use the direct-fetch endpoint. The Z39.50 page exposes a **Lookup by OCLC number** form for this; it fetches the single record and offers the same import-to-catalog or import-to-BIBFRAME choices as above.

This is also the path the librarian-agent MCP `catalog_import_from_oclc` tool uses when invoked from a chat session. The result is identical: a single record fetched from OCLC and previewed before write.

### 4. From another L30 instance

Use this when you want to bring in records from a peer L30 library — a consortium partner, a sister branch, or a library you're helping migrate.

The simplest path is to ask the peer library to run a MARC export (see [exporting_marc.md](exporting_marc.md)) and send you the resulting `.mrc` file. From there, follow **path 1 above** to import it.

There is no direct library-to-library push or pull endpoint in L30 today. The file handoff is intentional: each library retains full control over what enters its catalog, and there is always an exported file in the audit trail.

## Validation and dedupe

### What gets validated

The MARC parser (`pymarc`) reads the file and rejects records that are structurally invalid. Common reasons a record gets dropped:

- The MARC leader is missing or malformed.
- The record body is truncated.
- The encoding is misdeclared (e.g., a MARC-8 file marked as UTF-8).

For MARC21 binary files, L30 reads **leader byte 9** to choose the encoding (`a` = UTF-8, space = MARC-8). Older Polaris, Sierra, Koha, and Evergreen exports often ship as MARC-8 with diacritics or non-Roman scripts. L30 decodes these correctly. If you see U+FFFD replacement characters in the preview, the source file is mislabeled — ask the originating library to re-export with the correct encoding byte, or open the file in MarcEdit and force-convert before re-uploading.

### How dedupe works

During preview, every record in the upload is checked against the catalog by **ISBN** (`020$a`). If an existing `CatalogItem` has the same ISBN, the row is marked **match found** and defaults to the **Merge** action; otherwise it defaults to **Import**.

A few notes on the matching:

- The check is exact-string on the ISBN as parsed from `020$a`. ISBN-10 and ISBN-13 are not currently cross-walked at preview time, so a record with the ISBN-13 will not match an existing row that only has the ISBN-10, and vice versa. If you know you have records under both forms, prefer **Skip** on the duplicates and reconcile manually.
- Records without an ISBN are never marked as matches at preview time. They default to **Import**. If you're loading a DVD or a kit (no ISBN), you'll need to spot-check the title list to avoid duplicates.
- Matching by OCLC number (`035$a`) at preview is not yet wired. TODO: verify with cataloger whether this is a near-term need.

### What happens on conflict

The merge action is deliberately narrow. Today it only fills in `publisher` and `publication_year` on the matched record if those fields are currently empty. It does not overwrite a title, author, subjects, call number, or any other field. The reasoning: an automated overwrite of cataloger work is hard to undo and easy to regret.

If you want to apply a richer update from a MARC record to an existing catalog item, do it through the **single-record cataloging editor** (open the record, click **Edit MARC**, paste or load the new field values), or use a [MARC macro](marc_macros.md) for a targeted batch fix.

If both records have the same ISBN but you want to keep them as separate catalog items (different editions, large-print vs. regular, or simply two physical copies tracked separately), choose **Import** instead of **Merge**. L30 does not enforce ISBN uniqueness on `catalog_items`.

## Batch logging

Every import — whether one record or five thousand — creates a row in `marc_batch_jobs`. You can review past imports under **Staff Tools → Cataloging → Recent batches**, or directly at `/staff/cataloging` (the recent-jobs panel sits below the main import form).

Each job row records:

- The uploaded file name and format.
- The user who ran it.
- The total records, created, updated, skipped, and errored counts.
- Per-record errors, with the index of the offending record and the underlying error message.
- The timestamps for parse, execute, and completion.

This is also the audit trail you want to point at if a consortium ever asks "when did you load file X."

## Optional: the command-line path

For libraries that run a nightly vendor-feed cron, the upload + execute flow is available through internal API calls; there is not yet a dedicated CLI command for "import this file end-to-end with default actions." TODO: verify with cataloger whether a `app.cli.import_marc` companion to the export CLI is worth adding.

For one-off batches, the UI is faster than scripting, and the preview step catches encoding or structural problems before they hit the catalog.

## Known limitations

A few honest constraints to set expectations.

**ISBN-only dedupe at preview.** Records without an ISBN, or with an ISBN-10 vs. ISBN-13 mismatch against an existing row, will not be flagged as duplicates at preview time. Spot-check the title list before clicking **Execute import**.

**Merge fills only `publisher` and `publication_year`.** This is intentional. To apply richer updates from a MARC record onto an existing catalog item, use the single-record editor or a MARC macro.

**50 MB upload limit per file.** Files above 50 MB must be split in MarcEdit. A typical vendor-order file is well under this; a full-collection migration file may exceed it.

**Sync to BIBFRAME may lag.** A record imported through path 1 (file upload + execute) is created as a `CatalogItem`. Dual-write to BIBFRAME happens automatically on the create, but the BIBFRAME sync has a [known column-mismatch issue](bibframe_workflow.md#known-issue-column-mismatch-in-sync) that can drop the BIBFRAME side of certain records. If you imported a record and don't see it in the BIBFRAME view, check the BIBFRAME workflow page.

**No 949 vendor field handling.** Some vendors emit a 949 with shelving location and call number. L30 does not currently parse 949 into item-level holdings on import. Holdings must be added through the item-editor after import. TODO: verify with cataloger whether 949 parsing is a near-term priority.

## Who to ask

For questions about how to run an import or how to interpret a preview, contact your library's L30 admin. They can walk through a preview with you, retry a failed batch, or check the recent-jobs panel for prior runs.

For suspected bugs in the parser (records that should parse and don't, encodings that come through garbled, dedupe matches that should fire and don't), report the issue through the L30 issue tracker. Include a small sample file (or a redacted excerpt) and the preview screenshot when possible.
