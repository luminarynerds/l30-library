-- Flattens patron -> hold -> catalog item title/author into a single view so
-- outreach templates can render "your hold for <Title> is ready" without
-- N+1. Status filter limits the view to active/ready/pending holds — the
-- ones outreach actually messages about.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 7)
--
-- Safe to re-run.

BEGIN;

CREATE OR REPLACE VIEW patron_active_holds AS
SELECT
    h.user_id,
    h.id                AS hold_id,
    h.status            AS hold_status,
    h.position          AS queue_position,
    h.created_at        AS hold_created_at,
    h.notified_at       AS hold_notified_at,
    h.expires_at        AS hold_expires_at,
    h.pickup_location_id,
    b.name              AS pickup_branch_name,
    ci.id               AS catalog_item_id,
    ci.title            AS hold_title,
    ci.author           AS hold_author,
    ci.item_type        AS hold_item_type,
    ci.cover_url        AS hold_cover_url
FROM holds h
JOIN catalog_items ci ON ci.id = h.item_id
LEFT JOIN branches b  ON b.id  = h.pickup_location_id
WHERE h.status IN ('pending', 'ready');

COMMENT ON VIEW patron_active_holds IS
    'Flat patron -> hold -> catalog_item view for outreach templates and '
    'staff dashboards. Filtered to status IN (pending, ready). Refreshes '
    'live; no materialization. See spec '
    '2026-05-13-db-brittleness-reduction-spec.md.';

COMMIT;
