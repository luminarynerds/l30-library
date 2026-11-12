# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""normalize bibframe language codes to ISO 639-2/B 3-letter form

Revision ID: bibframe_lang_norm_001
Revises: subjects_join_001
Create Date: 2026-05-16

Collapses ISO 639-1 (2-letter) codes to their ISO 639-2/B (3-letter)
equivalents for the most common languages. This is required before the
catalog Language facet ships -- otherwise patrons see ``en (25)`` and
``eng (128)`` as two separate buckets for the same language.

Conservative on purpose: only normalizes the dozen languages we have
direct evidence of in production data. Unknown 2-letter codes are left
alone so a later, evidence-driven pass can address them once we see
which ones actually appear.

One-way. ``downgrade()`` is a no-op: re-splitting normalized rows would
require remembering which originally came in as 2-letter, and we do not
keep that signal anywhere.
"""
from alembic import op

revision = "bibframe_lang_norm_001"
down_revision = "subjects_join_001"
branch_labels = None
depends_on = None


# ISO 639-1 -> ISO 639-2/B map for the languages we know exist in the
# corpus or are likely to appear in immigrant-serving collections.
_TWO_TO_THREE = {
    "en": "eng",
    "es": "spa",
    "fr": "fre",
    "de": "ger",
    "zh": "chi",
    "ar": "ara",
    "ru": "rus",
    "ja": "jpn",
    "ko": "kor",
    "pt": "por",
    "it": "ita",
    "vi": "vie",
}


def upgrade() -> None:
    when_clauses = "\n            ".join(
        f"WHEN '{two}' THEN '{three}'" for two, three in _TWO_TO_THREE.items()
    )
    in_list = ",".join(f"'{two}'" for two in _TWO_TO_THREE)
    op.execute(
        f"""
        UPDATE bibframe_works
        SET language = CASE language
            {when_clauses}
            ELSE language
        END
        WHERE language IN ({in_list})
        """
    )


def downgrade() -> None:
    # One-way normalization. See module docstring.
    pass
