---
title: Library and L30 glossary
audience: all-staff
diataxis: reference
estimated_time: 25 min
last_reviewed: 2026-05-12
app_routes: []
---

# Library and L30 glossary

## What this is for

A reference for library-specific and L30-specific terms used in the staff documentation.

## When you'd use it

- Looking up an unfamiliar term while reading another doc.
- Checking the canonical name for a concept before writing a patron-facing message.

## Quick index

[AACR2](#aacr2) | [account block](#account-block) | [account hold](#account-hold) | [authority record](#authority-record) | [badge / milestone](#badge--milestone) | [barcode](#barcode) | [bib](#bib-bibliographic-record) | [bib record](#bib-record) | [BIBFRAME](#bibframe) | [branch](#branch) | [call number](#call-number) | [checkout](#checkout) | [circulation policy](#circulation-policy) | [claims returned / claims never had](#claims-returned--claims-never-had) | [co-reader / read-to-me entry](#co-reader--read-to-me-entry) | [copy](#copy) | [COUNTER R5](#counter-r5) | [courtesy account](#courtesy-account) | [dashboard function](#dashboard-function) | [dashboard tone](#dashboard-tone) | [discharge](#discharge) | [due date](#due-date) | [expired account](#expired-account) | [expiry](#expiry) | [EZproxy stanza](#ezproxy-stanza) | [family group](#family-group) | [fee](#fee) | [fine](#fine) | [fine schedule](#fine-schedule) | [fine vs fee vs lost-item charge](#fine-vs-fee-vs-lost-item-charge) | [fixed fields](#fixed-fields) | [function tag](#function-tag) | [guardian](#guardian) | [hold](#hold) | [hold queue](#hold-queue) | [hold shelf](#hold-shelf) | [holding](#holding) | [holdings record](#holdings-record) | [household](#household) | [IMLS report](#imls-report) | [in transit](#in-transit) | [instance](#instance) | [ISBN](#isbn) | [item](#item) | [kiosk session](#kiosk-session) | [LCSH](#lcsh) | [leaderboard opt-out](#leaderboard-opt-out) | [lost-item charge](#lost-item-charge) | [MARC](#marc) | [OCLC](#oclc) | [overdue](#overdue) | [parental consent (COPPA)](#parental-consent-coppa) | [patron](#patron) | [primary cardholder](#primary-cardholder) | [RDA](#rda) | [reading log entry](#reading-log-entry) | [reading program](#reading-program) | [reading streak](#reading-streak) | [recall](#recall) | [registration](#registration) | [renewal](#renewal) | [restricted](#restricted) | [restriction](#restriction) | [role](#role) | [self-reported vs staff-verified entry](#self-reported-vs-staff-verified-entry) | [SIP2](#sip2) | [suspension](#suspension) | [work](#work)

If you do every job at your library, ignore the role and token distinctions below -- they exist for libraries with separate desks and supervisors. A solo librarian is cardholder, circulation worker, cataloger, and head of circulation on one login. A token like `{{head_of_circulation_name}}` means "the person who handles this." If that's you, it's you.

## General library terms

The spine here is the bib/item/copy hierarchy: a **bib** is one cataloging record for one edition; an **item** is the lendable thing attached to a bib; a **copy** is the specific physical artifact with its own barcode. The companion [concepts.md](concepts.md) doc expands on the distinctions that trip new staff up.

| Term | Meaning | Example |
|------|---------|---------|
| <a id="aacr2"></a>AACR2 | Anglo-American Cataloguing Rules, 2nd edition. The cataloging rule set most North American libraries used before RDA. Older imported bibs follow AACR2; new cataloging follows RDA. | A 1990s import shows AACR2 punctuation in the 245 field. |
| <a id="authority-record"></a>authority record | A controlled-vocabulary record linking variant names to one canonical heading. Why a search for "Twain, Mark" also returns "Clemens, Samuel." Catalogers maintain these. | Searching "Twain" surfaces records cataloged under "Clemens, Samuel." |
| <a id="barcode"></a>barcode | Unique identifier on an item or card. | Scan the barcode during `Check Out`. |
| <a id="bib-bibliographic-record"></a>bib (bibliographic record) | Metadata record for one edition: title, author, subjects, identifiers. | A bib for the 2008 Penguin Classics edition of *Pride and Prejudice*. A different edition gets its own bib. |
| <a id="bib-record"></a>bib record | Synonym for `bib`. The full MARC21 record stored in L30. | Editing a bib record means editing its MARC fields. |
| <a id="bibframe"></a>BIBFRAME | Linked-data format intended as a long-term successor to bibliographic exchange formats, not yet a replacement in practice. L30 derives BIBFRAME 2.0 via one-way sync from the canonical cataloging store; corrections happen in the cataloging form, not in BIBFRAME. | BIBFRAME output is read-only; corrections go to the cataloging form. |
| <a id="call-number"></a>call number | The shelf address for an item, usually Dewey or LC. | `813.54 LEE`. |
| <a id="checkout"></a>checkout | Associating an item with a patron for a loan period. Reduces the item's available count. | A patron checks out two books and a DVD. |
| <a id="claims-returned--claims-never-had"></a>claims returned / claims never had | Patron disputes. *Claims returned*: patron says they returned it, system shows it still out. *Claims never had*: patron says they never checked it out. Both go through documented review; do not discharge to clear the record. | Patron insists they dropped the book at the chute; flag as claims returned. |
| <a id="copy"></a>copy | Single physical artifact on a shelf, identified by a barcode. Three copies of one book share one bib and three item records. Staff often say "item" when they mean "copy"; see [concepts.md](concepts.md). | Branch A and Branch B each hold one copy of the 2008 Penguin edition. |
| <a id="discharge"></a>discharge | Some ILSes call check-in "discharge." L30 calls it `check in`. If a vendor or trainer says "discharge," they mean check-in. | A vendor doc says "discharge"; read that as check-in. |
| <a id="due-date"></a>due date | Date and time a checked-out item is owed back. Default loan periods are configured per item type in `Borrowing Rules` (the patron-facing Help pages at `/help` are the canonical source: books and audiobooks are 3 weeks, DVDs 1 week, magazines 2 weeks, new releases 2 weeks no-renewal, museum passes 1 week, digital items 2-3 weeks). | Books due 21 days after checkout. |
| <a id="fee"></a>fee | One-time charge for a specific event such as a card-replacement or processing cost. Fixed amount; does not accrue over time. Compare `fine` (accrues over time) and `lost-item charge` (replacement plus processing). | `$2.00` lost-card replacement fee. |
| <a id="fine"></a>fine | Charge that accrues over time from a circulation event (overdue days). Local policy governs rate and caps; document the reason on the patron note before applying. Fine schedules are configurable per library; numbers here are illustrative. As of 2026-05, the patron-facing FAQ states this library does NOT charge daily overdue fines (items 30+ days late are marked lost instead). Confirm your library's current policy with `{{head_of_circulation_name}}` before quoting fine amounts to patrons. | `$0.10` per day for an overdue DVD at a fine-charging library. |
| <a id="fine-vs-fee-vs-lost-item-charge"></a>fine vs fee vs lost-item charge | Three distinct charge types staff confuse. A **fine** accrues over time (cents per day overdue). A **fee** is a fixed one-time charge for a specific event (card replacement, processing). A **lost-item charge** is the combined replacement plus processing posted when an item is declared lost, and is *removed* if the item is returned. Use the right name on the receipt and on patron-facing notes. | The `$15.00` line on the patron account is a lost-item charge, not a fine; it clears when the book comes back. |
| <a id="fixed-fields"></a>fixed fields | Positionally-encoded MARC fields (`leader`, `008`, `006`) where each character has a defined meaning (record type, language, audience). Catalogers edit these through the cataloging form; the form labels the positions in plain language. | Position 22 of the `008` field encodes audience level. |
| <a id="hold"></a>hold | A patron's request to be next in line for an item. Statuses: `pending`, `ready`, `fulfilled`, `cancelled`, `expired`. Pickup window after `ready` notification is `7 days` per `/help` (verify your library's current setting under `Borrowing Rules`). | A patron places a hold on a checked-out copy. |
| <a id="hold-queue"></a>hold queue | Ordered line of patrons waiting for the same bib. | Position 1 is next. |
| <a id="hold-shelf"></a>hold shelf | Physical shelf where ready holds wait for pickup. Supports slot assignment like `A-03`. | Pull the hold from slot `A-03`. |
| <a id="holding"></a>holding | A library's statement of what it owns for a bib, with location and call number. | Two copies at main, one at bookmobile. |
| <a id="holdings-record"></a>holdings record | The persisted record of a library's holding for a specific bib: locations, call numbers, copy counts. Some ILSes call this an MFHD (MARC Format for Holdings Data); L30 stores it inline with the bib. | The holdings record shows two copies at main and one at bookmobile. |
| <a id="in-transit"></a>in transit | An item's status when checked in at one branch but going to another. Do not re-route an item already `in transit`. | A book checked in at bookmobile, owned by main, shows `in transit` until arrival. Wait for the item to arrive at its destination branch before re-routing. |
| <a id="instance"></a>instance | BIBFRAME term for a specific edition of a work, equivalent to a MARC `bib`. BIBFRAME models the catalog as `Work -> Instance -> Item`. L30's canonical store is MARC; the BIBFRAME instance is derived. | The 2008 Penguin edition of *Pride and Prejudice* is one instance of the work. |
| <a id="isbn"></a>ISBN | International Standard Book Number. Identifies an edition. | Two paperback editions have different ISBNs. |
| <a id="item"></a>item | A physical or digital thing the library lends, attached to a bib. | A hardback of *Pride and Prejudice*. |
| <a id="lcsh"></a>LCSH | Library of Congress Subject Headings. The controlled subject vocabulary most U.S. public libraries use. L30 surfaces LCSH lookups in the cataloging form's subject (`650`) field. | Cataloging picks `Detective and mystery stories` from LCSH. |
| <a id="lost-item-charge"></a>lost-item charge | Combined replacement plus processing fee when an item is declared lost. Status moves to `lost` or `lost_by_patron`. Per the patron-facing Help pages at `/help`: returning the item clears the replacement portion of the charge even if late; a small processing fee may remain. | Posts when staff mark the checkout `lost`. Clears when the item is returned. |
| <a id="marc"></a>MARC | MAchine-Readable Cataloging. 1960s-era format still used as the canonical bibliographic exchange. L30 stores each bib as MARC21; the cataloging screen shows MARC tags (245 title, 100 author). Catalogers edit MARC; most staff don't. | Bibs saved through the cataloging form are stored as MARC21. |
| <a id="oclc"></a>OCLC | OCLC number from WorldCat. Used for Z39.50 copy cataloging. | Importing by OCLC number pre-fills MARC fields. |
| <a id="overdue"></a>overdue | A checkout past its due date. May trigger fines or suspension. | An item one day past due is overdue. |
| <a id="rda"></a>RDA | Resource Description and Access. The current cataloging rule set (replacing AACR2) used for new copy and original cataloging. L30 cataloging form defaults assume RDA. | A 2018 bib spells out `pages` rather than abbreviating, per RDA. |
| <a id="recall"></a>recall | Staff or system action shortening a due date, usually to fulfill a higher-priority hold or reclaim long-loan equipment. Patron is notified of the new due date. | Staff recall a laptop loan when an equipment hold comes in. |
| <a id="renewal"></a>renewal | Extending the due date on an active checkout. Renewal count appears on the patron detail page. Per `/help`: up to `2 renewals` per item, blocked if another patron holds the item, and new releases are non-renewable. Confirm current rules under `Borrowing Rules`. | A patron renews for another two weeks. |
| <a id="restriction"></a>restriction | Staff-applied limit on an account (blocking new holds, capping checkouts). Staff put it on and staff take it off. Local policy governs duration and conditions; document the reason on the patron note before applying. | Blocks new holds during a dispute investigation. |
| <a id="suspension"></a>suspension | Automatic, time-bounded patron status. Lifts when the end date passes or conditions clear. | Suspended 14 days after a third overdue notice. |
| <a id="work"></a>work | BIBFRAME and FRBR term for the abstract intellectual creation: the novel *Pride and Prejudice* independent of edition. One work has many instances (editions), each with many items (copies). Staff rarely interact with this layer; it shows up in BIBFRAME export and LCSH headings. | *Pride and Prejudice* is one work with dozens of instances. |

