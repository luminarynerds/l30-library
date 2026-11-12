# COPPA Compliance Memo — Template

## What this is

A director-facing memo certifying the library's compliance with the Children's Online Privacy Protection Act. Required if the library collects personal information online from anyone under 13, including through self-service card registration, room booking, program signup, or account management. Read at policy review, when a parent asks how the library handles their child's data, and on inspection.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{director_name}}` | Director name |
| `{{board_chair_name}}` | Board Chair |
| `{{privacy_contact_email}}` | privacy@example.org |
| `{{state}}` | Ohio |
| `{{minor_retention_months}}` | 12 |
| `{{parental_consent_method}}` | _in-person at the branch_ |
| `{{effective_date}}` | _to be filled at adoption_ |

## Implementation-derived facts

L30 enforces COPPA at the boundary of online self-service. The library should confirm these are operative before signing.

| Capability | L30 support | Source |
| --- | --- | --- |
| Under-13 self-registration block | The online card application rejects any applicant whose date of birth indicates an age under 13, before any personally identifying information is persisted | `app/api/v1/card_applications.py`, age check using `app/core/coppa.py` `is_under_coppa_age`; `COPPA_AGE_THRESHOLD = 13` |
| Configurable minor retention | The `COPPACompliance.minor_data_retention_months` setting controls how long minor patron records are retained. L30 falls back to a 12-month default if no setting is present | `app/services/data_retention_service.py` `_get_minor_retention_months`, `DEFAULT_MINOR_RETENTION_MONTHS = 12` |
| Separate minor anonymization cycle | A dedicated job anonymizes minor checkout records on the shorter retention | `app/services/data_retention_service.py` `_anonymize_minor_checkouts` |
| Parent / guardian access controls | API endpoints allow a parent to view and manage a child's records | `app/api/v1/privacy/children.py`, `app/api/v1/privacy/patron_data_controls.py` |
| Consent ledger for minor PII | Consent grants and withdrawals are recorded immutably | `app/models/privacy_ledger.py` `ConsentRecord`, `ConsentType` |

## Parental consent method

COPPA requires verifiable parental consent before collecting PII from a child under 13. L30 declines to collect online; the library obtains consent in person.

`[LIBRARY POLICY DECISION]` Document the library's verifiable parental consent method:

- [ ] In-person at the branch with photo identification of the parent or guardian (L30 default; pairs with the under-13 online block).
- [ ] Signed and mailed consent form, kept on file.
- [ ] Government-issued ID check at any branch in the consortium.
- [ ] A combination of the above for different services.

`[ATTORNEY REVIEW REQUIRED]` Counsel confirms the chosen method satisfies 16 CFR Sec. 312.5 verifiable-consent standards.

## PII collected from minors

`[LIBRARY POLICY DECISION]` Specify what the library collects from a patron under 13 at in-person registration. Suggested minimum:

- Name.
- Date of birth (used only to compute age category, not retained as a precise field beyond what is needed).
- Parent or guardian name and contact information.
- Address (household-level, not necessarily child-specific).
- School (`[LIBRARY POLICY DECISION]` optional, useful for school-partnership programs).

Avoid collecting: photographs, biometric data, precise geolocation, behavioral profiles, anything not directly necessary for lending.

## Parental access rights

Parents and legal guardians have the right to:

- See what the library holds on their child. Provided through the parent-facing endpoints at `app/api/v1/privacy/children.py`.
- Correct anything wrong, via the correction workflow at `app/api/v1/privacy/data_correction.py`.
- Delete the account and require the library to dispose of associated records, via `app/api/v1/privacy/account_deletion.py`.
- Withdraw consent for any specific data use, via the consent ledger.

## Notice to parents

`[LIBRARY POLICY DECISION]` The library must give parents notice of what is collected and how to exercise their rights, before or at the point of consent. Suggested format:

- One-page handout given at in-person registration of any child under 13.
- Posted alongside the patron privacy notice on the library website.
- Reissued whenever the data collected materially changes.

## Certification

I, `{{director_name}}`, director of `{{library_name}}`, certify that:

- The library does not collect personal information online from anyone under 13 without verifiable parental consent.
- The online card-registration system, powered by L30, rejects applicants whose date of birth indicates an age under 13 before any PII is stored.
- Parents have a documented method to review, correct, and delete their child's records.
- The library retains minor patron records for no more than `{{minor_retention_months}}` months past last activity, beyond which records are anonymized.

Director signature: _____________________ Date: __________

## Adoption checklist

1. Director and technical contact confirm the citations above remain accurate in the current L30 build.
2. Library decides on the parental consent method and drafts the one-page notice to parents.
3. Counsel reviews the consent method and notice.
4. Board adopts the memo at a public meeting.
5. Notice handed to every parent registering a child under 13. Posted with the patron privacy notice.
6. Calendar a yearly review.
