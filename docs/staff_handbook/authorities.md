# Local Authorities

This page explains L30's local authorities table: what it is for, when you should create a new local authority versus link out to LC or VIAF, how to merge two records, and what propagates to bibliographic records when you edit an authority.

It is written for catalogers familiar with the idea of authority control. No code knowledge is assumed.

## What this is

A **local authority** is a controlled-vocabulary heading that your library maintains itself, as opposed to a heading you pull from an external source like LCNAF (name authorities), VIAF, LCSH (subjects), or FAST.

The use cases are:

- **Local subject headings** that don't exist in LCSH — community names, hyperlocal events, regional history, neighborhood landmarks.
- **Indie author name authorities** that haven't made it into LCNAF.
- **Series and uniform titles** created in-house, especially for local collections or self-published works.
- **Geographic, temporal, genre, or jurisdictional headings** that need a local form distinct from any national authority's preferred form.

Local authorities live in the `bibframe_local_authorities` table and are tracked separately from external authority links. The BIBFRAME side of the catalog references them through the same `AuthorityLink` table that points at LCNAF, VIAF, and FAST records — the difference is the `source` field (`LOCAL` for these, `LCNAF`/`VIAF`/`FAST` for the external ones).

## When to create a local authority vs. link to LC or VIAF

Default to **linking to an external authority** when one exists. Local authorities are easy to create and very hard to keep tidy at scale, so the first question is always "does someone else already maintain this heading?"

Reach for **LC / VIAF / FAST / LCSH** when:

- The heading is a person, organization, place, subject, or work that any other library might also catalog.
- The form already exists in id.loc.gov, viaf.org, or another national or international authority file.
- You want the heading to interop with consortium catalogs, OCLC, and downstream linked-data consumers.

Reach for a **local authority** when:

- The heading is hyperlocal — a community organization, an indie author the rest of the world hasn't yet cataloged, a neighborhood that doesn't appear in LC's geographic authorities.
- You have a local cataloging convention that intentionally differs from the LC preferred form (a different display order, a local spelling, a local-language variant) and you don't want LC's form to be the user-facing label.
- You're describing a **library-specific work** — a local-history zine, a board minutes binder, a programming kit you built — that no national authority would have a record for.
- You're staging a **provisional** heading while a cataloger reviews whether a proper external authority should be created or pulled.

If you're unsure, link externally first. A bib record that points at the LCNAF form can always be re-pointed at a local authority later; the reverse is messier.

## The shape of a local authority record

Every local authority has:

- A **type** — one of `name_personal`, `name_corporate`, `name_meeting`, `name_jurisdiction`, `subject_topic`, `subject_geographic`, `subject_temporal`, `subject_genre`, `title_uniform`, `title_series`, or `other`. The types follow MARC 1XX/6XX conventions.
- A **status** — `provisional` (awaiting cataloger review), `active` (in use), or `deprecated` (superseded, see "Merging" below).
- A **label** — the authorized heading. This is the form that gets displayed and indexed.
- A **normalized label** — automatically derived (lowercased, punctuation stripped) for uniqueness and lookup. You don't edit this directly.
- A **scope note** — optional, free-text guidance about when to use this heading.
- **Variants** — optional list of "see from" forms. Patrons searching for any variant land on the authorized heading.
- **Related authorities** — optional list of "see also" links to other authorities.
- **External links** — optional URIs to LCNAF, VIAF, Wikidata, or other external IDs for the same entity. Useful when a local heading exists alongside (not instead of) an external one.
- A **use-instead pointer** — if this authority is deprecated, the ID of the authority that replaces it. See "Merging" below.

The `(library_system_id, authority_type, label_normalized)` triple is unique. You cannot have two active authorities with the same normalized label and type in the same library system. This is the database guardrail against accidental duplicates.

## How to create a local authority

1. Open the **Staff Tools** menu and click **Local Authorities**, or go directly to `/staff/local-authorities`.
2. Click **New authority**.
3. Pick the type (this is also a MARC 1XX/6XX shape — `name_personal` is 100, `subject_topic` is 650, and so on).
4. Enter the label exactly as you want it to display.
5. Optionally add a scope note, variants, related authorities, and external links.
6. Set status to **provisional** if you want a colleague to review before it goes live, otherwise **active**.
7. Save.

The new authority is immediately available to link to BIBFRAME entities (works, instances, items).

## How to link an authority to a bib record

From the local authority detail page, click **Link to record**, pick the BIBFRAME entity (a Work or an Instance, typically), and choose the relationship role — for example, `creator`, `contributor`, `subject`, `genre`. The link is written to the `AuthorityLink` table with `source = LOCAL`.

