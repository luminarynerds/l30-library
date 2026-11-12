# Data Retention Policy — Template

## What this is

This policy tells the library, its patrons, and any auditor or regulator how long the library keeps each category of patron and operational data, what is anonymized versus deleted, and how requests for legal hold or override are handled. It is internal-facing but underpins the public-facing patron privacy notice. It gets read when a board member asks "what do we keep?", when a state-library auditor asks for written confirmation, or when a patron asks for their records.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{library_address}}` | 100 Main St, Anytown, OH |
| `{{director_name}}` | Director, Anytown Public Library |
| `{{board_chair_name}}` | Board Chair |
| `{{state}}` | Ohio |
| `{{state_confidentiality_statute}}` | Ohio Rev. Code Sec. 149.432 |
| `{{policy_review_cycle}}` | every two years |
| `{{policy_adopted_date}}` | _to be filled at adoption_ |

## Implementation-derived facts

These are what L30 does today. Verify before publishing — citations point to source files in `/opt/l30/backend/`.

| Data category | Retention behavior | Source |
| --- | --- | --- |
| Returned checkout records (adult patrons) | Patron link anonymized after seven years; aggregate record retained for collection statistics | `app/services/data_retention_service.py` `CHECKOUT_ANONYMIZE_YEARS = 7` |
| Returned checkout records (minor patrons, under 13) | Patron link anonymized on a shorter cycle governed by the `COPPACompliance.minor_data_retention_months` setting; default twelve months if unset | `app/services/data_retention_service.py` `_get_minor_retention_months`, `DEFAULT_MINOR_RETENTION_MONTHS = 12` |
| Inactive patron accounts | Archived after three years of inactivity | `app/services/data_retention_service.py` `INACTIVE_ACCOUNT_YEARS = 3` |
| Database access logs | Retained 365 days by default; tunable via `DATABASE_ACCESS_LOG_RETENTION_DAYS` environment variable | `app/services/data_retention_service.py` `ACCESS_LOG_RETENTION_DAYS` |
| Expired email blocks | Retained 90 days then deleted | `app/services/data_retention_service.py` `cleanup_expired_email_blocks` |
| Refresh tokens | Cleaned up after expiry | `app/services/data_retention_service.py` `cleanup_expired_refresh_tokens` |
| Password history | Trimmed beyond the configured retention limit | `app/services/data_retention_service.py` `cleanup_excess_password_history` |
| Consent ledger | Immutable. Each consent grant or withdrawal recorded; never modified | `app/models/privacy_ledger.py` `ConsentRecord` |
| Compliance audit log | Hash-chained, tamper-evident; previous-hash linkage validates each entry | `app/models/unified_compliance_audit.py` `previous_hash` |
| Account deletion requests | Patron-initiated deletion is logged, then user data is removed or anonymized | `app/services/data_retention_service.py` `process_scheduled_deletions`, `_delete_user_data` |
| Book challenge: challenger identity | Name and contact nulled twelve months after the challenge is resolved. The challenge record, the objection text, and the public summary are retained permanently for transparency | `app/services/data_retention_service.py` `purge_resolved_challenger_pii`, `CHALLENGER_PII_RETENTION_MONTHS = 12` |
| Book challenge: objection text | Retained permanently. Encrypted at rest, never shown publicly; the public page is built from the sanitized summary instead | `app/models/book_challenge.py` `challenger_complaint` |

## Book challenges

`[LIBRARY POLICY DECISION]` A patron who objects to a book fills in the reconsideration form on the public banned-books page. That record is what a named person thinks about a book, which for a library sits close to circulation data in sensitivity.

L30 encrypts the challenger's name, contact and objection at rest, and nulls the name and contact twelve months after the challenge is resolved. The challenge itself is kept permanently: a library's record of what was challenged and how it was handled is the point of the transparency page.

The clock starts at resolution, not at submission, so an open challenge keeps the contact details staff need to correspond about it.

- [ ] Default: purge challenger name and contact twelve months after resolution (L30 default behavior).
- [ ] Stricter: purge at the moment of resolution.
- [ ] Longer: retain for the library's general correspondence-retention period, if counsel advises the challenge file is a public record in `{{state}}`.

`[ATTORNEY REVIEW REQUIRED]` In some states a completed reconsideration file is itself a public record with a statutory retention period that overrides this default. Counsel must confirm before the shorter cycle is adopted.

## Reading history

`[LIBRARY POLICY DECISION]` Most public libraries do not retain reading history at all by default, on intellectual-freedom grounds. L30 anonymizes the patron-checkout link after seven years but retains the aggregate record. The library must choose:

- [ ] Default: anonymize returned checkouts after seven years, retain aggregate record for collection-management statistics (L30 default behavior).
- [ ] Stricter: purge the link at the moment of return so no reading history is ever recoverable, even to staff with database access.
- [ ] Opt-in: retain reading history for patrons who explicitly opt in (a "my reading list" feature), purge at return for everyone else.

`[ATTORNEY REVIEW REQUIRED]` Counsel must confirm the chosen retention is consistent with `{{state_confidentiality_statute}}` and any applicable case law. State library-records statutes vary materially.

## Legal hold and override

`[LIBRARY POLICY DECISION]` When the library receives a litigation hold, subpoena, or formal preservation request, automated retention jobs must pause for the records in scope.

- L30's retention service accepts a `held_patron_ids` parameter that excludes specified patrons from anonymization. The library must document who has authority to mark a patron held and unhold them.

`[ATTORNEY REVIEW REQUIRED]` Counsel should specify the chain of approval and the documentation required to mark a patron held.

## Disposal method

`[LIBRARY POLICY DECISION]` L30 anonymizes by nulling the patron link; the underlying row remains for statistics. The library may also choose to operate a hard-delete tier, requiring database-administrator action. Specify:

- Routine retention: anonymization in place (L30 default).
- Hard delete on request: triggered by a patron right-to-erasure request, processed through the privacy API at `app/api/v1/privacy/account_deletion.py`.

## Adoption checklist

1. Director and technical contact verify all citations in this template against the current `/opt/l30/backend/` source.
2. Counsel reviews the `[ATTORNEY REVIEW REQUIRED]` sections.
3. Board resolves the `[LIBRARY POLICY DECISION]` points at a public meeting.
4. Director signs and dates the final policy.
5. Policy posted on the library website, linked from the patron privacy notice.
6. Calendar a `{{policy_review_cycle}}` review.
