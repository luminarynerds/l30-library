# Records Request Procedure — Template

## What this is

A director-facing procedure for handling four categories of records request the library will receive over time: law-enforcement requests, public-records (FOIA / state open records) requests, patron self-access requests, and litigation hold. Read when the request arrives, often under deadline. The procedure exists so the library does not improvise under pressure.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{director_name}}` | Director name |
| `{{board_chair_name}}` | Board Chair |
| `{{records_custodian}}` | Records custodian (usually director or designee) |
| `{{records_custodian_email}}` | records@example.org |
| `{{state}}` | Ohio |
| `{{state_confidentiality_statute}}` | Ohio Rev. Code Sec. 149.432 |
| `{{state_public_records_statute}}` | Ohio Rev. Code Sec. 149.43 |
| `{{state_response_days}}` | 10 business days |
| `{{counsel_name}}` | Library or municipal counsel |
| `{{counsel_phone}}` | (555) 555-5558 |

## Common principles

- Every request is logged. L30 tracks public-records requests in `app/models/public_records_request.py` and law-enforcement requests in `app/services/law_enforcement_service.py`.
- No staff responds substantively without director and counsel involvement. The desk acknowledges and routes.
- The library follows `{{state_confidentiality_statute}}`. Patron records are confidential by default; disclosure requires patron consent, proper legal process, or a statutory exception.
- Patron self-access goes through `app/api/v1/privacy/`, not the public-records path.

## Law-enforcement requests

L30's workflow at `app/services/law_enforcement_service.py` covers request intake (with `gag_order_until` tracking), tracking number, legal review, per-request checklist, response and patron-notification recording, patron-data export, per-request audit log, and annual transparency-report generation.

### Procedure

1. Staff routes immediately to `{{records_custodian}}`. Staff does not confirm or deny anyone's patron status.
2. `{{records_custodian}}` logs the request in L30 with: agency, officer, date, tracking number, type (subpoena, warrant, court order, National Security Letter), gag-order status, and records sought.
3. Call `{{counsel_name}}` at `{{counsel_phone}}`. Do not produce records without counsel review. Counsel determines validity, scope, and any basis to move to quash.
4. If valid and not under gag order: `[LIBRARY POLICY DECISION]` Notify the affected patron unless prohibited. Document the notification or the reason for non-notification.
5. Production via `export_patron_data` in `app/services/law_enforcement_service.py`; export hash recorded in the request audit log. Every action lands in the tamper-evident hash-chained audit log (`app/models/unified_compliance_audit.py` `previous_hash`).
6. After response, the full audit trail remains on file. Statistics roll up to the annual transparency report.

`[ATTORNEY REVIEW REQUIRED]` Counsel confirms the response, the patron-notification decision, and any move to quash. NSLs always go to counsel before any response.

## Public-records (FOIA) requests

L30 tracks public-records requests at `app/models/public_records_request.py`, with federal FOIA and per-state jurisdictions (`JurisdictionType`) encoding response-day expectations. Endpoints live at `app/api/v1/public_records.py`.

Public-records statutes cover library operations (board minutes, contracts, budgets, policies). They do **not** cover individual patron records, which are protected by `{{state_confidentiality_statute}}`.

### Procedure

1. Staff routes the request to `{{records_custodian}}` at `{{records_custodian_email}}`.
2. Log the request in L30 with: requester, date, scope, jurisdiction. Acknowledge within one business day, noting `{{state_response_days}}`.
3. Gather responsive records. Redact patron identifiers from any record that touches them.
4. `[ATTORNEY REVIEW REQUIRED]` Counsel reviews redactions and any exemption claim (privilege, security, patron-confidentiality per `{{state_confidentiality_statute}}`).
5. Release by deadline. Invoice per fee schedule if `{{state_public_records_statute}}` permits. Close the request in L30 with copies of what was released.

## Patron self-access requests

A patron may request their own records. L30 provides self-service through `app/api/v1/privacy/data_export.py`.

1. Verify identity (in-person with photo ID or authenticated patron-website login).
2. Direct the patron to the self-service export, or generate it staff-side.
3. Correction routes to `app/api/v1/privacy/data_correction.py`; deletion to `app/api/v1/privacy/account_deletion.py`. Both log to the privacy ledger at `app/models/privacy_ledger.py`.

## Litigation hold

When the library receives a hold notice or reasonably anticipates litigation, retention jobs must pause for affected records. L30's `anonymize_old_checkouts` (in `app/services/data_retention_service.py`) accepts a `held_patron_ids` set excluding those patrons.

1. `{{records_custodian}}` receives the notice; counsel confirms scope.
2. Technical operator adds patron IDs to the held set.
3. Hold logged with effective date and scope. Remains in effect until counsel releases it in writing.

`[ATTORNEY REVIEW REQUIRED]` Counsel sets the trigger (hold can attach before suit is filed) and scope.

## Annual transparency report

L30 generates a transparency report counting law-enforcement requests by type and including a separate count for those subject to gag order (`app/services/law_enforcement_service.py` `generate_transparency_report`). `[LIBRARY POLICY DECISION]` The library should choose whether to publish this report:

- [ ] Publish annually on the library website.
- [ ] Provide on request only.
- [ ] Provide to the board only.

`[ATTORNEY REVIEW REQUIRED]` Counsel reviews the transparency report before publication, particularly for any narrative content that could constitute disclosure of a gag-ordered request.

## Adoption checklist

1. Director and counsel walk through each procedure section and agree on the chain of approval.
2. Counsel resolves the `[LIBRARY POLICY DECISION]` points.
3. Board adopts at a public meeting.
4. Pocket card with the four request types and the routing path given to every staff member.
5. Director runs a tabletop exercise with counsel before the first real request.
6. Calendar an annual review of the procedure and the transparency report.
