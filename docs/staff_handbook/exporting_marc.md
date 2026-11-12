# Exporting MARC Records

This page explains how to export MARC records out of L30 and into the systems that need them. It is written for catalogers, library directors, and IT-light admins. No code knowledge is assumed.

## What this is

L30 stores every bibliographic record in its catalog as structured data. The MARC export turns those records into a standard MARC21 file (or MARCXML, if you prefer the XML flavor) that any other library system can read.

Public libraries need outbound MARC for three everyday reasons: contributing holdings to a state union catalog, sending periodic updates to OCLC, and keeping the option open to move your data somewhere else. L30 should never be a one-way door for your catalog. The export is how you keep the door open.

## When you would use it

Three concrete situations come up most often.

**Contributing to a state or regional union catalog.** Consortia such as OhioLINK, MOBIUS, and SEFLIN ingest member holdings on a recurring schedule. Most ask for a MARC21 file of new and changed records since your last submission. Without an export, your library does not appear in the union catalog, and your patrons lose ILL discovery.

**OCLC reclamation or holdings update.** Even libraries that catalog directly in WorldCat send periodic holdings files. The standard format is MARC21 binary. The export gives you that file.

**Migrating to a different ILS, or pulling a backup you control.** If your library ever leaves L30, the export plus a CatalogItem CSV is your handoff. The library owns the data, and the export is how you walk out with it.

## What is in an exported record

Each exported record carries the fields a state union catalog or OCLC expects:

- **Leader.** Record status, type, bibliographic level, encoding level.
- **001 control number.** L30's internal catalog ID.
- **005 transaction date.** When the record was last touched in L30.
- **008 fixed-length elements.** Date, place of publication, language, intended audience.
- **020 ISBN** when present.
- **040 cataloging source.** Identifies L30 as the agency that created or transcribed the record.
- **050 Library of Congress call number** and **082 Dewey** when classified.
- **100 personal author** or **710 corporate author**, with name inversion handled.
- **245 title and statement of responsibility**, with non-filing characters set correctly.
- **250 edition** when present.
- **264 publication information.** Publisher, place, date.
- **300 physical description.** Pages, dimensions, format hints.
- **336/337/338 RDA content, media, and carrier types.**
- **490 and 830 series statements**, including multi-part sets.
- **500/505/508/520/521 notes.** General notes, contents, credits, summary, audience.
- **650 topical subjects.** Up to ten LCSH headings per record.
- **852 holdings.** One entry per item, with shelving location and call number.
- **856 ebook URLs** when the item has an online resource.

You can think of an exported record as a respectable MARC21 record that a state catalog or OCLC will accept on first read. It is not gold-master national-library cataloging, but it passes ingestion checks and reads cleanly in MarcEdit.

## What is not in an exported record

It helps to know what the export deliberately leaves out.

- **No authority `$0` URIs.** Authority links in L30 are tracked separately and not embedded in the exported subfield. State catalogs do not require them.
- **No 949 vendor-load fields.** Some legacy systems (Sierra in particular) expect a 949 for re-import. L30 does not emit one yet. If your destination needs 949, mention it to your L30 admin.
- **No OAI-PMH harvest endpoint.** L30 does not currently expose an OAI-PMH server. If a digital-library harvester asks for one, that is a separate conversation.
- **No 035 OCLC number for L30-originated records.** Records that came in from Z39.50 or a MARC import retain their original 035. Records originally cataloged in L30 do not yet carry an OCLC control number, because L30 does not assign one.

There is also one important caveat about the BIBFRAME side of the catalog. L30 keeps a BIBFRAME view of every record alongside the operational catalog. The export reads from the operational catalog, not from BIBFRAME. If a cataloger edited a record in the BIBFRAME UI, those edits may not appear in the exported MARC until the BIBFRAME sync service runs. If you notice a recent BIBFRAME edit missing from your export, wait for the next sync or ask your L30 admin to trigger one.

## How to run an export from the staff UI

This is the path most staff will use.

1. Open the **Staff Tools** menu in the top navigation.
2. Click **Export MARC**.
3. Choose a scope:
    - **All records** for a full catalog dump.
    - **Records changed since a date** for an incremental update to a union catalog.
    - **Single record by ID** for cataloger troubleshooting or one-off requests.