## Patron-facing roles and accounts

L30 uses a three-tier age model (under-13, teen 13-17, adult) and a household model for parental access.

| Term | Meaning | Example |
|------|---------|---------|
| <a id="account-block"></a>account block | Administrative `blocked` status. Set by staff; requires staff to lift. Patron detail page shows who set it and when. Local policy governs when a block is appropriate; document the reason on the patron note. | Account blocked after repeated lost items; consult your supervisor before applying. |
| <a id="account-hold"></a>account hold | Any condition preventing normal circulation (overdue, unpaid fees, expired card). Unrelated to a patron *hold* on an item. (Some libraries rename this `account block` or `account flag`; L30 keeps the legacy name.) | An account hold shows at `Check Out` if fines exceed the limit. |
| <a id="courtesy-account"></a>courtesy account | Short-term account for visitors and non-resident scholars: reduced privileges (no holds, no ILL, low checkout cap), near-term expiry. | A visiting professor gets one for six weeks. |
| <a id="expired-account"></a>expired account | Card or account past its `expiry` date. The account stays on file but circulation is blocked until the patron renews their card (re-verify address and ID per `/help`). Compare `suspension` (time-bounded automatic) and `account block` (administrative). | A patron whose annual non-resident card hit its `expiry` shows `expired` at `Check Out`; renew at the desk before circulating. |
| <a id="expiry"></a>expiry | Date a card or trial expires. Shown on the patron detail page. | Temporary card expires 30 days after issue. |
| <a id="guardian"></a>guardian | Adult on record for a minor patron. Called "parent" in patron-facing language; same record. Sees household activity, teen titles redacted. Staff cannot unredact at the desk -- redaction is system-enforced; direct title requests to the policy doc. Includes legal guardian, foster parent, kinship caregiver: same record, same permissions. | Guardian sees three teen checkouts, not the titles. |
| <a id="household"></a>household | Accounts linked by a parent/guardian relationship. Patron-record-level grouping, not program-scoped. | A parent and two children share one household. |
| <a id="kiosk-session"></a>kiosk session | Short-lived authenticated session at a public kiosk or self-check device, scoped to the device and ended on logout or inactivity. Close lingering sessions at end of shift. | Close the kiosk session at end of shift. |
| <a id="parental-consent-coppa"></a>parental consent (COPPA) | Verifiable parental consent required before collecting personal information from a patron under 13 (FTC COPPA Rule, 16 C.F.R. Part 312). Method: email-plus-second-step token sent to the parent on record; staff cannot complete it at the desk for the parent. Account stays inactive until consent is recorded; if consent lapses, the account locks until a new token completes. "Parent" includes legal guardian, foster parent, kinship caregiver. | A 10-year-old's account stays inactive until a parent completes consent. Staff hand the parent a handout; the parent completes the token from email. |
| <a id="patron"></a>patron | Community member with a library account. The `PATRON` role is default. | A new sign-up is a patron in good standing. |
| <a id="primary-cardholder"></a>primary cardholder | Patron whose card is on record for a household or temporary upgrade. | Primary cardholder vouches for a temporary card upgrade. |
| <a id="restricted"></a>restricted | Account flag for limited privileges, scoped to specific collections or actions. Distinct from suspension (automatic) and block (administrative). Used for parent-permission access on challenged titles and similar narrow constraints. | A restricted patron borrows only from one collection. |

