<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Database Schema Map

> Structural map of the persistence layer. Generated from a clean `origin/main`
> worktree (read-only). Grouped by domain with counts and drill-down pointers —
> not an exhaustive column dump. See `backend/docs/MODEL_CONVENTIONS.md` and
> `backend/docs/schema/` for conventions and selected DDL.

## At a glance

| Metric | Count | Source |
|--------|------:|--------|
| Model modules (`backend/app/models/*.py`) | 253 | `ls app/models/*.py` |
| ORM classes (`class … (Base)`) | ~861 | `grep -rE "^class .*Base"` |
| `__tablename__` declarations | ~1,094 | `grep -r __tablename__` |
| Alembic revisions (`backend/alembic/versions/*.py`) | ~205 | `ls` |

There are more `__tablename__` declarations than `class … (Base)` matches
because some modules define association/junction tables and multiple ORM
classes per file, and some base classes are matched indirectly.

## Stack & conventions

- **SQLAlchemy 2.0 async** (`asyncpg` driver) over **PostgreSQL** with the
  **`pgvector`** extension (semantic-search embeddings; see `models/embeddings.py`).
- **Enum columns are lowercase** in the DB (native PG enums); a 3-layer defense
  enforces this. Inserting uppercase values (e.g. `"CATALOGED"`) fails every row.
- **PII is field-encrypted at rest** with Fernet (`encrypt_pii()`/`decrypt_pii()`),
  key rotation via `PII_ENCRYPTION_KEY_PREVIOUS`. TOTP secrets also encrypted.
- **Shared mixins** live in `models/mixins.py` (timestamps, soft-delete, etc.).
- `database.db` (SQLite) exists at repo root for local/dev scaffolding only —
  **prod is Postgres** (`l30-database` container).

## Migrations (Alembic)

~205 revision files under `backend/alembic/versions/`. **The head graph is
merge-point-heavy: main routinely ships with multiple concurrent heads** that
are periodically reconciled with `…_mergepoint`/`unify_heads` revisions
(e.g. `20260519_final_mergepoint.py`, `unify_heads_002`, `dropispub_mergepoint_20260519`).
Treat ">1 head" as normal, not breakage — verify applied state with
`docker exec l30-backend alembic current` vs `alembic heads`.

> Caveat: the backend image **bakes** `app/` and `alembic/` — schema changes
> require an image rebuild, and the entrypoint no longer auto-runs migrations,
> so they are applied manually post-deploy.

## Domain clusters

The 253 model modules group into the following functional domains. Counts are
illustrative (representative modules listed, not exhaustive).

### Catalog & bibliographic
`catalog`, `catalog_authority`, `catalog_demand_signal`, `catalog_state_event`,
`bibframe`, `subject`, `series_management`, `serial`, `marc_batch`, `marc_macro`,
`comic_cataloging`, `manga_cataloging`, `collection`, `collection_alert`,
`inventory`, `weeding`, `shelf_note`, `shelf_reading`, `z3950_source`,
`embeddings`, `publisher_data`.

### Circulation & fulfillment
`circulation`, `circulation_policy`, `fine`, `fine_waiver`, `lost_damaged`,
`interlibrary_loan`, `book_drop`, `found_items`, `home_delivery`, `repair`,
`overflow_purchase`, `pod_order`.

### Patrons, accounts & identity
`user`, `patron_account`, `patron_activity`, `patron_category`,
`patron_communication`, `patron_consent`, `patron_segmentation`,
`patron_shelf_preferences`, `patron_boundaries`, `patron_merge_audit`,
`patron_onboarding`, `patron_training_opt_out`, `household`, `card_application`,
`oauth_account`, `session`, `permission`, `known_device`, `kiosk_device`,
`identity_evidence`, `api_key`.

### Acquisitions, EDI & vendors
`acquisition`, `acquisition_rationale`, `edi`, `purchase_request`,
`database_subscription`, `donation`, `royalty_transaction`, `serial`.

### Events & programs
`event`, `event_marketing`, `event_program_partner`, `event_registration`,
`event_review`, `event_waitlist`, `attendance`, `program`, `program_family`,
`program_planning`, `storytime`, `reading_programs`* (under reading).

