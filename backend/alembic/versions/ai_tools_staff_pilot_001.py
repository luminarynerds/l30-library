# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Make the staff AI Tools page real: working guardrails + a seeded Cataloging Helper.

Three data fixes so the /staff/admin/ai#tools page demonstrates working
controls instead of decorative switches:

1. Allowlist the local model the staff tools actually run (qwen2.5:3b). The
   allowlist already names llama3.2:3b (not pulled); without this row every
   tool call would be rejected by check_model_allowed before reaching Ollama.

2. Reconcile the four guardrail rows onto rule_types the engine actually
   handles (blocked_topic / required_disclaimer / content_filter). The rows
   were hand-inserted with off-menu types (topic_block, role_gate,
   output_limit) that ai_guardrails_service.py silently skips, so the
   Guardrails tab switches blocked nobody. Staff-only is now enforced in code
   at the chat endpoint, so the old "Staff-only model access" role_gate row is
   repurposed into a working cataloging disclaimer.

3. Seed the Cataloging Helper tool, DISABLED by default, so staff see a real
   tool with an on/off switch they flip themselves.

Idempotent: allowlist + tool use ON CONFLICT; guardrail updates key on the
current name and are no-ops once applied.

Revision ID: ai_tools_staff_pilot_001
Revises: staff_kb_staleness_001
Create Date: 2026-06-22
"""

import json
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text as sa_text

revision: str = "ai_tools_staff_pilot_001"
down_revision: Union[str, None] = "staff_kb_staleness_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODEL = "qwen2.5:3b"

DISCLAIMER = (
    "AI-generated draft. Verify all subject headings and classification numbers "
    "against the authority file (id.loc.gov) before adding them to a record."
)

PII_KEYWORDS = [
    "social security", "ssn", "credit card number", "patron record",
    "borrowing history", "library card number", "home address",
]

CATALOGING_PROMPT = (
    "You are a cataloging assistant for library staff at Little Schitt Creek "
    "Public Library. Given a title, author, and brief description, produce a "
    "DRAFT catalog record with these four labeled sections:\n\n"
    "1. Summary - a neutral 2-3 sentence annotation suitable for a catalog note.\n"
    "2. Suggested subject headings - 3 to 6 candidate LCSH or FAST headings.\n"
    "3. Classification - a suggested Dewey Decimal number and a Library of "
    "Congress class range.\n"
    "4. Audience and genre - reading level, audience (Juvenile, Young Adult, or "
    "Adult), and genre tags.\n\n"
    "These are DRAFTS to speed up a human cataloger, not finished records. Never "
    "invent ISBNs, control numbers, or facts that are not derivable from the "
    "input. If the input is too thin to classify, say so plainly instead of "
    "guessing. Always treat subject headings and classification as candidates to "
    "be verified against the authority file at id.loc.gov before they are applied."
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Allowlist the model the staff tools run on.
    bind.execute(
        sa_text(
            "INSERT INTO ai_model_allowlist "
            "(model_name, display_name, description, max_tokens_limit, "
            " allowed_temperature_min, allowed_temperature_max, enabled) "
            "VALUES (:m, 'Qwen2.5 3B', "
            "'Local general model for staff AI tools (cataloging assist). Runs "
            "on the library''s own server.', 2000, 0.0, 1.0, true) "
            "ON CONFLICT (model_name) DO UPDATE SET enabled = true"
        ),
        {"m": MODEL},
    )

    # 2. Reconcile guardrails onto handled rule_types.
    bind.execute(
        sa_text(
            "UPDATE ai_guardrails SET rule_config = cast(:cfg AS jsonb) "
            "WHERE name = 'No PII'"
        ),
        {"cfg": json.dumps({
            "keywords": PII_KEYWORDS,
            "message": "I can't help with requests that involve personal or patron data.",
        })},
    )
    bind.execute(
        sa_text(
            "UPDATE ai_guardrails SET rule_type = 'blocked_topic', "
            "rule_config = cast(:cfg AS jsonb) WHERE name = 'No legal advice'"
        ),
        {"cfg": json.dumps({
            "keywords": ["legal advice", "should i sue", "is it legal", "lawsuit", "my lawyer"],
            "message": "I can't provide legal advice. Please direct patrons to a qualified professional.",
        })},
    )
    # Old role_gate row (staff-only now enforced in code) becomes a working
    # required_disclaimer that fits the cataloging tool.
    bind.execute(
        sa_text(
            "UPDATE ai_guardrails SET name = 'Verify against authority file', "
            "description = 'Appends a reminder to verify AI-suggested headings "
            "and classifications against the authority file.', "
            "rule_type = 'required_disclaimer', rule_config = cast(:cfg AS jsonb) "
            "WHERE name = 'Staff-only model access'"
        ),
        {"cfg": json.dumps({"text": DISCLAIMER, "position": "append"})},
    )
    bind.execute(
        sa_text(
            "UPDATE ai_guardrails SET rule_type = 'content_filter', "
            "rule_config = cast(:cfg AS jsonb) WHERE name = 'Response length cap'"
        ),
        {"cfg": json.dumps({"max_length": 2000, "block_urls": False, "block_code": False})},
    )

    # The rows were scoped via applies_to_tools to tools that never existed,
    # so the switches matched nothing. Empty list = applies to every tool.
    bind.execute(
        sa_text(
            "UPDATE ai_guardrails SET applies_to_tools = cast('[]' AS jsonb) "
            "WHERE name IN ('No PII', 'No legal advice', "
            "'Verify against authority file', 'Response length cap')"
        )
    )

    # 3. Seed the Cataloging Helper, disabled by default.
    bind.execute(
        sa_text(
            "INSERT INTO ai_tools "
            "(tool_id, name, description, system_prompt, temperature, max_tokens, "
            " model, enabled, in_library_only, requires_auth, icon, category, "
            " sort_order, usage_count, block_for_minors, requires_parental_consent, "
            " block_for_patron_types) "
            "VALUES ('cataloging_helper', 'Cataloging Helper', :desc, :sys, 0.3, 500, "
            ":m, false, false, true, 'book-marked', 'staff', 0, 0, false, false, "
            "cast('[]' AS jsonb)) "
            "ON CONFLICT (tool_id) DO NOTHING"
        ),
        {
            "desc": (
                "Drafts catalog metadata (summary, subject headings, "
                "classification, audience/genre) from a title, author, and "
                "description. Staff-only. Drafts must be verified against the "
                "authority file before use."
            ),
            "sys": CATALOGING_PROMPT,
            "m": MODEL,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa_text("DELETE FROM ai_tools WHERE tool_id = 'cataloging_helper'"))
    bind.execute(sa_text("DELETE FROM ai_model_allowlist WHERE model_name = :m"), {"m": MODEL})
    bind.execute(sa_text(
        "UPDATE ai_guardrails SET name = 'Staff-only model access', "
        "rule_type = 'role_gate' WHERE name = 'Verify against authority file'"
    ))
    bind.execute(sa_text(
        "UPDATE ai_guardrails SET rule_type = 'topic_block' WHERE name = 'No legal advice'"
    ))
    bind.execute(sa_text(
        "UPDATE ai_guardrails SET rule_type = 'output_limit' WHERE name = 'Response length cap'"
    ))
