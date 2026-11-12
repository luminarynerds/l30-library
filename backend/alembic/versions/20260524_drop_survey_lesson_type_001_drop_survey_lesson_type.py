"""drop_survey_lesson_type

Revision ID: drop_survey_lesson_type_001
Revises: courses_created_by_id_001
Create Date: 2026-05-24

Wave 1 of the L30 course-authoring friction strip plan. The ``survey``
lesson type was speculative scaffolding -- zero prod rows ever used it
(verified 2026-05-24). Remove the enum value so the editor surface
shrinks and the schema accurately reflects what is shipped.

IMPORTANT: prod's `lessons.lesson_type` is stored as ``varchar(20)``,
NOT as a PG enum. Earlier drafts of this migration assumed an
``ALTER TYPE lessontype`` rename-recreate dance; that statement errors
in prod with "type lessontype does not exist" because no such enum was
ever created (SQLAlchemy ``Enum(..., native_enum=False)`` was used).

The actual removal of ``survey`` is therefore a code-level change only
(Python ``LessonType`` enum + FE union + downstream cleanup). This
migration's job is just to guard data integrity: refuse to advance if
any ``survey`` rows exist, so a future runtime-enum check doesn't
silently swallow them.

The PG enum-drop branch is kept (gated on enum existence) for forward
compatibility with environments that DID adopt the native enum.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "drop_survey_lesson_type_001"
down_revision: Union[str, None] = "courses_created_by_id_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LESSON_TYPE_VALUES_WITHOUT_SURVEY = ("article", "video", "quiz", "sandbox", "lab")
LESSON_TYPE_VALUES_WITH_SURVEY = LESSON_TYPE_VALUES_WITHOUT_SURVEY + ("survey",)


def _native_enum_exists(bind, name: str) -> bool:
    """True iff a PG enum type with ``name`` exists in the connected DB."""
    if bind.dialect.name != "postgresql":
        return False
    return bool(
        bind.execute(
            sa.text(
                "SELECT 1 FROM pg_type WHERE typname = :n AND typtype = 'e'"
            ),
            {"n": name},
        ).scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()

    if not op.get_context().as_sql:
        # Data-integrity guard runs on every dialect. Refuse to advance the
        # schema if any 'survey' row still exists -- the code paths that read
        # this column will not survive seeing an unknown value.
        rows = bind.execute(
            sa.text("SELECT COUNT(*) FROM lessons WHERE lesson_type = 'survey'")
        ).scalar()
        if rows:
            raise RuntimeError(
                f"Refusing to drop 'survey' from LessonType: {rows} lesson(s) "
                "still use it. Migrate those rows to another type first."
            )

        # If the prod schema does NOT use a PG enum (current state for L30),
        # the column is varchar and there is nothing to alter at the DB level.
        if not _native_enum_exists(bind, "lessontype"):
            return

    # Otherwise: rename-recreate the enum to drop the value.
    op.execute("ALTER TYPE lessontype RENAME TO lessontype_old")
    new_type = sa.Enum(*LESSON_TYPE_VALUES_WITHOUT_SURVEY, name="lessontype")
    new_type.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE lessons ALTER COLUMN lesson_type TYPE lessontype "
        "USING lesson_type::text::lessontype"
    )
    op.execute("DROP TYPE lessontype_old")


def downgrade() -> None:
    bind = op.get_bind()
    if not op.get_context().as_sql:
        if not _native_enum_exists(bind, "lessontype"):
            return
    op.execute("ALTER TYPE lessontype RENAME TO lessontype_old")
    old_type = sa.Enum(*LESSON_TYPE_VALUES_WITH_SURVEY, name="lessontype")
    old_type.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE lessons ALTER COLUMN lesson_type TYPE lessontype "
        "USING lesson_type::text::lessontype"
    )
    op.execute("DROP TYPE lessontype_old")