### AI & knowledge
`ai_agents`, `ai_config`, `ai_guardrails`, `ai_tools`, `generated_content`,
`knowledge_base`, `knowledge_version`, `curated_recommendations`,
`training_example`, `support_ticket`. *(The Anthropic-backed AI support agent
was removed 2026-06-02; its 3 tables — `doc_chunks`,
`agent_support_tickets`, `agent_support_ticket_replies` — remain in the DB,
orphaned and unmapped. `support_ticket` is the unrelated human ticketing system.)*

### Indie authors, ebooks & external book sources
`indie_author`, `indie_author_follow`, `indie_author_release_notification`,
`indie_bookmark`, `indie_content_preference`, `indie_ebook_borrow`,
`indie_reading_list`, `indie_reading_progress`, `ebook_access_card`,
`ebook_checkout_log`, `ebook_curation`, `digital_access`, `download_event`,
`feedbooks`, `gutenberg`, `librivox`, `manybooks`, `open_library`,
`standard_ebooks`, `streaming`, `watermark_record`.

### Governance, legal & compliance
`board_audit_log`, `book_challenge`, `ban_tracker`, `content_flag`, `dmca`,
`law_enforcement_request`, `legal_compliance`, `cipa_compliance`,
`compliance_tracking`, `state_compliance`, `unified_compliance_audit`,
`public_records_request`, `professional_judgment`, `literacy_confidentiality`,
`threat_response`, `security_integration`.

### Learning, school & literacy
`learning`, `learning_path`, `learning_path_cohort`, `learning_path_waitlist`,
`learning_platform_enhanced`, `cohort`, `rubric`, `teacher_application`,
`literacy_learner`, `literacy_matching`, `literacy_outcomes`, `literacy_resources`,
`literacy_tutor`.

### Staff operations & scheduling
`end_of_day`, `end_of_shift`, `shift_handoff`, `shift_swap`, `cash_drawer`,
`staff_time_entry`, `staff_pay_rate`, `staff_presence`, `staff_safety`,
`staff_schedule_fairness`, `staff_picks`, `staff_shelves`,
`staff_message_board`, `fair_scheduling`, `focus_time`, `task_batching`,
`pto`, `volunteer`, `teen_volunteer`, `work_relationships`, `workflows`.

### Community, outreach & impact
`community`, `community_metrics`, `community_resource`, `immigrant_services`,
`genealogy`, `genealogy_research`, `outreach`, `engagement`, `impact`,
`carbon_metrics`, `local_authority`, `partner_collaboration`, `advocacy`*.

### Equipment, spaces & devices
`equipment`, `computer`, `makerspace`, `rfid`, `room`, `tech_booking`,
`tech_support`, `collectible_card`, `gamification`, `signage`,
`signage_advanced`, `multi_branch`, `branch`.

### Privacy, audit & lifecycle
`audit_log`, `operations_audit_log`, `board_audit_log`, `report_audit`,
`pii_access_log`, `privacy_ledger`, `archival`, `lifecycle`, `version_history`,
`offline_sync`.

### CMS, home & notifications
`blog`, `blog_bookmark`, `blog_subscription`, `home`, `home_page`,
`homepage_content`, `homepage_quote`, `announcements`, `emergency_alert`,
`emergency_operations`, `emergency_routing`, `library_branding`,
`library_document`, `page_meta_tag`, `marketing`, `marketing_hub`*,
`notification`, `notification_failure`, `notification_preference`, `sms`, `sip2`,
`print`, `print_notice`, `social_sharing`.

### Reading engagement & gamification
`reading`, `reading_activity`, `reading_goal`, `reading_list`,
`reading_milestone`, `reading_progress`, `reading_status`, `favorite`,
`review`, `review_response`, `mood_category`, `joy_capture`, `positivity`,
`perfectionism_antidotes`, `nudge`, `gamification`, `achievement`*.

### Operations, jobs & monitoring
`import_job`, `migration_job`, `migration_project`, `job_failure`,
`notification_failure`, `monitoring`, `system_status`, `link_health`,
`report_schedule`, `search_analytics`, `recent_search`, `saved_search`,
`usage_statistics`, `annual_report`, `strategic`, `demo_tenant`.

> `*` = referenced by feature/route name; verify exact module name in
> `backend/app/models/` before relying on it.

## How to drill down

```bash
# All tables in a domain module
grep -E "__tablename__|^class " backend/app/models/catalog.py

# Relationships for a model
grep -E "relationship\(|ForeignKey\(" backend/app/models/circulation.py

# Applied vs head migrations (prod)
docker exec l30-backend alembic current
docker exec l30-backend alembic heads
```
