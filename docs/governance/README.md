# Governance Templates

This directory contains policy and procedure templates for libraries adopting the L30 integrated library system. Each document is a starting point, not a finished policy. The library and its counsel must complete the tokens, resolve the policy decision points, and obtain attorney sign-off before adoption.

## Conventions

| Marker | Meaning |
| --- | --- |
| `{{token}}` | Library-fillable value (e.g., `{{library_name}}`). Replace before publication. |
| `[LIBRARY POLICY DECISION]` | Choice the library board or director must make. Options are listed where possible. |
| `[ATTORNEY REVIEW REQUIRED]` | Section needing review by municipal or library counsel before adoption. |
| `[CODE GAP]` | Place where the L30 implementation does not yet match what a policy might assume. Surfaces follow-up engineering work. |

## The templates

1. **`data-retention-policy.md`** — How long L30 keeps patron records, audit logs, and operational data, and how the library disposes of them. Internal-facing.
2. **`patron-privacy-notice.md`** — Public-facing notice posted on the library website and at point of registration. Tells patrons what is collected, how it is used, and what choices they have.
3. **`cipa-compliance-memo.md`** — Children's Internet Protection Act posture for libraries receiving federal e-rate funding. Internet safety policy, monitoring of minors, public-hearing requirement.
4. **`coppa-compliance-memo.md`** — Children's Online Privacy Protection Act posture for any PII collected from patrons under 13. Parental consent workflow, notice, access rights.
5. **`fine-and-fee-policy.md`** — Fine schedule, waiver authority, replacement-cost policy, collections threshold. Codifies L30's fine-free default or a library-specific schedule.
6. **`incident-response-protocol.md`** — Director-facing protocol for system outages, security incidents, and data breaches. Call sequence, RTO/RPO targets, patron and board communication.
7. **`records-request-procedure.md`** — Procedure for law-enforcement requests, FOIA / public-records requests, patron self-access requests, and litigation hold.

## Adoption order

A library setting up L30 for the first time should draft these in roughly this order:

1. **Patron privacy notice** — Required before opening for circulation. Most state library-records statutes require a posted notice.
2. **Data retention policy** — Pairs with the privacy notice. Counsel and the privacy notice should be consistent.
3. **CIPA compliance memo** — Required before applying for federal e-rate funding. Includes a public-hearing requirement that takes 30 days lead time.
4. **COPPA compliance memo** — Required before allowing patron self-registration of minors. L30's online registration flow already enforces the under-13 block, so policy must match operational reality.
5. **Fine and fee policy** — Required before the first overdue item. L30 ships in fine-free mode by default, but the board should ratify the position in writing.
6. **Records-request procedure** — Required before the library receives its first subpoena or FOIA request. Document the chain of authority in advance, not under deadline pressure.
7. **Incident response protocol** — Required before going live. Tabletop the call sequence at least once before production cutover.

## Budget guidance

Plan for `[ATTORNEY REVIEW REQUIRED]` sections to consume two to five thousand dollars of municipal or contracted counsel time across all seven documents, depending on the rate and the depth of state-law analysis. Libraries with a sister municipality may be able to route the work through the city or county attorney at no marginal cost.

## How to keep these current

L30 evolves. The implementation-derived facts cited in these templates point at specific file paths in the L30 codebase. When a feature changes, the citing template should be updated in the same pull request. If you adopt these templates, plan a yearly governance review where the director, board chair, and a technical contact compare each document to current L30 behavior.
