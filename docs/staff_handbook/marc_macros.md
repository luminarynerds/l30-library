# MARC Macros

This page explains what MARC macros are in L30, when to reach for them, and how to create and run one. It is written for catalogers comfortable with MARC tag-and-subfield notation. No code knowledge is assumed.

## What a macro is

A MARC macro in L30 is a **saved, ordered list of MARC field edits** that you can run against one record or a multi-select of records. It is modeled after MarcEdit's task list rather than a record-and-replay editor: each step is an explicit operation on a MARC tag and subfield, stored as structured data and validated before it runs.

Macros are how a cataloger says, "every time a record comes in with `650 $a Juvenile fiction`, I want to normalize that to my local genre heading," and then applies that intent to fifty records at once without re-typing.

A macro is **not** a free-form script. It does not execute Python, it does not have loops or conditionals, and it cannot reach across records. This is intentional: a macro that can do anything is a macro that can break everything. The four supported operations are deliberately narrow.

## The four operations

Every step in a macro is one of:

- **Set** — replace the current value of the targeted field with `value`.
- **Clear** — set the targeted field to NULL / empty.
- **Find / replace** — literal-string replace `find` with `replace` inside the targeted field. Not a regex.
- **Append** — append `value` to a list-shaped field. Today only **subjects** is treated as a list; on other fields, `append` falls back to `set` semantics.

The `find_replace` operation is strict literal matching. If you need pattern matching (e.g., "any year between 1900 and 1950"), you currently need to do that work in MarcEdit and re-import. TODO: verify with cataloger whether regex support in find_replace is a near-term ask.

## Supported targets

A macro can target any of the following MARC tag/subfield pairs. Each maps to a column on the `CatalogItem` row:

| Target  | Catalog field           |
|---------|-------------------------|
| `245$a` | title                   |
| `245$n` | volume_number           |
| `245$p` | volume_label            |
| `100$a` | author                  |
| `020$a` | isbn                    |
| `010$a` | lccn                    |
| `035$a` | oclc_number             |
| `260$b` | publisher               |
| `260$c` | publication_year        |
| `250$a` | edition                 |
| `490$a` | series_name             |
| `490$v` | series_number           |
| `520$a` | description             |
| `650$a` | subjects                |
| `082$a` | dewey_decimal           |
| `050$a` | lc_classification       |
| `300$a` | page_count              |

If you try to target a tag/subfield outside this list, the macro fails validation before any record is touched. The supported set is the operational catalog's column set; it does **not** cover the full BIBFRAME entity graph (contributors, complex notes, holdings) by design — those edits belong in the BIBFRAME-aware single-record editor.

## Visibility: private vs. shared

A macro is either **private** (visible only to the cataloger who created it) or **shared** (visible to all staff).

- Any staff user can create, edit, and delete **private** macros they own.
- Only **admin** or **director** roles can create or promote a macro to **shared**, edit a shared macro, or delete one.

This split exists because a shared macro is a small library policy decision: when you ship a "normalize genre headings" macro to the whole staff, you are saying "this is how we do it here." That decision should sit with the people accountable for the catalog's overall consistency.

When a staff user leaves the library and their account is removed, their **private** macros are detached (owner becomes null) but not deleted. Shared knowledge survives departures.

## How to create a macro

1. Open the **Staff Tools** menu and click **MARC Macros**, or go directly to `/staff/marc-macros`.
2. Click **New macro**.
3. Give it a clear name and a one-line description of what it does and when to use it. "Normalize JFIC to local genre 'Juvenile Fiction'" is a good description; "fix genre" is not.
4. Choose **Private** or **Shared** visibility.
5. Add one step at a time:
    - Pick an operation: **Set**, **Clear**, **Find / replace**, or **Append**.
    - Pick the MARC tag (three digits) and subfield (one alphanumeric character). The form offers a dropdown of the supported targets.
    - Fill in `value`, or `find` + `replace`, as the operation requires.
