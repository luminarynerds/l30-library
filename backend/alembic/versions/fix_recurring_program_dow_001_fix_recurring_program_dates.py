# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""fix recurring-tagged programs whose program_date is on the wrong day-of-week

Three seed/demo rows in programs have notes referring to Wednesday recurrence
but program_date set to a Monday or Sunday (the seed creation date, 2026-04-26).
This causes them to surface on /staff/schedule/today on the wrong day-of-week,
confusing front-desk staff (see issue #803).

Targeted fix per the issue's recommended option 2 (move dates):
  id=3 "Adult Book Club" (Third Wednesday) -> 2026-06-17 (next 3rd Wed of a month)
  id=6 "Craft Club"      (Wednesdays)      -> 2026-05-27 (next Wednesday)
  id=7 "ESL Conversation Circle"           -> 2026-05-27 (next Wednesday)

The migration matches on (id, current program_date) so it's a no-op on any
environment whose data has already been corrected (or where these demo rows
have been deleted). A larger structural fix (recurrence rules) is tracked
separately and explicitly out of scope here per the issue.

Revision ID: fix_recurring_program_dow_001
Revises: card_app_check_token_001
Create Date: 2026-05-24
"""

from datetime import date
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text as sa_text

revision: str = "fix_recurring_program_dow_001"
down_revision: Union[str, None] = "card_app_check_token_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (program_id, old_date, new_date)
# old_date acts as an idempotency gate so the migration is a no-op on already-fixed data.
DATE_FIXES = [
    (3, date(2026, 5, 18), date(2026, 6, 17)),
    (6, date(2026, 5, 18), date(2026, 5, 27)),
    (7, date(2026, 5, 24), date(2026, 5, 27)),
]


def upgrade() -> None:
    bind = op.get_bind()
    for program_id, old_date, new_date in DATE_FIXES:
        bind.execute(
            sa_text(
                "UPDATE programs SET program_date = :new_date "
                "WHERE id = :pid AND program_date = :old_date"
            ),
            {"pid": program_id, "old_date": old_date, "new_date": new_date},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for program_id, old_date, new_date in DATE_FIXES:
        bind.execute(
            sa_text(
                "UPDATE programs SET program_date = :old_date "
                "WHERE id = :pid AND program_date = :new_date"
            ),
            {"pid": program_id, "old_date": old_date, "new_date": new_date},
        )
