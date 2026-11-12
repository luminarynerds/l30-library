# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed starter teacher training modules

Revision ID: pd_modules_001
Revises: circulation_policy_001
Create Date: 2026-05-14

teacher_training_modules was empty in prod, so the ProfessionalDevelopmentPage
rendered an empty list even after #497 wired its endpoints. Seeds 7 starter
modules across categories (reading-strategies, engagement, assessment,
technology) so the page has content for pilot.

Idempotency: partner_id is looked up dynamically by name pattern; each row
inserted with WHERE NOT EXISTS guard on (partner_id, title). Re-running this
migration is a no-op. If no Little Schitt Creek partner exists (e.g. fresh
test DB without that seed), this migration is a silent no-op -- no error.

The TeacherTrainingModule model has no natural unique constraint; the
WHERE NOT EXISTS guard handles dedup at insert time without adding a
constraint that other paths might violate.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "pd_modules_001"
down_revision: Union[str, None] = "circulation_policy_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SEED_MODULES = [
    {
        "title": "Building a Classroom Reading Routine",
        "description": (
            "Establish daily independent reading time that sticks. Covers "
            "schedule design, book selection norms, and quiet expectations "
            "for K-5 classrooms."
        ),
        "duration_minutes": 25,
        "category": "reading-strategies",
        "level": "beginner",
    },
    {
        "title": "Conferring with Readers: Quick 1-on-1 Strategies",
        "description": (
            "Short, structured reading conferences that fit inside a "
            "regular class period. Includes question prompts and a simple "
            "note-taking template."
        ),
        "duration_minutes": 30,
        "category": "assessment",
        "level": "intermediate",
    },
    {
        "title": "Welcoming Reluctant Readers",
        "description": (
            "Practical approaches for students who say they hate reading. "
            "Focuses on choice, low-stakes formats (graphic novels, audio), "
            "and how to avoid common pitfalls."
        ),
        "duration_minutes": 20,
        "category": "engagement",
        "level": "beginner",
    },
    {
        "title": "Using the Library Catalog in Lesson Planning",
        "description": (
            "Walkthrough of the library catalog from a teacher's perspective: "
            "subject search, reading level filters, requesting class sets, "
            "and pulling holds for a unit."
        ),
        "duration_minutes": 15,
        "category": "technology",
        "level": "beginner",
    },
    {
        "title": "Reading Aloud Across Grade Levels",
        "description": (
            "Read-aloud is not just for early elementary. Techniques for "
            "selecting texts, pacing, and discussion that work from "
            "kindergarten through middle school."
        ),
        "duration_minutes": 25,
        "category": "reading-strategies",
        "level": "intermediate",
    },
    {
        "title": "Pairing Books with Curriculum Standards",
        "description": (
            "How to map trade books to state standards without forcing the "
            "fit. Includes a worked example with a fifth-grade social "
            "studies unit."
        ),
        "duration_minutes": 40,
        "category": "assessment",
        "level": "advanced",
    },
    {
        "title": "Hosting an Author Visit (Library Partnership)",
        "description": (
            "Logistics, budget, and prep work for a successful author "
            "visit -- with the library as your co-host. Covers virtual "
            "and in-person options."
        ),
        "duration_minutes": 30,
        "category": "engagement",
        "level": "intermediate",
    },
]


def upgrade() -> None:
    if op.get_context().as_sql:
        # Seed depends on runtime partner lookup; cannot be previewed offline.
        return
    conn = op.get_bind()

    # Dynamic partner lookup. Prefer the school district over a single school
    # since modules apply across all teachers in the partnership.
    partner_row = conn.execute(
        sa.text(
            "SELECT id FROM outreach_partners "
            "WHERE name ILIKE 'Little Schitt Creek%' "
            "AND status = 'active' "
            "ORDER BY "
            "  CASE WHEN name ILIKE '%City Schools%' THEN 0 ELSE 1 END, "
            "  id "
            "LIMIT 1"
        )
    ).fetchone()

    if partner_row is None:
        # No matching partner (e.g. fresh test DB). Silent no-op.
        return

    partner_id = partner_row[0]

    insert_sql = sa.text(
        "INSERT INTO teacher_training_modules "
        "(partner_id, title, description, content_url, duration_minutes, "
        " category, level, is_active) "
        "SELECT :partner_id, :title, :description, NULL, :duration_minutes, "
        "       :category, :level, true "
        "WHERE NOT EXISTS ("
        "  SELECT 1 FROM teacher_training_modules "
        "  WHERE partner_id = CAST(:partner_id AS INTEGER) AND title = CAST(:title AS VARCHAR)"
        ")"
    )

    for module in SEED_MODULES:
        conn.execute(
            insert_sql,
            {
                "partner_id": partner_id,
                "title": module["title"],
                "description": module["description"],
                "duration_minutes": module["duration_minutes"],
                "category": module["category"],
                "level": module["level"],
            },
        )


def downgrade() -> None:
    if op.get_context().as_sql:
        return
    conn = op.get_bind()
    titles = [m["title"] for m in SEED_MODULES]
    conn.execute(
        sa.text(
            "DELETE FROM teacher_training_modules "
            "WHERE title = ANY(:titles) "
            "AND partner_id IN ("
            "  SELECT id FROM outreach_partners "
            "  WHERE name ILIKE 'Little Schitt Creek%'"
            ")"
        ),
        {"titles": titles},
    )