6. Click **Save**.

You can reorder steps with the up/down arrows. Steps run in order, top to bottom, on each selected record.

## How to run a macro

From the macros page, click **Run** on the macro you want, then either:

- Paste a list of catalog item IDs (comma-separated), or
- Use the **Pick from catalog** picker to multi-select records.

The run is **capped at 500 records per invocation**. For larger jobs, split into batches. This cap exists to keep the request synchronous and rollback-safe; long-running background macros are not yet supported.

Click **Run macro**. The result screen shows, per record:

- Which fields changed.
- Which steps were skipped (e.g., a `find_replace` whose `find` string wasn't present in the field).
- Any errors. **A record that errors mid-macro is fully rolled back**: every field the macro touched is restored to its pre-run value, so you never end up with a half-applied edit. The other records in the batch still apply normally.

## Common use cases

### Genre normalization

Vendor records often arrive with imprecise or non-local genre headings. A macro can sweep a batch into your local vocabulary:

- Step 1: `find_replace` on `650$a`, find `"Juvenile fiction"`, replace `"Juvenile Fiction"`.
- Step 2: `find_replace` on `650$a`, find `"Fiction, Juvenile"`, replace `"Juvenile Fiction"`.

Run it against your last vendor batch and the headings land in a consistent form.

### Location code fixes

When a branch is renamed or a shelving scheme changes, a macro can rewrite the affected field across a multi-select.

- Step 1: `find_replace` on `082$a`, find `"FIC"`, replace `"F"` (if you've moved from "FIC" to a single-letter call-number prefix).

For an actual branch-level shelving location change (which lives on the item record, not on `082`), use the **batch-update tool** in the catalog, not a macro — the macro target set does not cover item-level holdings.

### Series-statement cleanup

Series statements come in with inconsistent punctuation, trailing periods, or duplicated `;` separators. A macro can normalize:

- Step 1: `find_replace` on `490$a`, find `" ;"`, replace `";"` (collapse stray space-before-semicolon).
- Step 2: `find_replace` on `490$a`, find `"."`, replace `""` (strip a trailing period — apply with care, this is greedy literal replace).

Spot-check the **changed fields** column on the result screen before considering the run finished.

### Filling in a missing field across a batch

When you've just imported a vendor file that omitted publication year, and you know all the records are 2024 textbooks:

- Step 1: `set` on `260$c`, value `"2024"`.

Run against the imported batch. Records that already have a publication year are still overwritten — `set` is unconditional. If you want to fill only when empty, today you'd need to filter your selection in the catalog picker first.

## Known limitations

**No regex in find_replace.** Patterns are literal strings only. For pattern-based edits, export to MarcEdit, edit there, and re-import.

**No conditional steps.** A macro applies every step to every selected record. "Only set publication_year if it's empty" is not expressible today — filter your selection instead.

**500-record cap per run.** Larger jobs must be batched. This cap exists because macros are synchronous and roll back per-record on error; a background-job version is not yet built.

**Operational catalog only.** Targets are limited to the `CatalogItem` column set. Contributor entities, complex notes, holdings, and the full BIBFRAME entity graph are out of scope for macros and must be edited through the BIBFRAME-aware single-record editor.

**`append` only behaves as append on `subjects`.** On every other field it is equivalent to `set`. If you want to append to a different list-shaped field, that field must be added to the `LIST_FIELDS` set in the service layer — talk to your L30 admin.

## Who to ask

For help designing a macro that does what you want, or to review whether a sequence of steps is safe to run against a batch, contact your library's L30 admin or your cataloging lead. A two-minute review before running against 200 records is much cheaper than reconciling 200 unwanted edits afterward.

For suspected bugs (steps that should apply and don't, rollbacks that didn't restore the prior value, validation errors on legitimate targets), report through the L30 issue tracker. Include the macro JSON (copy from the editor), a sample catalog item ID, and the result screen.
