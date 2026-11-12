# Fine and Fee Policy — Template

## What this is

A board-adopted policy that sets fines, fees, waiver authority, and replacement-cost rules for the library. Read by the public when a charge appears, by staff when deciding whether to waive, and by the board when reviewing budget and equity outcomes. L30 ships in fine-free mode by default; this template supports both the fine-free position and a traditional fine schedule.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{director_name}}` | Director name |
| `{{board_chair_name}}` | Board Chair |
| `{{circulation_supervisor_title}}` | Head of Circulation |
| `{{collections_threshold_dollars}}` | 25.00 |
| `{{replacement_processing_fee}}` | 5.00 |
| `{{collections_agency_name}}` | _to be filled if used_ |
| `{{effective_date}}` | _to be filled at adoption_ |

## Implementation-derived facts

L30's fine engine is feature-complete but **defaults to fine-free**. Per-policy overrides live in the circulation-policy matrix.

| Capability | Source |
| --- | --- |
| Fine-free mode (zero overdue fines across all checkouts) | `app/services/fine_service.py` `FINE_FREE_MODE = True`, `OVERDUE_FINE_PER_DAY = Decimal("0.00")` |
| Per-policy rate, max-fine cap, grace period | `app/services/circulation_policy.py` `ResolvedPolicy.overdue_fine_per_day`, `max_fine`, `grace_period_days`, `fine_free` |
| Closure-day exemption (no fine for library-closed days) | `app/services/fine_service.py` `count_closure_days` |
| Role-based fine exemption | `app/services/fine_service.py` `settings.fine_exempt` |
| Reading-minutes alternative for certain roles | `app/services/fine_service.py` `check_and_create_overdue_fine` |
| Fines, payments, payment plans, waivers | `app/models/fine.py` `Fine`, `FineStatus`, `FineType`; `FinePaymentHistory`; `PaymentPlan` |
| System defaults (25-dollar max fine, two renewals) | `app/services/circulation_policy.py` `_system_defaults` |

## Position on fines

`[LIBRARY POLICY DECISION]` The board must state, in writing, the library's position:

- [ ] **Fine-free** (L30 default): The library does not charge overdue fines on any circulating item. Patrons are still responsible for replacement cost of lost or damaged items. Aligns with American Library Association policy and a growing majority of US public libraries.
- [ ] **Fine-free for minors, fines for adults**: Patrons under 18 do not accrue fines. Adult patrons accrue fines per the schedule below.
- [ ] **Standard fine schedule**: All patrons accrue fines per the schedule below.

`[ATTORNEY REVIEW REQUIRED]` If the library is municipal, counsel must confirm the chosen position is consistent with any city or county ordinance authorizing the library's fine schedule.

## Fine schedule (if not fine-free)

`[LIBRARY POLICY DECISION]` Complete this schedule only if the library is operating with fines. Rates are stored in the `CirculationPolicy` matrix at `app/services/circulation_policy.py` and can be set per item type, patron type, or branch.

| Item type | Loan period | Renewals | Overdue fine per day | Max fine | Grace period |
| --- | --- | --- | --- | --- | --- |
| Books | _days_ | _count_ | _dollars_ | _dollars_ | _days_ |
| Audiobooks | | | | | |
| DVDs | | | | | |
| Periodicals | | | | | |
| Hotspots / devices | | | | | |
| Interlibrary loan | | | | | |

## Replacement costs

`[LIBRARY POLICY DECISION]` Items billed as lost or damaged beyond use:

- Replacement equals the price L30 records on the item plus a `{{replacement_processing_fee}}` processing fee. If no recorded price, staff uses current retail for the same edition.
- Billed regardless of fine-free status. Fine-free is about overdue, not about returning the collection whole.
- Same item in good condition accepted as a substitute at staff discretion.

## Waiver authority

`[LIBRARY POLICY DECISION]` Who can waive without director approval:

| Role | Per-incident limit |
| --- | --- |
| Circulation staff | _dollars_ |
| `{{circulation_supervisor_title}}` | _dollars_ |
| Director | unlimited |
| Board | notified of waivers exceeding `{{collections_threshold_dollars}}` in monthly stats |

Every waiver logged in the fine record and visible in patron history.

## Collections referral

`[LIBRARY POLICY DECISION]` When a patron's outstanding balance exceeds `{{collections_threshold_dollars}}` and has aged past a stated period, the library may:

- [ ] Block the patron's card (suspend checkout privileges only) until resolved. No external collections.
- [ ] Refer to a collections agency, `{{collections_agency_name}}`. Patrons notified at least 30 days before referral.
- [ ] Write off the balance per board-approved write-off policy.

`[ATTORNEY REVIEW REQUIRED]` Collections referral implicates Fair Debt Collection Practices Act, state debt-collection law, and the library's confidentiality statute (the act of disclosing a patron's balance to a third party can violate library-records confidentiality). Counsel must confirm before adopting.

## Refund authority

`[LIBRARY POLICY DECISION]` Refunds for paid fines later found invalid: written request to `{{director_name}}`, director approves case-by-case, issued by check or original method, documented in the fine record (L30 supports a refunded status in `FineStatus`).

## Adoption checklist

1. Board adopts the position on fines.
2. If fined, fill the schedule and load rates into L30's circulation-policy matrix via the staff admin interface.
3. Counsel reviews collections-referral language.
4. Director signs. Policy posted on website and at every service desk.
5. Calendar an annual review aligned with the budget cycle.