## L30-specific terms

Terms specific to L30's data model and configuration.

| Term | Meaning | Example |
|------|---------|---------|
| <a id="badge--milestone"></a>badge / milestone | A reward earned by hitting a logged-reading threshold (10 books, 30 days). Shown on the patron's reading-program page. | A child earns the "10 books" badge after their tenth approved entry. |
| <a id="branch"></a>branch | Physical library location. Holds and checkouts scope to the branch chosen as pickup or owning location. | Main and bookmobile are separate branches. |
| <a id="circulation-policy"></a>circulation policy | Rules for loan period, renewal limits, hold limits, and fines per patron-type / item-type combination. Maintained by the head of circulation; staff see the result at `Check Out`. | Adult-fiction allows two renewals; juvenile-DVD allows one. |
| <a id="co-reader--read-to-me-entry"></a>co-reader / read-to-me entry | A log entry for a pre-reader being read to by an adult. Counts toward the child's program, not the adult's. | A parent reads a picture book to a four-year-old and logs it under the child. |
| <a id="counter-r5"></a>COUNTER R5 | Release 5 of the COUNTER Code of Practice, the standard for vendor-reported e-resource usage statistics. L30 records R5 metrics on subscription records; counts come from vendor portals, not L30 traffic. | COUNTER R5 figures come from the EBSCO admin portal each January. |
| <a id="dashboard-function"></a>dashboard function | Tag on a staff user controlling which widgets and tools appear on their dashboard. Values include `front_desk`, `board_ops`. See the Your Account doc. | Tagged `front_desk` shows the circulation dashboard. |
| <a id="dashboard-tone"></a>dashboard tone | Per-user setting: `calm`, `standard`, `full`. Affects density, not permissions. | A staff member who prefers less noise picks `calm`. |
| <a id="ezproxy-stanza"></a>EZproxy stanza | Configuration block in an EZproxy server's `config.txt` authorizing a database for remote patron access. L30 stores the stanza alongside the subscription record; the EZproxy server is the proxy. | The JSTOR stanza lives next to the JSTOR subscription. |
| <a id="family-group"></a>family group | Reading-program-scoped grouping tying a parent's account to children for shared registration and progress. Not the same as `household` -- household is patron-record-level; a family group only exists inside a program. | Three siblings tracked as one family group in summer reading. |
| <a id="fine-schedule"></a>fine schedule | Configured rates and caps for overdue fines by item type. | DVD: `$0.25` per day, capped at `$5.00`. |
| <a id="function-tag"></a>function tag | Literal string value of a dashboard function. Maps to widgets and routes. | `youth_services` enables the reading-program widget. |
| <a id="imls-report"></a>IMLS report | Annual stats report for the Institute of Museum and Library Services. L30 surfaces counts; the library submits. | IMLS needs total circulation and visit counts. |
| <a id="leaderboard-opt-out"></a>leaderboard opt-out | A reading program can suppress its leaderboard for an entire program (set by staff at program creation, useful for trauma-informed programs or younger age groups). A parent can also opt their child's individual progress out of any displayed leaderboard without leaving the program. Default for children's programs (target age under 13) is leaderboard-OFF; staff can opt in. | A parent of an 11-year-old asks for their child's name off the summer-reading top-10 board. Toggle the patron-level opt-out on the registration page. |
| <a id="reading-log-entry"></a>reading log entry | Patron-submitted reading activity tied to a program. Status: `pending`, `approved`, `rejected`. | A 30-minute entry awaits staff approval. |
| <a id="reading-program"></a>reading program | Configured challenge such as summer reading. Types: `summer`, `winter`, `year_round`, `special`. | Summer reading 2026 runs June--August. |
| <a id="reading-streak"></a>reading streak | Consecutive days with at least one logged entry. Resets when a day passes with no log. | A 14-day streak resets if the patron skips a day. |
| <a id="registration"></a>registration | Signing a patron up for a reading program. Not creating a library account. | A child registers for summer reading at the desk. |
| <a id="role"></a>role | A staff person's job category. Determines what pages and actions they can access. Multiple roles can stack on one account -- a solo librarian commonly has all of them. The current values: `circulation` (desk work, checkouts, holds, fines), `tech-services` (cataloging, MARC, imports, system health), `youth-services` (reading programs, events, family registration), `admin` (user management, policy, compliance reports), `director` (includes admin plus law-enforcement-request gating), `bookmobile` (outreach routes; flags the staffer for bookmobile-specific tools, separate from being the person who drives the bookmobile, which doesn't require this role), `homebond` (staff who deliver materials to homebound patrons), `legal` (handles legal holds and litigation requests), `super_admin` (system-level access; should be one or two people total). | `director` gates law-enforcement requests; `circulation` gates check-out and check-in. |
| <a id="self-reported-vs-staff-verified-entry"></a>self-reported vs staff-verified entry | A log entry defaults to self-reported. Staff can mark it verified after sighting the book or hearing the patron talk about it. Some programs require verification before badges issue. | A staffer flips a third-grader's entry to staff-verified after a book-talk. |
| <a id="sip2"></a>SIP2 | Standard Interchange Protocol v2. L30 runs a SIP2 TCP server with TLS for self-check and third-party circ. | The self-check kiosk talks to L30 over SIP2. |

