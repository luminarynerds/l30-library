# CIPA Compliance Memo — Template

## What this is

A director-facing memo, addressed to the board and on file for state-library and FCC auditors, certifying the library's compliance with the Children's Internet Protection Act. Required if the library receives federal e-rate discounts on internet access or internal connections, or Library Services and Technology Act (LSTA) funds for internet access. Read at e-rate filing time, on inspection, and whenever the board reviews internet policy.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{director_name}}` | Director name |
| `{{board_chair_name}}` | Board Chair |
| `{{state}}` | Ohio |
| `{{e_rate_funding_year}}` | 2026 |
| `{{public_hearing_date}}` | _to be filled before filing_ |
| `{{public_hearing_notice_outlet}}` | local newspaper or county records |
| `{{filter_vendor_name}}` | _to be filled if filtering is in use_ |
| `{{filter_product_name}}` | _to be filled if filtering is in use_ |

## Implementation-derived facts

L30's CIPA-related models live at `app/models/cipa_compliance.py` and support:

| Capability | L30 support | Source |
| --- | --- | --- |
| Per-session computer logging with filter state | Each session records whether content filtering and minor filtering were enabled | `app/models/cipa_compliance.py` `ComputerSession`, fields `content_filtering_enabled`, `minor_filtering_enabled` |
| Filter bypass workflow for adults | Adult patrons may request a documented temporary bypass (CIPA permits disabling for adults engaged in bona fide research or lawful purpose) | `app/models/cipa_compliance.py` `FilterBypassRequest`, `BypassReason`, `BypassStatus` |
| Internet policy acceptance record | Patrons accept the library's Internet Safety Policy and the acceptance is timestamped | `app/models/cipa_compliance.py` `InternetPolicyAcceptance` |
| CIPA compliance reports for e-rate | Reportable counts of filter blocks, broken out by patron-age category | `app/models/cipa_compliance.py` `CIPAComplianceReport`, fields `filter_blocks_total`, `filter_blocks_minors` |

`[CODE GAP]` L30 records filter state on each session but does not itself perform DNS or HTTP filtering. The library must contract a Technology Protection Measure (TPM) — typically a network appliance or DNS-level filter — and configure the staff or computer-checkout flow to set the filtering flags on each session accurately. Confirm before certifying.

## Technology Protection Measure

`[LIBRARY POLICY DECISION]` Identify the TPM in use:

- [ ] Network-appliance filter at the gateway, vendor `{{filter_vendor_name}}`, product `{{filter_product_name}}`.
- [ ] DNS-level filter (e.g., a managed DNS service with category filtering).
- [ ] Per-workstation filter installed on each public computer.
- [ ] No TPM in use, and the library certifies it does not receive e-rate or LSTA internet funds.

`[ATTORNEY REVIEW REQUIRED]` If the library accepts federal funds and does not deploy a TPM, the director must consult counsel and the state library before signing.

## Internet safety policy

`[LIBRARY POLICY DECISION]` CIPA requires a written Internet Safety Policy covering all five elements:

1. Minors' access to inappropriate matter on the internet.
2. Safety and security of minors using email, chat, and other direct electronic communication.
3. Unauthorized access ("hacking") and other unlawful online activities by minors.
4. Unauthorized disclosure, use, and dissemination of personal information regarding minors.
5. Measures restricting minors' access to materials harmful to them.

One to two pages. Policy should reference this memo.

## Monitoring of minors

`[LIBRARY POLICY DECISION]` CIPA requires that minors' online activities be monitored. This is a procedural, not a technical, requirement.

- [ ] Staff sight-line monitoring: public computers are placed so that staff can observe screens.
- [ ] Software monitoring: filter or session-management software logs activity by minors.
- [ ] Hybrid: both of the above.

Document the chosen approach in the Internet Safety Policy.

## Public hearing requirement

CIPA requires public notice and at least one public hearing before adopting the Internet Safety Policy and TPM. Document:

- Notice published in `{{public_hearing_notice_outlet}}` at least 30 days before the hearing.
- Hearing held on `{{public_hearing_date}}` at a regularly scheduled board meeting.
- Minutes record any public comment.

`[ATTORNEY REVIEW REQUIRED]` Counsel confirms the notice and hearing meet `{{state}}` open-meetings law in addition to CIPA.

## Certification

I, `{{director_name}}`, director of `{{library_name}}`, certify that:

- The library has adopted an Internet Safety Policy meeting the five CIPA elements.
- A TPM is in place on all public-access computers, blocking obscenity, child pornography, and material harmful to minors.
- Public notice and a public hearing occurred on `{{public_hearing_date}}`.
- Minors' use is monitored as described above.
- The library will renew annually with each e-rate filing for funding year `{{e_rate_funding_year}}` and after.

Director signature: _____________________ Date: __________

Board chair countersign: _____________________ Date: __________

## Adoption checklist

1. Director identifies the TPM and confirms L30 session-logging integration.
2. Library drafts the Internet Safety Policy.
3. Public hearing scheduled at least 30 days out; notice published.
4. Board adopts policy and memo at the hearing.
5. Director signs, files with the FCC at e-rate filing time, retains a signed copy.
6. Calendar annual review aligned with the e-rate funding-year cycle.