4. Choose a format. **MARC21 binary** is the right default for state union catalogs and OCLC. **MARCXML** is useful when the destination prefers XML or when you want to read the file in a text editor.
5. Optionally narrow by item type (books, ebooks, audio, and so on).
6. Click **Download**. The file streams to your browser.

Below the form you will see a **Recent exports** panel listing the last several export jobs, who ran them, when, and how many records were included. Each row has a download link if you need to grab the same file again.

## How to run an export from the command line

For libraries that want a nightly or weekly cron job feeding a state catalog, the same export is available as a command-line tool. This is for IT staff who have shell access to the L30 server.

The command shape is:

```
docker compose exec l30-backend python -m app.cli.export_marc --format marc21 --since 2026-01-01 > export.mrc
```

The flags map directly to the UI: `--format` chooses MARC21 or MARCXML, `--since` filters to records changed after a date, and the result is written to standard output, which you redirect into a file. From there you can SFTP the file to the consortium or hand it to whatever upload tool your destination uses.

This path requires shell access to the L30 VPS. Most libraries will use the UI for ad hoc exports and the CLI only for scheduled jobs.

## Validating an export before you send it

Before handing a file to a consortium or to OCLC, open it in **MarcEdit**. MarcEdit is the standard free tool for inspecting MARC files. Use the MARC Tools validator to confirm the file has no structural errors, then spot-check a handful of records to confirm the title, author, ISBN, call number, and holdings look right. Five minutes of validation here saves a frustrating rejection email later.

## Typical state union catalog workflow

A typical monthly submission to a state catalog looks like this:

1. In the UI, choose **Records changed since** the date of your last submission, format **MARC21 binary**, and download the file.
2. Open the file in MarcEdit. Run the MARC validator. Spot-check a few records.
3. Upload the file to the consortium's submission portal, or SFTP it to the target the consortium provided.
4. Note the date of this submission so you can use it as the starting point for next month.

L30 does not push directly to consortia. The librarian is the courier. This is intentional. You decide when and what to send, and you keep the audit trail.

## Typical OCLC workflow

OCLC submissions look similar, with one difference in tools:

1. In the UI, choose **All records** or **Records changed since** depending on whether this is a reclamation or an update. Format **MARC21 binary**.
2. Open the file in MarcEdit. Validate and spot-check.
3. Upload to OCLC Connexion as a local file, or use the OCLC batch upload tool your library has configured.

For libraries on a Cataloging or Metadata subscription, the upload portal is the destination. For reclamations, follow the specific reclamation instructions your OCLC contact provided. The export gives you the file; OCLC's tools handle the rest.

## Migrating off L30

If your library decides to move to another ILS, a **full MARC21 export plus a CatalogItem CSV** is the universal handoff format. The MARC file carries bibliographic data; the CSV carries item-level circulation status, barcodes, and acquisition data. Together they cover what almost any destination ILS needs.

The library owns the data. The export is the proof.

## Known limitations of the current writer

A few honest constraints to set expectations.

**Leader byte 05 is `n` (new) on first export.** When you export a record for the first time, the leader marks it as new. On subsequent exports of the same record, it flips to `c` (corrected). Most consortia handle this correctly. A small number of older ingestion scripts get confused by the `n` to `c` transition. If your destination flags it, mention this to your L30 admin.

**No 035 OCLC number for L30-originated records.** Records cataloged from scratch in L30 do not yet carry an OCLC control number, because L30 does not assign one. Records that came in from Z39.50 keep the OCLC number they were imported with. If your destination requires every record to carry an OCLC number, you will need to enrich the file in MarcEdit before submission.

**Large catalogs may be slow.** Catalogs above roughly 50,000 records may take more than a minute to export and could time out on a slow connection. For very large catalogs, prefer the CLI over the browser, or break the export into incremental slices by date.

## Who to ask

For questions about how to run an export, contact your library's L30 admin. They can run the export for you, check the recent-exports panel for prior runs, or trigger a BIBFRAME sync if a recent edit is not appearing.

For suspected bugs in the exported file (missing fields, validation errors that MarcEdit flags, records that fail consortium ingestion), report the issue through the L30 issue tracker so the engineering team can confirm and fix it. Include a small sample file and the destination's rejection message when possible.
