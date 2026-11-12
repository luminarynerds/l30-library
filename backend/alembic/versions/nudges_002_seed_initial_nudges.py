# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed initial nudges

Revision ID: nudges_002
Revises: nudges_001
Create Date: 2026-05-05 23:30:00.000000
"""
from typing import Sequence, Union
import json
import sqlalchemy as sa
from alembic import op

revision: str = "nudges_002"
down_revision: Union[str, None] = "nudges_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_NUDGES = [
    {
        "slug": "first-indie-checkout",
        "trigger_conditions": json.dumps([{"type": "event", "event": "checkout.indie_ebook"}]),
        "content_title": None,
        "content_body": "You just found something special. This came directly from an indie author, and your library will have it on the shelf forever.",
        "content_cta_label": "Discover more indie books",
        "content_cta_route": "/indie",
        "delivery_type": "toast",
        "delivery_placement": "global",
        "priority": 7,
        "cooldown_seconds": 2592000,
        "max_impressions": 1,
        "tags": "{behavior,indie}",
    },
    {
        "slug": "catalog-filters-hint",
        "trigger_conditions": json.dumps([
            {"type": "page_context", "route_pattern": "/catalog"},
            {"type": "feature_usage", "feature": "catalog_filters", "used": False},
        ]),
        "content_title": None,
        "content_body": "Tip: Use filters to browse by format, language, or availability. You can also filter for indie-only titles.",
        "content_cta_label": None,
        "content_cta_route": None,
        "delivery_type": "inline",
        "delivery_placement": "catalog",
        "priority": 4,
        "cooldown_seconds": 604800,
        "max_impressions": 2,
        "tags": "{contextual}",
    },
    {
        "slug": "ebook-discovery",
        "trigger_conditions": json.dumps([
            {"type": "patron_attribute", "attribute": "visit_count", "operator": "gte", "value": 5},
            {"type": "feature_usage", "feature": "ebook_checkout", "used": False},
        ]),
        "content_title": None,
        "content_body": "Did you know you can borrow ebooks instantly? No waitlists on indie titles -- and the library owns every copy permanently.",
        "content_cta_label": "Browse ebooks",
        "content_cta_route": "/ebooks",
        "delivery_type": "toast",
        "delivery_placement": "global",
        "priority": 5,
        "cooldown_seconds": 1209600,
        "max_impressions": 2,
        "tags": "{behavior,ebooks}",
    },
    {
        "slug": "makerspace-booking-hint",
        "trigger_conditions": json.dumps([
            {"type": "page_context", "route_pattern": "/makerspace"},
            {"type": "feature_usage", "feature": "equipment_booking", "used": False},
        ]),
        "content_title": None,
        "content_body": "Book equipment directly from here -- no phone calls, no forms. Just pick a time that works.",
        "content_cta_label": None,
        "content_cta_route": None,
        "delivery_type": "inline",
        "delivery_placement": "makerspace",
        "priority": 4,
        "cooldown_seconds": 604800,
        "max_impressions": 2,
        "tags": "{contextual,makerspace}",
    },
    {
        "slug": "accessibility-welcome",
        "trigger_conditions": json.dumps([
            {"type": "event", "event": "patron.login"},
            {"type": "patron_attribute", "attribute": "visit_count", "operator": "lte", "value": 2},
        ]),
        "content_title": "Make this yours",
        "content_body": "You can customize how this site looks and feels. Quiet Mode, dyslexia-friendly fonts, reduced motion -- it's all in your account settings.",
        "content_cta_label": "Personalize",
        "content_cta_route": "/account?tab=accessibility",
        "delivery_type": "panel",
        "delivery_placement": "global",
        "priority": 6,
        "cooldown_seconds": 2592000,
        "max_impressions": 1,
        "tags": "{milestone,accessibility}",
    },
]


def upgrade() -> None:
    nudges_table = sa.table(
        "nudges",
        sa.column("slug", sa.String),
        sa.column("trigger_conditions", sa.String),
        sa.column("content_title", sa.String),
        sa.column("content_body", sa.Text),
        sa.column("content_cta_label", sa.String),
        sa.column("content_cta_route", sa.String),
        sa.column("delivery_type", sa.String),
        sa.column("delivery_placement", sa.String),
        sa.column("priority", sa.SmallInteger),
        sa.column("cooldown_seconds", sa.Integer),
        sa.column("max_impressions", sa.SmallInteger),
        sa.column("tags", sa.ARRAY(sa.String)),
    )
    op.bulk_insert(nudges_table, SEED_NUDGES)


def downgrade() -> None:
    slugs = [n["slug"] for n in SEED_NUDGES]
    op.execute(sa.text("DELETE FROM nudges WHERE slug = ANY(:slugs)").bindparams(slugs=slugs))