## Terms staff confuse most

A few short notes for the pairs that catch new staff out.

A **hold** is a patron's request for a specific bib; a **hold shelf** is the place where ready holds wait for pickup. Don't say "on hold" when you mean "on the hold shelf."

A **fine** accrues over time, a **fee** is a fixed one-time charge, and a **lost-item charge** is the replacement-plus-processing posted when an item is declared lost. The lost-item charge *clears* when the item is returned; a fine or fee does not. Use the right name on the receipt and the patron note.

An **account hold** is a circulation gate (overdue, unpaid fees, expired card) -- it has nothing to do with a patron *hold* on an item. Some libraries call this an `account block` or `account flag`; L30 keeps the legacy name. An **account block** is one specific type of account hold: administrative, set by staff, requires staff to lift. A **suspension** is automatic and time-bounded (it lifts when the end date passes). A **restriction** is staff-applied and scoped (no holds, or one collection only). An **expired account** is past its `expiry` date and circulation is blocked until renewal at the desk.

A **bib** (or `bib record`) is one cataloging record for one edition; an **instance** is the BIBFRAME-side equivalent. A **work** is the abstract intellectual creation across all editions. A **holdings record** is the library's statement of what it owns for a bib. An **item** is the lendable thing attached to a bib; a **copy** is the specific physical artifact with its own barcode. Staff often say "item" when they mean "copy"; both are accepted at the desk but be precise in patron-facing notes.

Loan periods, renewal limits, hold pickup windows, and lost-item handling are configured per library. The patron-facing Help / Knowledge Base at `/help` is the canonical statement of *current* numbers for this library. If a staff doc and Help disagree, Help wins (and the doc should be updated). Don't quote numbers from this glossary as policy -- treat them as illustrative and confirm at `Borrowing Rules` or with `{{head_of_circulation_name}}`.

## Related

- [concepts.md](concepts.md) -- terms you'll mix up before day two
- [Staff orientation](orientation.md)
- [Circulation role orientation](../roles/circulation/orientation.md)
- [Circulation daily workflows](../roles/circulation/daily.md)
