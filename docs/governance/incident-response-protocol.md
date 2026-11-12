# Incident Response Protocol — Director Edition

## What this is

A director-facing protocol for handling system outages, data breaches, and security incidents. It covers who calls whom, what the library tells patrons and the board, and what targets the library holds the technical operator to. It does not duplicate the technical runbooks in `/opt/l30/docs/runbooks/`; those are for the engineer fixing the problem. This document is for the person answering the phone and the board chair.

## Library-fillable tokens

| Token | Example value |
| --- | --- |
| `{{library_name}}` | Anytown Public Library |
| `{{director_name}}` | Director name |
| `{{director_phone}}` | (555) 555-5555 |
| `{{director_email}}` | director@example.org |
| `{{board_chair_name}}` | Board Chair |
| `{{board_chair_phone}}` | (555) 555-5556 |
| `{{technical_operator}}` | Vendor or in-house technical contact |
| `{{technical_operator_phone}}` | (555) 555-5557 |
| `{{technical_operator_email}}` | ops@example.org |
| `{{patron_notification_channels}}` | Library website, lobby signage, social media |
| `{{rto_hours}}` | _to be set_ |
| `{{rpo_hours}}` | _to be set_ |

## Severity classification

| Severity | Description |
| --- | --- |
| **Sev-1: Service down** | Patrons cannot check out, place holds, or access accounts. Staff cannot circulate materials. |
| **Sev-2: Service degraded** | Major feature unavailable but circulation continues (e.g., catalog search broken, email stopped, one branch offline). |
| **Sev-3: Localized issue** | A subsystem affecting some patrons or staff. |
| **Sev-4: Security incident** | Suspected unauthorized access, data exposure, or active attack. |

A Sev-4 always takes precedence and follows the security path below, even if it presents as a Sev-1.

## Call sequence

### On detection of Sev-1 or Sev-2

1. Staff on duty notifies `{{director_name}}` at `{{director_phone}}`.
2. Director notifies `{{technical_operator}}` at `{{technical_operator_phone}}` with: symptom, when first noticed, what staff has tried.
3. Director posts a brief patron-facing notice through `{{patron_notification_channels}}` within 60 minutes.
4. Director notifies `{{board_chair_name}}` within 4 hours if outage continues, immediately if expected to last past closing.
5. Technical operator works through `/opt/l30/docs/runbooks/` (e.g., `backup-restore.md`, `drift-response.md`) for diagnosis and recovery.

### On detection of Sev-4 (security)

1. Staff notifies `{{director_name}}` immediately. Do not investigate further at the workstation.
2. Director notifies `{{technical_operator}}` and the library's counsel.
3. Director notifies `{{board_chair_name}}` within 1 hour.
4. Technical operator preserves logs and the L30 hash-chained audit log (`app/models/unified_compliance_audit.py` `previous_hash`) before any recovery action.
5. `[ATTORNEY REVIEW REQUIRED]` Counsel directs any patron-notification or regulator-notification timing under `{{state}}` data-breach notification law.

## RTO and RPO targets

`[LIBRARY POLICY DECISION]` The board must set the library's expectation for how fast service is restored (Recovery Time Objective) and how much data the library is willing to lose to a recovery (Recovery Point Objective).

| Service tier | Recommended RTO range | Recommended RPO range |
| --- | --- | --- |
| Sev-1 service-down | 4 to 24 hours | 1 to 24 hours |
| Sev-2 service-degraded | 24 to 72 hours | 24 hours |
| Sev-4 security incident | RTO subordinate to forensic preservation; RPO governed by counsel | n/a |

Document the library's chosen values:

- RTO target: `{{rto_hours}}` hours.
- RPO target: `{{rpo_hours}}` hours.

`[ATTORNEY REVIEW REQUIRED]` If the library has signed any agreement (with a consortium, the state library, or a vendor) committing to specific recovery targets, counsel confirms this protocol does not conflict.

## Patron communication template (Sev-1)

> The library's catalog and account system is currently unavailable. We are working with our technical team to restore service. You can still browse, return items at the desk, and we will not penalize anything overdue today. Updates here as we have them. Thanks for your patience.

For longer outages, name what works (computers, programs, returns) and what does not (checkout, holds, login), with a best-estimate return-to-service only if one is available. Never invent an estimate. For Sev-4, draft only after counsel review.

## Board chair template

> `{{board_chair_name}}`, brief note. Sev-`__` status. Symptom: `__`. First noticed: `__`. Working with `{{technical_operator}}`. Expected impact: `__`. Update by `__`. No public comment required unless you advise otherwise.

For Sev-4, first contact is by phone.

## Post-incident review

Every Sev-1 and Sev-4 incident receives a written post-incident review within 14 days:

- Timeline.
- Root cause as understood.
- What worked, what did not.
- Changes to runbooks or this protocol.
- Items added to the technical operator's punch list.

Sev-2 and Sev-3 are reviewed in aggregate quarterly. The director presents a summary to the board at least once a year.

## Adoption checklist

1. Director fills in contact tokens and confirms phone numbers are current.
2. Board adopts RTO and RPO targets at a public meeting.
3. Counsel reviews the security-incident path against `{{state}}` data-breach law.
4. Director and technical operator run a tabletop exercise at least once before going live, then annually.
5. Protocol posted to the staff handbook; pocket card with the call sequence given to anyone who may answer the phone after hours.
6. Calendar an annual review.
