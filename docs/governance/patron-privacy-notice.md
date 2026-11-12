# Patron Privacy Notice — Template

## What this is

A public-facing notice posted on the library website and offered to every patron at the point of registration. It tells patrons what the library collects, how it is used, what choices they have, and how to exercise their rights. It is read by patrons, parents, journalists, and occasionally regulators. Keep it short, plain, and consistent with the internal data-retention policy.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{library_address}}` | 100 Main St, Anytown, OH |
| `{{library_website}}` | https://example.org |
| `{{director_name}}` | Director name |
| `{{privacy_contact_email}}` | privacy@example.org |
| `{{privacy_contact_phone}}` | (555) 555-5555 |
| `{{state}}` | Ohio |
| `{{state_confidentiality_statute}}` | Ohio Rev. Code Sec. 149.432 |
| `{{effective_date}}` | _to be filled at adoption_ |

## Suggested headings (patron-facing copy)

### What we collect

When you get a library card, we record your name, address, contact information, date of birth, and any household or family link you set up. When you borrow or return items, place holds, reserve rooms, attend programs, or use library computers, we keep enough information to support the service you asked for.

### What we do with it

We use your information to lend you materials, contact you about holds and overdues, run programs, and keep the library secure. We do not sell your information. We do not share it with advertisers. The library follows the American Library Association's commitment to the confidentiality of library records.

### What we keep, and for how long

`[LIBRARY POLICY DECISION]` Wording here must match the internal data retention policy. Suggested baseline language follows; the library can substitute the stricter or opt-in variants if chosen.

- Items you have returned: we anonymize the link between you and the item after seven years. The aggregate record stays for collection-management statistics.
- Items currently checked out, on hold, or overdue: kept while active and for one billing cycle after.
- Account activity: kept while your account is active. Inactive accounts are archived after three years.
- Audit and security logs: kept for one year by default, longer if required by law.
- Computer-session records: kept as required for Children's Internet Protection Act reporting if the library participates in e-rate.

### Your rights

You can:

- Ask to see what information we have on you. The library provides this through a self-service export at `{{library_website}}/account/privacy`.
- Ask us to correct information that is wrong.
- Ask us to delete your account. We honor deletion requests on the schedule required by `{{state}}` law.
- Withdraw consent for anything you previously opted into.
- Ask a parent or guardian to make these requests on behalf of a patron under 13.

### How we handle requests from law enforcement

We follow `{{state_confidentiality_statute}}` and the Library Bill of Rights. We require a properly issued subpoena, warrant, or court order before disclosing patron records. Where the request includes a gag order, we comply. Where it does not, we notify the affected patron unless prohibited.

### Children's privacy

We do not allow online self-registration for anyone under 13. A parent or guardian must come into the library to register a child. We collect the minimum information needed to lend items and contact the parent. Parents can see, correct, and delete their child's records on request.

### Contact

Questions, requests, or complaints go to `{{privacy_contact_email}}` or `{{privacy_contact_phone}}`. The library director, `{{director_name}}`, is responsible for this notice. The board of trustees adopts it.

## Implementation-derived facts (do not paste this section into the public notice; for drafting only)

| Patron right | How L30 supports it | Source |
| --- | --- | --- |
| Self-export of own records | Patron-data export endpoints | `app/api/v1/privacy/data_export.py` |
| Correction | Data-correction request and audit | `app/api/v1/privacy/data_correction.py`, `ConsentRecord` audit on `app/models/privacy_ledger.py` |
| Account deletion | Patron-initiated deletion workflow | `app/api/v1/privacy/account_deletion.py` |
| Consent withdrawal | Consent ledger with grant and withdrawal entries | `app/models/privacy_ledger.py` `ConsentRecord` |
| Parent / guardian acting for minor | Patron-data controls for children | `app/api/v1/privacy/children.py`, `app/api/v1/privacy/patron_data_controls.py` |
| Under-13 self-registration block | Online card application rejects under-13 applicants | `app/api/v1/card_applications.py` COPPA gate at the application endpoint |

Patron-facing FAQ content already exists at `/opt/l30/frontend/src/data/faq/` and should remain consistent with this notice; specifically the `accessibility.tsx`, `account-features.tsx`, and `ebook-protection.tsx` entries reference adjacent privacy claims.

`[ATTORNEY REVIEW REQUIRED]` Counsel must confirm the law-enforcement, children's-privacy, and rights sections meet `{{state}}` law and any local ordinance.

## Adoption checklist

1. Director drafts library-specific copy by replacing tokens and resolving the retention paragraph against the data retention policy.
2. Counsel reviews the rights, law-enforcement, and children's sections.
3. Board adopts at a public meeting.
4. Notice posted on `{{library_website}}` and offered to every new patron at registration.
5. Effective date logged. Calendar a yearly review.