From the BIBFRAME-aware single-record editor (see [bibframe_workflow.md](bibframe_workflow.md)), you can also search local authorities inline when adding a contributor or subject and link in one step.

## How to merge two authority records

You will, eventually, discover two authorities that are the same person, organization, or subject under slightly different forms — usually because two catalogers created them independently before the dedupe check found them. The merge process keeps one as the canonical record and points the other at it.

### The procedure

1. Decide which authority is the **keeper** (the one with the better form, more variants, more existing links, or the more recent review).
2. Open the **loser** authority (the one to be retired).
3. Optionally, copy any variants, scope notes, or external links from the loser to the keeper before retiring it.
4. Edit the loser: set its **status** to `deprecated`, and set its **use_instead_id** to the keeper's ID.
5. Save.

The deprecated record stays in the table — it is **not** deleted. Anything that was linking to it continues to resolve, and the `use_instead_id` pointer tells the catalog "if you're displaying this heading, redirect to the keeper."

### What does NOT happen automatically

Marking an authority deprecated and pointing at a keeper **does not** rewrite existing `AuthorityLink` rows. Bib records that were linked to the loser stay linked to the loser; the deprecation is a presentational redirect, not a database rewrite.

If you want every existing link to be re-pointed at the keeper, you need a separate batch step — today this is a request for your L30 admin to run a small SQL update. TODO: verify with cataloger whether an automatic relink-on-merge action belongs on the merge UI.

For most use cases the soft redirect is fine: patrons see the keeper's heading, and the next time a cataloger touches an affected bib record they can re-point the link.

## What propagates to bib records when you edit an authority

A useful mental model: **the authority record is the source of truth for the display label and the variants. The link between the authority and a bib record is what makes that record appear under the heading.** Editing the authority changes how it shows up everywhere that links to it; it does not rewrite the bib records themselves.

Concretely, when you edit a local authority:

- Changing the **label** updates the heading displayed wherever any linked bib record is shown under that authority. No bib record rows are mutated.
- Changing **variants** updates which alternate searches resolve to this heading. No bib record rows are mutated.
- Changing **scope note**, **related authorities**, or **external links** is metadata-only and visible only on the authority detail page.
- Changing **status** to `deprecated` triggers the use-instead redirect described above.
- Changing **authority_type** is allowed but rarely useful — if you've decided a heading is actually a different MARC shape (e.g., it should be `subject_geographic`, not `subject_topic`), prefer to create a new authority of the correct type and merge the old one into it. Type changes don't migrate the existing link relationship roles.

What this means in practice: editing an authority is cheap and safe. You do not need to re-batch-update every linked bib record to pick up a label correction. You **do** need to think carefully before changing a heading that's used in patron-facing displays — a sudden label change is visible to your patrons.

## Provisional workflow

If your library wants a two-person review on new headings (one cataloger drafts, another approves), use the **provisional → active** flow:

1. Drafting cataloger creates the authority with status `provisional`.
2. Reviewing cataloger opens the provisional list (filter by status), reviews each, and either edits + sets `active`, or deletes if it shouldn't have been created.

The provisional status doesn't prevent the authority from being linked to a bib record — it's a workflow flag, not a hard gate. If your library wants provisional headings to be link-blocked, that is a feature request, not a configuration. TODO: verify with cataloger whether provisional-blocks-linking is wanted.

## Known limitations

**Merging is a soft redirect, not a relink.** Marking an authority deprecated with `use_instead_id` does not rewrite existing `AuthorityLink` rows. Patrons see the keeper's heading; database links still point at the loser until a cataloger re-points them.

**Single-tenant uniqueness.** The uniqueness constraint is per `library_system_id`. In a multi-tenant deployment, the same heading can exist independently in two libraries — by design.

**No bulk import.** Local authorities are created one at a time through the UI. There is no MARC authority import, and no CSV upload. For libraries migrating in with a large authority file, an admin can write a one-off import script — talk to your L30 admin.

**Type changes don't migrate link roles.** Changing an authority's `authority_type` after it has been linked to bib records is allowed but rarely the right move; create a new authority and merge instead.

**`scope_note` and `source_notes` are not searched.** The authority search (the `q=` parameter) hits the label only. Notes are for human readers, not for retrieval.

## Who to ask

For help deciding whether to create a local authority or link externally, talk to your cataloging lead or your L30 admin. The default ("link external when possible") is right almost all the time, but the exceptions are real and worth a five-minute conversation.

For suspected bugs (a label edit that didn't update displays, a deprecation that didn't redirect, a uniqueness constraint that fired when it shouldn't have), report through the L30 issue tracker. Include the authority ID, the action you took, and what you expected to happen.
